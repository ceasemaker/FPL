"""Do squad changes improve the points forecast?

Two ideas from Sincere FC's videos, each added to the v2.0 features and
run through the same walk-forward backtest (2023/24-2025/26, weekly retrain):

* turnover: the share of last season's goalkeeper and defender minutes that
  left the player's club, and the same for his opponents. Fixed before the
  season starts.
* leap: how far a player's season-to-date xG + xA per 90 and share of minutes
  have moved from last season (FPL data, deadline-safe), plus whether he
  "made the leap" last season: the change in usage rate and xG + xA per 90
  from two seasons ago to last season at the same club (Opta season sheets).

Differences are paired by gameweek and bootstrapped over gameweeks. Results go
to squad_changes_eval.json next to this file.

    cd django_etl && python ../analysis/points_forecast_report/squad_changes_eval.py
"""
from __future__ import annotations

import gc
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "django_etl"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fpl_platform.settings")

import django  # noqa: E402

django.setup()

from etl.forecast.backtest import SEED, _bootstrap, evaluate  # noqa: E402
from etl.forecast.data import load_fixtures, load_players  # noqa: E402
from etl.forecast.features import FEATURES, build_features  # noqa: E402
from etl.models import PlayerSeasonStat  # noqa: E402
from etl.services.forecast_sync import elite_squads  # noqa: E402
from etl.services.squad_changes import _profile, defensive_turnover  # noqa: E402
from etl.services.usage import player_usage  # noqa: E402

TURNOVER = ["team_def_lost", "opp_def_lost"]
LEAP = ["xgi90_delta", "min_share_delta", "prev_usage_rise", "prev_xgi_rise"]
TEST = [2023, 2024, 2025]


def turnover_frame(seasons) -> pd.DataFrame:
    rows = [
        {"season": s, "team_code": r["code"], "def_lost": r["share"]}
        for s in seasons for r in defensive_turnover(s) if not r["promoted"]
    ]
    return pd.DataFrame(rows, columns=["season", "team_code", "def_lost"])


def leap_frame() -> pd.DataFrame:
    seasons = sorted(set(PlayerSeasonStat.objects.filter(competition_id=8).values_list("season", flat=True)))
    profiles = {s: {p["id"]: p for p in player_usage(s) if p["teamKnown"]} for s in seasons}
    rows = []
    for s in seasons:
        if s - 1 not in profiles:
            continue
        for pid, last in profiles[s].items():
            before = profiles[s - 1].get(pid)
            if not before or before["teamId"] != last["teamId"] or not str(pid).isdigit():
                continue
            if min(before["minutes"] or 0, last["minutes"] or 0) < 450:
                continue
            a, b = _profile(before), _profile(last)
            rise = lambda k: None if a[k] is None or b[k] is None else b[k] - a[k]
            # A rise from season s-1 to s is known before season s+1 starts.
            rows.append({"season": s + 1, "code": int(pid), "prev_usage_rise": rise("usage"), "prev_xgi_rise": rise("xgi90")})
    return pd.DataFrame(rows, columns=["season", "code", "prev_usage_rise", "prev_xgi_rise"])


def add_features(features: pd.DataFrame, fixtures: pd.DataFrame) -> pd.DataFrame:
    turnover = turnover_frame(sorted(features["season"].unique()))
    features = features.merge(turnover.rename(columns={"def_lost": "team_def_lost"}), on=["season", "team_code"], how="left")
    # Opponents' turnover, averaged over the week's fixtures.
    long = pd.concat([
        fixtures[["season", "gameweek", "team_h_code", "team_a_code"]].set_axis(["season", "gameweek", "team_code", "opp_code"], axis=1),
        fixtures[["season", "gameweek", "team_a_code", "team_h_code"]].set_axis(["season", "gameweek", "team_code", "opp_code"], axis=1),
    ], ignore_index=True)
    long["gameweek"] = long["gameweek"].astype(int)
    opp = long.merge(turnover.rename(columns={"team_code": "opp_code"}), on=["season", "opp_code"], how="left")
    opp = opp.groupby(["season", "gameweek", "team_code"])["def_lost"].mean().rename("opp_def_lost").reset_index()
    features = features.merge(opp, on=["season", "gameweek", "team_code"], how="left")

    features["xgi90_delta"] = (features["xg90_s"] + features["xa90_s"]) - (features["prev_xg90"] + features["prev_xa90"])
    features["min_share_delta"] = features["min_share_s"] - features["min_share_prev"]
    features = features.merge(leap_frame(), on=["season", "code"], how="left")
    return features


def weekly_abs_error(preds, mask=None):
    rows = preds.dropna(subset=["pred"])
    if mask is not None:
        rows = rows[mask(rows)]
    return rows.assign(err=(rows["pred"] - rows["total_points"]).abs()).groupby(["season", "gameweek"])["err"].mean()


def summarise(result):
    preds = result["_preds"]
    return {
        "summary": {
            "mae": result["accuracy"]["model_mae"],
            "corr": result["accuracy"]["model_corr"],
            "captain": result["captain"]["points_per_week"]["model"],
            "lineup": result["lineup"]["points_per_week"]["model"],
        },
        "mae": weekly_abs_error(preds),
        # Turnover should matter most early in the season and for defenders and keepers.
        "mae_early_def": weekly_abs_error(preds, lambda r: (r["gameweek"] <= 8) & r["position"].isin([1, 2])),
        "mae_early": weekly_abs_error(preds, lambda r: r["gameweek"] <= 8),
        # Leap features should matter most for players whose output moved a lot.
        "mae_movers": weekly_abs_error(preds, lambda r: r["xgi90_delta"].abs() >= 0.15),
        "captain": result["_picks"].set_index(["season", "gameweek"])["model_points"],
        "lineup": result["_lineups"].groupby(["season", "gameweek"])["model_points"].mean(),
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    players = load_players()
    players = players[players["season"] <= 2025]
    fixtures = load_fixtures()
    fixtures = fixtures[fixtures["season"] <= 2025]
    squads = elite_squads()
    features = add_features(build_features(players, fixtures), fixtures)
    quiet = lambda *_: None

    test = features[features["season"].isin(TEST) & features["total_points"].notna()]
    coverage = {
        "test_player_weeks": int(len(test)),
        **{f"with_{c}": round(float(test[c].notna().mean()), 3) for c in TURNOVER + LEAP},
    }

    runs = {}
    for name, extra in (("base", []), ("turnover", TURNOVER), ("leap", LEAP)):
        result = evaluate(players, fixtures, squads, features=features, feature_list=FEATURES + extra, log=quiet)
        runs[name] = summarise(result)
        del result
        gc.collect()
        print(f"done {name} {runs[name]['summary']}", flush=True)

    base = runs["base"]
    out = {"coverage": coverage, "base": base["summary"]}
    for name in ("turnover", "leap"):
        run = runs[name]
        paired = lambda key: (base[key] - run[key]).dropna().values
        out[name] = {
            **run["summary"],
            "paired": {
                "mae_reduction": _bootstrap(paired("mae"), rng),
                "mae_reduction_early": _bootstrap(paired("mae_early"), rng),
                "mae_reduction_early_def": _bootstrap(paired("mae_early_def"), rng),
                "mae_reduction_movers": _bootstrap(paired("mae_movers"), rng),
                "captain_points": _bootstrap((run["captain"] - base["captain"]).dropna().values, rng),
                "lineup_points": _bootstrap((run["lineup"] - base["lineup"]).dropna().values, rng),
            },
        }
    (HERE / "squad_changes_eval.json").write_text(json.dumps(out, indent=1))
    print("RESULT_JSON " + json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
