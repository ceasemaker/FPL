"""Fixture model: projected goals and clean-sheet chances for every league fixture.

Each club gets an attack and a defence rating from its recent league matches:
expected goals for and against (mostly xG, a little actual goals), weighted
towards recent games, pulled towards average while there is little data, and
relative to the league average. A fixture's projected goals for each side are

    home goals = league home average x home attack x away defence
    away goals = league away average x away attack x home defence

and a side's clean-sheet chance is the chance the other side scores none
(Poisson: e^-goals).

The backtest walks through past seasons match by match, rating clubs only on
matches played before each kick-off, and compares the predictions with what
happened against two simple rules: the league average, and each club's
season-to-date goals for and against. The model is shown only when it is
clearly better at both clean sheets (Brier score) and goals (Poisson
deviance); the result is stored as ModelEvaluation "fixture_model".
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field

from django.core.cache import cache
from django.db.models import Max

from ..models import Fixture, MatchTeamStat, ModelEvaluation, PlMatch, Team

HALF_LIFE = 12          # matches: a game 12 matches ago counts half as much
PRIOR_MATCHES = 4       # shrink towards average as if 4 average matches were seen
GOALS_WEIGHT = 0.25     # blend of actual goals into xG
SEASON_CARRY = 0.6      # weight kept on last season's ratings at a new season
PROMOTED = (0.85, 1.2)  # attack, defence for a club with no league history
DECAY = 0.5 ** (1 / HALF_LIFE)
BACKTEST_SEASONS = (2023, 2024, 2025)


@dataclass
class Rating:
    att: float = 0.0     # weighted sums of (value / league average)
    dfn: float = 0.0
    weight: float = 0.0
    season: int | None = None

    def value(self, prior=(1.0, 1.0)):
        w = self.weight
        att = (self.att + PRIOR_MATCHES * prior[0]) / (w + PRIOR_MATCHES)
        dfn = (self.dfn + PRIOR_MATCHES * prior[1]) / (w + PRIOR_MATCHES)
        return att, dfn


@dataclass
class League:
    home_goals: float = 1.5
    away_goals: float = 1.2
    n: int = 0
    ratings: dict = field(default_factory=lambda: defaultdict(Rating))

    def predict(self, home: str, away: str) -> tuple[float, float]:
        ha, hd = self.ratings[home].value(self._prior(home))
        aa, ad = self.ratings[away].value(self._prior(away))
        return self.home_goals * ha * ad, self.away_goals * aa * hd

    def _prior(self, club):
        return (1.0, 1.0) if self.ratings[club].weight > 0 or self.ratings[club].season is not None else PROMOTED

    def update(self, season: int, home: str, away: str, home_xg: float, away_xg: float, hg: int, ag: int):
        for club in (home, away):
            r = self.ratings[club]
            if r.season is not None and r.season != season:  # new season: keep part of last season's view
                r.att *= SEASON_CARRY; r.dfn *= SEASON_CARRY; r.weight *= SEASON_CARRY
            r.season = season
        h_for = (1 - GOALS_WEIGHT) * home_xg + GOALS_WEIGHT * hg
        a_for = (1 - GOALS_WEIGHT) * away_xg + GOALS_WEIGHT * ag
        avg = (self.home_goals + self.away_goals) / 2
        for club, scored, conceded in ((home, h_for, a_for), (away, a_for, h_for)):
            r = self.ratings[club]
            r.att = r.att * DECAY + scored / avg
            r.dfn = r.dfn * DECAY + conceded / avg
            r.weight = r.weight * DECAY + 1
        # League averages drift slowly with the matches seen.
        self.n += 1
        k = 1 / min(self.n + 20, 380)  # starts from 20 matches' worth of the default averages
        self.home_goals += k * (h_for - self.home_goals)
        self.away_goals += k * (a_for - self.away_goals)


def _matches():
    """League matches in kick-off order with both sides' xG (None when not loaded)."""
    xg = defaultdict(dict)
    for match_id, team_id, stats in MatchTeamStat.objects.filter(match__competition_id=PlMatch.PREMIER_LEAGUE).values_list("match_id", "team_id", "stats"):
        if stats.get("expectedGoals") is not None:
            xg[match_id][team_id] = float(stats["expectedGoals"])
    rows = []
    for m in PlMatch.objects.filter(competition_id=PlMatch.PREMIER_LEAGUE, home_score__isnull=False, kickoff__isnull=False).order_by("kickoff"):
        pair = xg.get(m.id, {})
        rows.append((m.season, m.home_team_id, m.away_team_id, pair.get(m.home_team_id), pair.get(m.away_team_id), m.home_score, m.away_score))
    return rows


def fit(rows) -> League:
    league = League()
    for season, h, a, hxg, axg, hg, ag in rows:
        league.update(season, h, a, hxg if hxg is not None else hg, axg if axg is not None else ag, hg, ag)
    return league


# ------------------------------------------------------------------ backtest

def _poisson_deviance(y: int, mu: float) -> float:
    mu = max(mu, 1e-6)
    return 2 * ((y * math.log(y / mu) if y > 0 else 0.0) - (y - mu))


