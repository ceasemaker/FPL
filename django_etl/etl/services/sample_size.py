"""How many league minutes a player needs before his per-90 numbers are ranked.

One rule for every page (Stats Explorer, the Player page's comparisons and
full stat sheet): 40% of the league minutes played so far (90 a gameweek),
never below 270, rounded to 10. About 290 at gameweek 8, 680 by Christmas,
1,370 by May. Players under 450 minutes are still ranked once they pass the
bar, but flagged as a small sample: per-90 rates swing on a few games.
"""
from __future__ import annotations

FLOOR = 270
SHARE = 0.4
SMALL_SAMPLE = 450


def qualifying_minutes(gameweeks_played: int) -> int:
    return max(FLOOR, int(round(SHARE * 90 * max(0, gameweeks_played) / 10.0)) * 10)
