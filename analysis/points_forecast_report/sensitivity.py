"""Sensitivity and ablation runs for the points-forecast report.

Each variant re-runs the full walk-forward backtest (weekly retraining,
2023/24-2025/26) with one choice changed: a block of features removed, or a
model setting moved. Results go to sensitivity.json next to this file.

    cd django_etl && python ../analysis/points_forecast_report/sensitivity.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "django_etl"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fpl_platform.settings")

import django  # noqa: E402

django.setup()

from etl.forecast.backtest import evaluate  # noqa: E402
from etl.forecast.data import load_fixtures, load_players  # noqa: E402
from etl.forecast.features import FEATURES, build_features  # noqa: E402
from etl.services.forecast_sync import elite_squads  # noqa: E402

BLOCKS = {
    "prior season": ["prev_xg90", "prev_xa90", "pts90_prev", "min_share_prev"],
    "club and opponent strength": ["team_xgf", "team_xga", "opp_xgf", "opp_xga"],
    "per-90 rates (last six)": ["xg90_6", "xa90_6", "bonus90_6", "bps90_6", "saves90_6"],
    "season to date": ["xg90_s", "xa90_s", "pts90_s", "min_share_s", "fix_s"],
    "minutes and starts": ["mins_l1", "mins_m3", "mins_m6", "start_r6"],
}
SETTINGS = {
    "learning rate 0.1, 125 iterations": {"learning_rate": 0.1, "max_iter": 125},
    "15 leaves per tree": {"max_leaf_nodes": 15},
    "63 leaves per tree": {"max_leaf_nodes": 63},
    "20 observations per leaf": {"min_samples_leaf": 20},
    "library defaults": {"learning_rate": 0.1, "max_iter": 100, "max_leaf_nodes": 31,
                         "min_samples_leaf": 20, "l2_regularization": 0.0},
}


def brief(result: dict) -> dict:
    return {
        "mae": result["accuracy"]["model_mae"],
        "corr": result["accuracy"]["model_corr"],
        "captain": result["captain"]["points_per_week"]["model"],
        "versus": {k: v for k, v in result["captain"]["versus"].items()},
        "lineup": result["lineup"]["points_per_week"]["model"],
        "lineup_versus": result["lineup"]["versus"],
    }


def main() -> None:
    players = load_players()
    players = players[players["season"] <= 2025]
    fixtures = load_fixtures()
    squads = elite_squads()
    features = build_features(players, fixtures)
    quiet = lambda *_: None
    out = {"baseline": brief(evaluate(players, fixtures, squads, features=features, log=quiet))}
    print("baseline", out["baseline"]["captain"], flush=True)
    for name, dropped in BLOCKS.items():
        keep = [f for f in FEATURES if f not in dropped]
        out[f"without {name}"] = brief(evaluate(players, fixtures, squads, features=features, feature_list=keep, log=quiet))
        print(name, out[f"without {name}"]["captain"], flush=True)
    for name, params in SETTINGS.items():
        out[name] = brief(evaluate(players, fixtures, squads, features=features, params=params, log=quiet))
        print(name, out[name]["captain"], flush=True)
    (HERE / "sensitivity.json").write_text(json.dumps(out, indent=1))
    # One line, so the result survives in job logs on a server with no persistent disk.
    print("RESULT_JSON " + json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
