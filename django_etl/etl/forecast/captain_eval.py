"""Captain backtest: does the forecast pick better captains than simple rules?

Walk-forward over the test seasons (each week predicted by a model trained only
on earlier weeks), for two feature sets:

* ``v2``: the production forecast (FPL data, club strength, last season).
* ``v3``: v2 plus per-match Opta features (shots and shots in the box, big
  chances, touches in the box, chances created, corners, penalties taken).

Each week's captain from each rule is scored by the points that player
actually scored (single, not doubled). Comparators, as in the report:

* premium: the priciest midfielder or forward who played 60+ minutes last week;
* form: best six-week points per gameweek among regulars;
* form_scaled: that form times the coming week's fixture count (doubles count);
* regression: a walk-forward ridge on price, recent minutes, position, fixtures;
* elite: the eventual top-100 managers' most-captained player (reported only:
  chosen with hindsight and with team news, so not a pass condition).

**Pass** (decided before running, 24 Oct 2026): the chosen model beats premium,
form_scaled and regression, each with a 95% bootstrap lower bound above zero.
"""
from __future__ import annotations

import gc

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from .backtest import SEED, TEST_SEASONS, _bootstrap, walk_forward
from .data import load_fixtures, load_opta_gameweeks, load_players
from .features import FEATURES, FEATURES_V3, OPTA_FEATURES, build_features

PASS_BASELINES = ("premium", "form_scaled", "regression")
REPORTED = ("premium", "form", "form_scaled", "regression", "elite")
REG_COLUMNS = ["start_price", "mins_m3", "mins_l1", "n_fix", "pos_1", "pos_2", "pos_3", "pos_4"]
KEEP = ["season", "gameweek", "code", "web_name", "position", "start_price", "mins_l1", "mins_m3", "pts_m6",
        "n_fix", "total_points", "appearances"]


def regression_baseline(features: pd.DataFrame, test_seasons=TEST_SEASONS) -> pd.Series:
    """Walk-forward ridge on price, recent minutes, position and fixture count."""
    frame = features[["season", "gameweek", "position", "start_price", "mins_m3", "mins_l1", "n_fix",
                      "total_points", "appearances"]]
    frame = frame.assign(**{f"pos_{p}": (frame["position"] == p).astype(float) for p in (1, 2, 3, 4)})
    X = frame[REG_COLUMNS].astype(float).fillna(0.0)
    t = frame["season"] * 100 + frame["gameweek"]
    played = frame["total_points"].notna() & frame["appearances"].notna()
    out = pd.Series(np.nan, index=frame.index)
    weeks = sorted({(s, g) for s, g in frame.loc[frame["season"].isin(test_seasons), ["season", "gameweek"]].itertuples(index=False)})
    for season, gameweek in weeks:
        now = season * 100 + gameweek
        model = Ridge(alpha=1.0).fit(X[played & (t < now)], frame.loc[played & (t < now), "total_points"].astype(float))
        rows = (t == now) & frame["total_points"].notna()
        out[rows] = model.predict(X[rows])
    return out


def _top(frame: pd.DataFrame, column: str, tiebreak: str | None = None) -> int | None:
    frame = frame.dropna(subset=[column])
    if frame.empty:
        return None
    order = [column] + ([tiebreak] if tiebreak else []) + ["code"]
    ranked = frame.assign(**{tiebreak: frame[tiebreak].fillna(-1e9)} if tiebreak else {})
    return int(ranked.sort_values(order, ascending=[False] * (len(order) - 1) + [True]).iloc[0]["code"])


def weekly_picks(test: pd.DataFrame, squads: pd.DataFrame, models: list[str]) -> pd.DataFrame:
    elite = (squads[squads["is_captain"] == 1].groupby(["season", "gameweek", "code"]).size().rename("n").reset_index()
             .sort_values(["n", "code"], ascending=[False, True]).drop_duplicates(["season", "gameweek"])
             .set_index(["season", "gameweek"])["code"])
    rows = []
    for (season, gameweek), week in test.groupby(["season", "gameweek"]):
        points = week.set_index("code")["total_points"]
        names = week.set_index("code")["web_name"]
        regulars = week[week["mins_m3"] >= 60]
        attackers = week[(week["position"] >= 3) & (week["mins_l1"] >= 60)]
        picks = {m: _top(week, m) for m in models}
        picks.update({
            "premium": _top(attackers, "start_price", tiebreak="pts_m6"),
            "form": _top(regulars, "pts_m6"),
            "form_scaled": _top(regulars.assign(fs=regulars["pts_m6"] * regulars["n_fix"]), "fs"),
            "regression": _top(week, "reg"),
            "elite": int(elite[(season, gameweek)]) if (season, gameweek) in elite.index else None,
        })
        row = {"season": int(season), "gameweek": int(gameweek)}
        for rule, code in picks.items():
            row[f"{rule}_code"] = code
            row[f"{rule}_name"] = None if code is None else str(names.get(code))
            row[f"{rule}_points"] = None if code is None else float(points.get(code, 0))
        rows.append(row)
    return pd.DataFrame(rows)


