"""Captain and starting-XI choices, scored with FPL's ordinary rules.

Chips are ignored on purpose: every strategy is scored as a normal week (one
captain at x2, eleven starters, ordinary autosubs) so the comparison is about
the choices, not about when a chip was played.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

MIN_OUTFIELD = {2: 3, 3: 2, 4: 1}  # DEF, MID, FWD minimums in a legal XI
MAX_OUTFIELD = {2: 5, 3: 5, 4: 3}
FORMATIONS = [
    (d, m, f)
    for d, m, f in product(range(3, 6), range(2, 6), range(1, 4))
    if d + m + f == 10
]


@dataclass
class Player:
    code: int
    position: int  # 1 GK, 2 DEF, 3 MID, 4 FWD
    score: float  # what the strategy ranks by
    minutes: float  # what actually happened
    points: float


@dataclass
class Lineup:
    starters: list[Player]
    bench: list[Player]  # bench[0] is the reserve goalkeeper
    captain: Player
    vice: Player


def choose_lineup(squad: list[Player]) -> Lineup:
    """Best legal XI by score; captain and vice are the two highest scorers in it."""
    by_position = {p: sorted([x for x in squad if x.position == p], key=lambda x: -x.score) for p in (1, 2, 3, 4)}
    best, best_total = None, float("-inf")
    for d, m, f in FORMATIONS:
        if len(by_position[2]) < d or len(by_position[3]) < m or len(by_position[4]) < f or not by_position[1]:
            continue
        xi = [by_position[1][0], *by_position[2][:d], *by_position[3][:m], *by_position[4][:f]]
        total = sum(p.score for p in xi)
        if total > best_total:
            best, best_total = xi, total
    chosen = {id(p) for p in best}
    keepers = [p for p in by_position[1] if id(p) not in chosen]
    outfield = sorted([p for p in squad if id(p) not in chosen and p.position != 1], key=lambda x: -x.score)
    ranked = sorted(best, key=lambda x: -x.score)
    return Lineup(starters=best, bench=keepers[:1] + outfield, captain=ranked[0], vice=ranked[1])


def _legal(xi: list[Player]) -> bool:
    counts = {p: sum(1 for x in xi if x.position == p) for p in (1, 2, 3, 4)}
    return counts[1] == 1 and all(counts[p] >= MIN_OUTFIELD[p] for p in (2, 3, 4))


def score_lineup(lineup: Lineup) -> float:
    """Points for the week with ordinary autosubs and captaincy."""
    xi = list(lineup.starters)
    bench = list(lineup.bench)
    for index, starter in enumerate(list(xi)):
        if starter.minutes > 0:
            continue
        for sub in bench:
            if sub.minutes <= 0 or (starter.position == 1) != (sub.position == 1):
                continue
            trial = xi.copy()
            trial[index] = sub
            if _legal(trial):
                xi = trial
                bench.remove(sub)
                break
    total = sum(p.points for p in xi)
    if lineup.captain.minutes > 0:
        total += lineup.captain.points
    elif lineup.vice.minutes > 0 and any(p is lineup.vice for p in xi):
        total += lineup.vice.points
    return float(total)
