"""How Opta's "possession lost" relates to its itemised components.

For Premier League players with at least 1,500 minutes, compares
totalLossesOfPossession with the sum of unsuccessful passes (excluding
crosses and corners), unsuccessful crosses and corners, unsuccessful
dribbles, times tackled and overruns. Prints one RESULT_JSON line.

    cd django_etl && python ../analysis/points_forecast_report/possession_lost_check.py
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

from etl.models import PlayerSeasonStat  # noqa: E402

PARTS = ["totalUnsuccessfulPassesExclCrossesAndCorners", "unsuccessfulCrossesAndCorners",
         "unsuccessfulDribbles", "timesTackled", "overruns"]


def main() -> None:
    out = {}
    for season in (2023, 2024, 2025):
        ratios = []
        for stats in PlayerSeasonStat.objects.filter(source="sdp", competition_id=8, season=season).values_list("stats", flat=True):
            if float(stats.get("timePlayed") or 0) < 1500 or not stats.get("totalLossesOfPossession"):
                continue
            parts = sum(float(stats.get(k) or 0) for k in PARTS)
            if parts:
                ratios.append(float(stats["totalLossesOfPossession"]) / parts)
        r = np.array(ratios)
        out[season] = {"players": int(len(r)), "median": round(float(np.median(r)), 3),
                       "p05": round(float(np.percentile(r, 5)), 3), "p95": round(float(np.percentile(r, 95)), 3)}
    print("RESULT_JSON " + json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