def backtest(save: bool = True) -> dict:
    rows = _matches()
    league = League()
    # Simple rules: league average to date, and each club's season-to-date goals.
    avg = {"h": 1.5, "a": 1.2, "n": 0}
    table = defaultdict(lambda: {"for": 0.0, "against": 0.0, "n": 0})
    scored = []  # per side: (model_cs, avg_cs, table_cs, cs_actual, model_mu, avg_mu, table_mu, goals)
    for season, h, a, hxg, axg, hg, ag in rows:
        if season in BACKTEST_SEASONS:
            mh, ma = league.predict(h, a)
            th, ta = table[(season, h)], table[(season, a)]
            def season_rate(t, key, fallback):
                return (t[key] + 3 * fallback) / (t["n"] + 3)  # three average matches of prior
            tbl_h = avg["h"] * season_rate(th, "for", avg["h"]) / avg["h"] * season_rate(ta, "against", avg["h"]) / avg["h"]
            tbl_a = avg["a"] * season_rate(ta, "for", avg["a"]) / avg["a"] * season_rate(th, "against", avg["a"]) / avg["a"]
            # side = the team keeping the clean sheet; mu = goals scored against it
            scored.append((math.exp(-ma), math.exp(-avg["a"]), math.exp(-tbl_a), int(ag == 0), mh, avg["h"], tbl_h, hg))
            scored.append((math.exp(-mh), math.exp(-avg["h"]), math.exp(-tbl_h), int(hg == 0), ma, avg["a"], tbl_a, ag))
        league.update(season, h, a, hxg if hxg is not None else hg, axg if axg is not None else ag, hg, ag)
        avg["n"] += 1
        k = 1 / min(avg["n"] + 20, 380)
        avg["h"] += k * (hg - avg["h"]); avg["a"] += k * (ag - avg["a"])
        for club, f, ag_ in ((h, hg, ag), (a, ag, hg)):
            t = table[(season, club)]
            t["for"] += f; t["against"] += ag_; t["n"] += 1
    if len(scored) < 500:
        result = {"accepted": False, "reason": f"Only {len(scored) // 2} matches to test on."}
        if save:
            ModelEvaluation.objects.create(name="fixture_model", version="v1", accepted=False, summary=result)
        return result

    def brier(i):
        return [(r[i] - r[3]) ** 2 for r in scored]

    def dev(i):
        return [_poisson_deviance(r[7], r[i]) for r in scored]

    def compare(model, base, seed):
        diffs = [b - m for m, b in zip(model, base)]  # positive = model better
        rng = random.Random(seed)
        means = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(300))
        return {"model": round(sum(model) / len(model), 4), "rule": round(sum(base) / len(base), 4),
                "gain": round(sum(diffs) / len(diffs), 4), "low": round(means[7], 4), "high": round(means[292], 4)}

    cs_m, gl_m = brier(0), dev(4)
    result = {
        "matches": len(scored) // 2, "seasons": [f"{s}/{(s + 1) % 100:02d}" for s in BACKTEST_SEASONS],
        "cleanSheets": {"vsLeagueAverage": compare(cs_m, brier(1), 1), "vsSeasonTable": compare(cs_m, brier(2), 2)},
        "goals": {"vsLeagueAverage": compare(gl_m, dev(5), 3), "vsSeasonTable": compare(gl_m, dev(6), 4)},
        "calibration": _calibration(scored),
        "settings": {"halfLife": HALF_LIFE, "priorMatches": PRIOR_MATCHES, "goalsWeight": GOALS_WEIGHT, "seasonCarry": SEASON_CARRY},
    }
    result["accepted"] = all(c["low"] > 0 for part in ("cleanSheets", "goals") for c in result[part].values())
    if save:
        ModelEvaluation.objects.create(name="fixture_model", version="v1", accepted=result["accepted"], summary=result)
        cache.delete(CACHE_KEY)
    return result


def _calibration(scored) -> list[dict]:
    """Clean-sheet chances in bands against how often clean sheets happened."""
    bands = [(0, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 1.01)]
    out = []
    for lo, hi in bands:
        rows = [r for r in scored if lo <= r[0] < hi]
        if rows:
            out.append({"band": f"{int(lo * 100)}–{min(int(hi * 100), 100)}%", "predicted": round(sum(r[0] for r in rows) / len(rows), 3),
                        "actual": round(sum(r[3] for r in rows) / len(rows), 3), "n": len(rows)})
    return out


# ------------------------------------------------------------------ today's projections

CACHE_KEY = "fixture-model:projections:v1"


def projections() -> dict | None:
    """Projected goals and clean-sheet chance per remaining fixture (FPL fixture id),
    or None when the latest backtest didn't accept the model."""
    ev = ModelEvaluation.objects.filter(name="fixture_model").order_by("-created_at").first()
    if not ev or not ev.accepted:
        return None
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached
    league = fit(_matches())
    codes = {t.id: str(t.code) for t in Team.objects.exclude(code=None)}
    out = {}
    for f in Fixture.objects.filter(finished=False, team_h__isnull=False, team_a__isnull=False):
        h, a = codes.get(f.team_h_id), codes.get(f.team_a_id)
        if not h or not a:
            continue
        gh, ga = league.predict(h, a)
        out[str(f.id)] = {"homeGoals": round(gh, 2), "awayGoals": round(ga, 2),
                          "homeCleanSheet": round(math.exp(-ga), 3), "awayCleanSheet": round(math.exp(-gh), 3)}
    payload = {"fixtures": out, "record": ev.summary}
    cache.set(CACHE_KEY, payload, 6 * 60 * 60)
    return payload
