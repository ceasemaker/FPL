"""Robustness analyses requested in review.

One walk-forward run of the reference model (2023/24-2025/26, weekly
retraining), plus:

* two further comparators: recent form scaled by the coming week's fixture
  count, and a walk-forward ridge regression on price, recent minutes,
  position and fixture count;
* season-by-season intervals and a within-season moving-block bootstrap;
* weekly rank correlation, RMSE and calibration, overall and by subgroup;
* lineup points split into the eleven and the armband;
* results on regular weeks (every club plays once) versus blank/double weeks;
* realised boosting iterations; where the usage features are missing.

Prints one RESULT_JSON line and one WEEK_JSON line per test week, so results
survive on a server without persistent disk. Also writes robustness.json and
robustness_weeks.csv next to this file when run locally.

    cd django_etl && python ../analysis/points_forecast_report/robustness.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "django_etl"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fpl_platform.settings")

import django  # noqa: E402

django.setup()

import pandas as pd  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402

from etl.forecast.backtest import SEED, TEST_SEASONS, walk_forward  # noqa: E402
from etl.forecast.data import load_fixtures, load_players  # noqa: E402
from etl.forecast.features import build_features, team_weeks  # noqa: E402
from etl.forecast.selection import Lineup, Player, choose_lineup, score_lineup_parts  # noqa: E402
from etl.services.forecast_sync import elite_squads  # noqa: E402

DRAWS = 10_000
REG_COLUMNS = ["start_price", "mins_m3", "mins_l1", "n_fix", "pos_1", "pos_2", "pos_3", "pos_4"]


def regression_baseline(features: pd.DataFrame) -> pd.Series:
    """Walk-forward ridge on price, recent minutes, position and fixture count."""
    frame = features.assign(**{f"pos_{p}": (features["position"] == p).astype(float) for p in (1, 2, 3, 4)})
    X = frame[REG_COLUMNS].astype(float).fillna(0.0)
    t = frame["season"] * 100 + frame["gameweek"]
    played = frame["total_points"].notna() & frame["appearances"].notna()
    out = pd.Series(np.nan, index=frame.index)
    for season, gameweek in sorted({(s, g) for s, g in frame.loc[frame["season"].isin(TEST_SEASONS), ["season", "gameweek"]].itertuples(index=False)}):
        now = season * 100 + gameweek
        train = played & (t < now)
        model = Ridge(alpha=1.0).fit(X[train], frame.loc[train, "total_points"].astype(float))
        rows = (t == now) & frame["total_points"].notna()
        out[rows] = model.predict(X[rows])
    return out


def iid_interval(values: np.ndarray, rng) -> dict:
    values = np.asarray(values, dtype=float)
    draws = values[rng.integers(0, len(values), size=(DRAWS, len(values)))].mean(axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"mean": round(float(values.mean()), 3), "low": round(float(lo), 3), "high": round(float(hi), 3), "n": int(len(values))}


def block_interval(frame: pd.DataFrame, column: str, block: int, rng) -> dict:
    """Moving-block bootstrap within each season (blocks never cross a season boundary)."""
    seasons = [g[column].to_numpy(dtype=float) for _, g in frame.groupby("season")]
    means = np.empty(DRAWS)
    for d in range(DRAWS):
        sample = []
        for values in seasons:
            n = len(values)
            starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
            sample.append(np.concatenate([values[s:s + block] for s in starts])[:n])
        means[d] = np.concatenate(sample).mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"block": block, "low": round(float(lo), 3), "high": round(float(hi), 3)}


def main() -> None:
    rng = np.random.default_rng(SEED)
    players = load_players()
    players = players[players["season"] <= max(TEST_SEASONS)]
    fixtures = load_fixtures()
    squads = elite_squads()
    features = build_features(players, fixtures)
    preds = walk_forward(features, log=lambda *_: None)
    iterations = preds.attrs.get("iterations", [])
    import gc
    gc.collect()
    features["reg"] = regression_baseline(features)
    preds = preds.merge(features[["season", "gameweek", "code", "reg"]], on=["season", "gameweek", "code"], how="left")
    preds["form"] = preds["pts_m6"].fillna(preds["pts90_prev"].fillna(0) * preds["min_share_prev"].fillna(0))
    preds["form_scaled"] = preds["form"] * preds["n_fix"]
    scored = preds.dropna(subset=["pred"]).copy()

    # Regular weeks: every club plays exactly once (no blank or double gameweek).
    weeks_tbl = team_weeks(players, fixtures)
    irregular = set(map(tuple, weeks_tbl.loc[weeks_tbl["n_fix"] != 1, ["season", "gameweek"]].drop_duplicates().to_numpy()))
    all_clubs = players.groupby(["season", "gameweek"])["team_code"].nunique()
    for (season, gameweek), clubs in all_clubs.items():
        fixtures_week = weeks_tbl[(weeks_tbl["season"] == season) & (weeks_tbl["gameweek"] == gameweek)]
        if len(fixtures_week) < 20:
            irregular.add((season, gameweek))

    # ------------------------------------------------------------ accuracy
    def accuracy(frame: pd.DataFrame) -> dict:
        out = {"n": int(len(frame))}
        for name in ("pred", "form", "form_scaled", "reg"):
            err = frame[name] - frame["total_points"]
            out[name] = {"mae": round(float(err.abs().mean()), 3), "rmse": round(float(np.sqrt((err ** 2).mean())), 3),
                         "corr": round(float(frame[name].corr(frame["total_points"])), 3)}
        return out

    def weekly_rank(frame: pd.DataFrame, name: str) -> float:
        rho = frame.groupby(["season", "gameweek"])[[name, "total_points"]].apply(lambda g: g[name].corr(g["total_points"], method="spearman"))
        return round(float(rho.mean()), 3)

    candidates = scored[scored["mins_m3"] >= 60]
    weekly_err = scored.assign(**{f"e_{n}": (scored[n] - scored["total_points"]).abs() for n in ("pred", "form_scaled", "reg")}) \
        .groupby(["season", "gameweek"])[["e_pred", "e_form_scaled", "e_reg"]].mean()
    calib = np.polyfit(scored["pred"], scored["total_points"], 1)
    deciles = scored.assign(bin=pd.qcut(scored["pred"], 10, labels=False, duplicates="drop")).groupby("bin")[["pred", "total_points"]].mean().round(3)
    result = {
        "iterations": {"min": int(min(iterations)), "median": float(np.median(iterations)), "max": int(max(iterations)), "fits": len(iterations)},
        "accuracy": {
            "all": accuracy(scored),
            "candidates_mins60": accuracy(candidates),
            "weekly_spearman_all": {n: weekly_rank(scored, n) for n in ("pred", "form", "form_scaled", "reg")},
            "weekly_spearman_candidates": {n: weekly_rank(candidates, n) for n in ("pred", "form", "form_scaled", "reg")},
            "paired_weekly_mae_gain": {
                "vs_form_scaled": iid_interval((weekly_err["e_form_scaled"] - weekly_err["e_pred"]).values, rng),
                "vs_regression": iid_interval((weekly_err["e_reg"] - weekly_err["e_pred"]).values, rng),
            },
            "calibration": {"slope": round(float(calib[0]), 3), "intercept": round(float(calib[1]), 3),
                            "deciles": deciles.reset_index().to_dict("records")},
            "by_position": {int(p): accuracy(g) for p, g in scored.groupby("position")},
            "by_season": {int(s): accuracy(g) for s, g in scored.groupby("season")},
            "early_gw1_8": accuracy(scored[scored["gameweek"] <= 8]),
            "later_gw9_38": accuracy(scored[scored["gameweek"] > 8]),
            "double_fixture": accuracy(scored[scored["n_fix"] == 2]),
            "single_fixture": accuracy(scored[scored["n_fix"] == 1]),
        },
    }

    # ------------------------------------------------------------- captain
    cap_elite = (squads[squads["is_captain"] == 1].groupby(["season", "gameweek", "code"]).size().rename("n").reset_index()
                 .sort_values(["n", "code"], ascending=[False, True]).drop_duplicates(["season", "gameweek"])
                 .set_index(["season", "gameweek"])["code"])
    week_rows = []
    for (season, gameweek), week in preds.groupby(["season", "gameweek"]):
        points = week.set_index("code")["total_points"]

        def top(frame, column, tiebreak=None):
            frame = frame.dropna(subset=[column])
            if frame.empty:
                return None
            order = [column] + ([tiebreak] if tiebreak else []) + ["code"]
            ranked = frame.assign(**{tiebreak: frame[tiebreak].fillna(-1e9)} if tiebreak else {})
            return int(ranked.sort_values(order, ascending=[False] * (len(order) - 1) + [True]).iloc[0]["code"])

        regulars = week[week["mins_m3"] >= 60]
        attackers = week[(week["position"] >= 3) & (week["mins_l1"] >= 60)]
        picks = {
            "model": top(week, "pred"),
            "form": top(regulars, "pts_m6"),
            "form_scaled": top(regulars.assign(fs=regulars["pts_m6"] * regulars["n_fix"]), "fs"),
            "regression": top(week, "reg"),
            "premium": top(attackers, "start_price", tiebreak="pts_m6"),
            "elite": int(cap_elite[(season, gameweek)]) if (season, gameweek) in cap_elite.index else None,
        }
        row = {"season": int(season), "gameweek": int(gameweek), "regular": (season, gameweek) not in irregular}
        for k, code in picks.items():
            row[f"{k}_code"] = code
            row[f"{k}_points"] = None if code is None else float(points.get(code, 0))
        week_rows.append(row)
    weeks = pd.DataFrame(week_rows)

    captain = {"points_per_week": {k: round(float(weeks[f"{k}_points"].mean()), 3) for k in
                                   ("model", "form", "form_scaled", "regression", "premium", "elite")}}
    for base in ("form", "form_scaled", "regression", "premium", "elite"):
        diff = weeks.assign(d=weeks["model_points"] - weeks[f"{base}_points"]).dropna(subset=["d"])
        captain[f"vs_{base}"] = {
            "iid": iid_interval(diff["d"].values, rng),
            "blocks": [block_interval(diff, "d", b, rng) for b in (3, 6)],
            "by_season": {int(s): iid_interval(g["d"].values, rng) for s, g in diff.groupby("season")},
            "regular_weeks": iid_interval(diff.loc[diff["regular"], "d"].values, rng),
            "irregular_weeks": iid_interval(diff.loc[~diff["regular"], "d"].values, rng) if (~diff["regular"]).sum() > 1 else None,
            "lag1_autocorr": round(float(diff.groupby("season")["d"].apply(lambda s: s.autocorr(1)).mean()), 3),
        }
    result["captain"] = captain
    result["weeks"] = {"total": int(len(weeks)), "regular": int(weeks["regular"].sum()), "irregular": int((~weeks["regular"]).sum())}

    # -------------------------------------------------------------- lineup
    lookup = preds.set_index(["season", "gameweek", "code"])[["pred", "form", "form_scaled", "reg"]]
    actual = players.set_index(["season", "gameweek", "code"])[["minutes", "total_points"]]
    sq = squads[squads["season"].isin(TEST_SEASONS)].join(lookup, on=["season", "gameweek", "code"]).join(actual, on=["season", "gameweek", "code"])
    sq[["minutes", "total_points"]] = sq[["minutes", "total_points"]].fillna(0)
    sq[["pred", "form", "form_scaled", "reg"]] = sq[["pred", "form", "form_scaled", "reg"]].fillna(0)
    rows = []
    for (season, gameweek, manager), squad in sq.groupby(["season", "gameweek", "manager"]):
        squad = squad.sort_values("slot")
        recs = list(squad.itertuples(index=False))

        def by(column):
            return [Player(int(r.code), int(r.position), float(getattr(r, column)), float(r.minutes), float(r.total_points)) for r in recs]

        manual = by("pred")
        captain_p = next(p for p, r in zip(manual, recs) if r.is_captain)
        vice_p = next(p for p, r in zip(manual, recs) if r.is_vice_captain)
        row = {"season": season, "gameweek": gameweek}
        for name, lineup in (("manager", Lineup(manual[:11], manual[11:], captain_p, vice_p)),
                             ("model", choose_lineup(by("pred"))), ("form", choose_lineup(by("form"))),
                             ("form_scaled", choose_lineup(by("form_scaled"))), ("regression", choose_lineup(by("reg")))):
            eleven, armband = score_lineup_parts(lineup)
            row[f"{name}_xi"], row[f"{name}_arm"] = eleven, armband
        rows.append(row)
    lineups = pd.DataFrame(rows).groupby(["season", "gameweek"]).mean().reset_index()
    lineup = {"per_week": {}}
    for name in ("model", "manager", "form", "form_scaled", "regression"):
        lineup["per_week"][name] = {"eleven": round(float(lineups[f"{name}_xi"].mean()), 3),
                                    "armband": round(float(lineups[f"{name}_arm"].mean()), 3)}
    for base in ("manager", "form", "form_scaled", "regression"):
        lineup[f"vs_{base}"] = {
            "total": iid_interval((lineups["model_xi"] + lineups["model_arm"] - lineups[f"{base}_xi"] - lineups[f"{base}_arm"]).values, rng),
            "eleven": iid_interval((lineups["model_xi"] - lineups[f"{base}_xi"]).values, rng),
            "armband": iid_interval((lineups["model_arm"] - lineups[f"{base}_arm"]).values, rng),
        }
    result["lineup"] = lineup

    print("RESULT_JSON " + json.dumps(result), flush=True)
    for record in weeks.replace({np.nan: None}).to_dict("records"):
        print("WEEK_JSON " + json.dumps(record), flush=True)
    try:
        (HERE / "robustness.json").write_text(json.dumps(result, indent=1))
        weeks.to_csv(HERE / "robustness_weeks.csv", index=False)
    except OSError:
        pass


if __name__ == "__main__":
    main()
