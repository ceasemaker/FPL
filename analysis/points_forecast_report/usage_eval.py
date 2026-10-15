"""Does last season's ball usage improve the points forecast?

Runs the walk-forward backtest twice on identical weeks: the base model
(v2.0 features) and the base model plus last season's usage profile (v2.1).
Differences are paired by gameweek and bootstrapped over gameweeks.
Results go to usage_eval.json next to this file.

    cd django_etl && python ../analysis/points_forecast_report/usage_eval.py
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

from etl.forecast.backtest import SEED, _bootstrap, evaluate  # noqa: E402
from etl.forecast.data import load_fixtures, load_players, load_usage  # noqa: E402
from etl.forecast.features import FEATURES, FEATURES_V21, build_features  # noqa: E402
from etl.services.forecast_sync import elite_squads  # noqa: E402


def weekly_abs_error(preds):
    rows = preds.dropna(subset=["pred"])
    return rows.assign(err=(rows["pred"] - rows["total_points"]).abs()).groupby(["season", "gameweek"])["err"].mean()


def main() -> None:
    rng = np.random.default_rng(SEED)
    players = load_players()
    players = players[players["season"] <= 2025]
    fixtures = load_fixtures()
    squads = elite_squads()
    usage = load_usage()
    features = build_features(players, fixtures, usage)
    quiet = lambda *_: None
    base = evaluate(players, fixtures, squads, features=features, feature_list=FEATURES, log=quiet)
    plus = evaluate(players, fixtures, squads, features=features, feature_list=FEATURES_V21, log=quiet)

    test = features[features["season"].isin([2023, 2024, 2025]) & features["total_points"].notna()]
    coverage = {
        "test_player_weeks": int(len(test)),
        "with_prev_usage": round(float(test["prev_usage"].notna().mean()), 3),
        "moved_club_share": round(float((test["moved_club"] == 1).mean()), 3),
        "usage_seasons": sorted(int(s) for s in usage["season"].unique()),
    }

    # Accuracy: weekly mean absolute error, base minus plus (positive = usage helps).
    mae_gain = weekly_abs_error(base["_preds"]) - weekly_abs_error(plus["_preds"])
    movers = lambda p: p[p["code"].isin(test.loc[test["moved_club"] == 1, "code"]) & (p["moved_club"] == 1)]
    mover_gain = (weekly_abs_error(movers(base["_preds"])) - weekly_abs_error(movers(plus["_preds"]))).dropna()
    captain_gain = plus["_picks"].set_index(["season", "gameweek"])["model_points"] - base["_picks"].set_index(["season", "gameweek"])["model_points"]
    lineup_gain = (plus["_lineups"].groupby(["season", "gameweek"])["model_points"].mean()
                   - base["_lineups"].groupby(["season", "gameweek"])["model_points"].mean())

    def summary(result):
        return {
            "mae": result["accuracy"]["model_mae"],
            "corr": result["accuracy"]["model_corr"],
            "captain": result["captain"]["points_per_week"]["model"],
            "captain_versus": result["captain"]["versus"],
            "lineup": result["lineup"]["points_per_week"]["model"],
            "lineup_versus": result["lineup"]["versus"],
        }

    out = {
        "coverage": coverage,
        "base": summary(base),
        "with_usage": summary(plus),
        "paired": {
            "mae_reduction": _bootstrap(mae_gain.values, rng),
            "mae_reduction_movers": _bootstrap(mover_gain.values, rng),
            "captain_points": _bootstrap(captain_gain.values, rng),
            "lineup_points": _bootstrap(lineup_gain.values, rng),
        },
    }
    (HERE / "usage_eval.json").write_text(json.dumps(out, indent=1))
    print("RESULT_JSON " + json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