def compare(weeks: pd.DataFrame, model: str, rng) -> dict:
    out = {}
    for base in REPORTED:
        diff = (weeks[f"{model}_points"] - weeks[f"{base}_points"]).dropna()
        by_season = {int(s): _bootstrap(g.values, rng) for s, g in
                     (weeks.assign(d=weeks[f"{model}_points"] - weeks[f"{base}_points"]).dropna(subset=["d"])
                      .groupby("season")["d"])}
        out[base] = {**_bootstrap(diff.values, rng), "by_season": by_season}
    return out


def run(log=print, test_seasons=TEST_SEASONS) -> dict:
    from ..services.forecast_sync import elite_squads

    rng = np.random.default_rng(SEED)
    players = load_players()
    last = max(test_seasons)
    players = players[players["season"] <= last]
    fixtures = load_fixtures()
    fixtures = fixtures[fixtures["season"] <= last]
    opta = load_opta_gameweeks()
    log(f"Opta player-gameweeks: {len(opta):,} ({sorted(opta['season'].unique().tolist()) if len(opta) else []})")
    features = build_features(players, fixtures, opta=opta)
    del players
    gc.collect()

    test_mask = features["season"].isin(test_seasons) & features["total_points"].notna()
    coverage = {
        "test_player_weeks": int(test_mask.sum()),
        "with_opta_features": round(float(features.loc[test_mask, "box_shots90_6"].notna().mean()), 3),
        "opta_seasons": sorted(int(s) for s in opta["season"].unique()) if len(opta) else [],
    }
    test = features.loc[test_mask, KEEP].copy()
    log("Regression baseline")
    test["reg"] = regression_baseline(features, test_seasons)[test_mask].values

    quiet = lambda *_: None
    for name, feature_list in (("v2", FEATURES), ("v3", FEATURES_V3)):
        log(f"Walk-forward {name}")
        preds = walk_forward(features, test_seasons, 1, quiet, feature_list=feature_list)
        test = test.merge(preds[["season", "gameweek", "code", "pred"]].rename(columns={"pred": name}),
                          on=["season", "gameweek", "code"], how="left")
        del preds
        gc.collect()

    scored = test.dropna(subset=["v2", "v3"])
    weekly_err = scored.assign(e2=(scored["v2"] - scored["total_points"]).abs(),
                               e3=(scored["v3"] - scored["total_points"]).abs()).groupby(["season", "gameweek"])[["e2", "e3"]].mean()
    accuracy = {
        "v2_mae": round(float((scored["v2"] - scored["total_points"]).abs().mean()), 4),
        "v3_mae": round(float((scored["v3"] - scored["total_points"]).abs().mean()), 4),
        "mae_reduction": _bootstrap((weekly_err["e2"] - weekly_err["e3"]).values, rng),
    }

    weeks = weekly_picks(test, elite_squads(), ["v2", "v3"])
    per_week = {rule: round(float(weeks[f"{rule}_points"].mean()), 3)
                for rule in ("v2", "v3", *REPORTED) if weeks[f"{rule}_points"].notna().any()}
    v3_vs_v2 = _bootstrap((weeks["v3_points"] - weeks["v2_points"]).dropna().values, rng)
    # Production uses v3 only if it is at least as accurate and picks captains at least as well.
    # (and only when most test weeks actually have the Opta features).
    chosen = "v3" if (coverage["with_opta_features"] >= 0.5 and accuracy["mae_reduction"]["low"] > -0.002
                      and v3_vs_v2["mean"] >= 0) else "v2"
    versus = compare(weeks, chosen, rng)
    passed = all(versus[b]["low"] > 0 for b in PASS_BASELINES)
    return {
        "test_seasons": list(test_seasons),
        "weeks": int(len(weeks)),
        "coverage": coverage,
        "accuracy": accuracy,
        "captain_points_per_week": per_week,
        "v3_vs_v2": v3_vs_v2,
        "chosen": chosen,
        "chosen_features": OPTA_FEATURES if chosen == "v3" else [],
        "versus": versus,
        "pass_baselines": list(PASS_BASELINES),
        "passed": passed,
        "recent_picks": weeks.tail(8)[["season", "gameweek", f"{chosen}_name", f"{chosen}_points"]].to_dict("records"),
    }
