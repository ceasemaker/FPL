"""Where the usage features are present and why they are missing (test seasons).

    cd django_etl && python ../analysis/points_forecast_report/usage_coverage.py
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

from etl.forecast.backtest import TEST_SEASONS  # noqa: E402
from etl.forecast.data import load_fixtures, load_players, load_usage  # noqa: E402
from etl.forecast.features import build_features  # noqa: E402


def main() -> None:
    players = load_players()
    players = players[players["season"] <= max(TEST_SEASONS)]
    features = build_features(players, load_fixtures(), load_usage())
    test = features[features["season"].isin(TEST_SEASONS) & features["total_points"].notna()]
    played_last = test["min_share_prev"].fillna(0) > 0  # had Premier League minutes last season
    has_usage = test["prev_usage"].notna()
    result = {
        "rows": int(len(test)),
        "with_usage": round(float(has_usage.mean()), 3),
        "missing_no_pl_minutes_last_season": round(float((~has_usage & ~played_last).mean()), 3),
        "missing_despite_pl_minutes_last_season": round(float((~has_usage & played_last).mean()), 3),
        "regulars_with_usage": round(float(test.loc[test["mins_m3"] >= 60, "prev_usage"].notna().mean()), 3),
    }
    print("RESULT_JSON " + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
