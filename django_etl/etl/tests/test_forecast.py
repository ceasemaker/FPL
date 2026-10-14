from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd
from django.test import TestCase
from django.utils import timezone

from ..forecast.backtest import _bootstrap, captain_picks
from ..forecast.features import build_features, future_rows
from ..forecast.selection import Player, choose_lineup, score_lineup
from ..forecast.service import log_picks, settle_picks
from ..models import (
    Athlete,
    AthleteStat,
    DeadlineSnapshot,
    ForecastPrediction,
    GameweekHistory,
    GameweekSummary,
    ModelEvaluation,
    ShadowPick,
    Team,
)
from ..services.forecast_sync import next_deadline


def synthetic_season(season=2024, weeks=8, teams=4, per_team=6, seed=1):
    """A tiny league: every team plays every week, players score at random."""
    rng = np.random.default_rng(seed)
    players, fixtures = [], []
    for gw in range(1, weeks + 1):
        order = rng.permutation(teams)
        for h, a in zip(order[::2], order[1::2]):
            fixtures.append({"season": season, "gameweek": gw, "team_h_code": int(h), "team_a_code": int(a),
                             "team_h_score": 1, "team_a_score": 0, "kickoff_time": None})
        for team in range(teams):
            for slot in range(per_team):
                code = team * 100 + slot
                minutes = 90 if slot < 4 else int(rng.integers(0, 2)) * 30
                players.append({
                    "season": season, "gameweek": gw, "code": code, "element": code, "web_name": f"P{code}",
                    "team_code": team, "position": 1 + slot % 4, "start_price": 5.0 + slot,
                    "minutes": minutes, "starts": int(minutes >= 60), "goals_scored": 0, "assists": 0,
                    "clean_sheets": 0, "goals_conceded": 0, "saves": 0, "bonus": 0, "bps": 10,
                    "expected_goals": float(rng.random() * slot / 5), "expected_assists": 0.1,
                    "expected_goals_conceded": 1.0, "total_points": int(rng.integers(0, 10)) if minutes else 0,
                })
    return pd.DataFrame(players), pd.DataFrame(fixtures)


class FeatureLeakageTests(TestCase):
    def test_features_only_use_earlier_weeks(self):
        players, fixtures = synthetic_season()
        before = build_features(players, fixtures)
        changed = players.copy()
        late = changed["gameweek"] == 6
        changed.loc[late, "total_points"] = 99
        changed.loc[late, "expected_goals"] = 5.0
        after = build_features(changed, fixtures)
        cols = [c for c in before.columns if c not in ("total_points",)]
        early_before = before[before["gameweek"] <= 6][cols].reset_index(drop=True)
        early_after = after[after["gameweek"] <= 6][cols].reset_index(drop=True)
        pd.testing.assert_frame_equal(early_before, early_after)
        # ...and week 7 does see week 6.
        self.assertFalse(before[before["gameweek"] == 7]["pts_m3"].equals(after[after["gameweek"] == 7]["pts_m3"]))

    def test_future_rows_get_features_without_targets(self):
        players, fixtures = synthetic_season(weeks=8)
        history = players[players["gameweek"] <= 6]
        future = future_rows(history, 2024, [7, 8])
        features = build_features(pd.concat([history, future], ignore_index=True), fixtures)
        upcoming = features[features["gameweek"].isin([7, 8])]
        self.assertTrue(upcoming["total_points"].isna().all())
        self.assertTrue(upcoming["pts_m3"].notna().all())
        # Week 8 forecasts reuse the state after week 6, the last played week.
        week7 = upcoming[upcoming["gameweek"] == 7].set_index("code")["pts_m6"]
        week8 = upcoming[upcoming["gameweek"] == 8].set_index("code")["pts_m6"]
        pd.testing.assert_series_equal(week7, week8)

    def test_previous_season_rates_become_priors(self):
        a, fa = synthetic_season(season=2023, seed=2)
        b, fb = synthetic_season(season=2024, seed=3)
        features = build_features(pd.concat([a, b]), pd.concat([fa, fb]))
        first_week = features[(features["season"] == 2024) & (features["gameweek"] == 1)]
        self.assertTrue(first_week["prev_xg90"].notna().all())
        self.assertTrue(first_week["xg90_s"].isna().all(), "no season-to-date numbers before a ball is kicked")


class ModelFitTests(TestCase):
    def test_fit_skips_empty_and_constant_columns(self):
        from ..forecast.model import fit, predict

        players, fixtures = synthetic_season()
        features = build_features(players, fixtures)  # one season: no prior-season rates
        model = fit(features)
        self.assertNotIn("prev_xg90", model.columns)
        self.assertNotIn("dc_era", model.columns)
        self.assertEqual(len(predict(model, features)), len(features))


class SelectionTests(TestCase):
    def squad(self):
        spec = [(1, 5, 90), (1, 1, 90)] + [(2, s, 90) for s in (6, 5, 4, 3, 2)] + \
               [(3, s, 90) for s in (9, 8, 7, 6, 1)] + [(4, s, 90) for s in (10, 3, 2)]
        return [Player(code=i, position=p, score=s, minutes=m, points=s) for i, (p, s, m) in enumerate(spec)]

    def test_lineup_is_legal_and_captains_the_top_score(self):
        lineup = choose_lineup(self.squad())
        positions = [p.position for p in lineup.starters]
        self.assertEqual(len(lineup.starters), 11)
        self.assertEqual(positions.count(1), 1)
        self.assertGreaterEqual(positions.count(2), 3)
        self.assertEqual(lineup.captain.score, 10)
        self.assertEqual(lineup.bench[0].position, 1, "reserve keeper sits first on the bench")

    def test_autosub_keeps_formation_and_vice_takes_the_armband(self):
        from ..forecast.selection import Lineup

        def p(code, pos, points, minutes=90):
            return Player(code=code, position=pos, score=0, minutes=minutes, points=points)

        gk, d1, d2, d3 = p(1, 1, 2), p(2, 2, 2), p(3, 2, 2), p(4, 2, 0, minutes=0)
        mids = [p(10 + i, 3, 3) for i in range(5)]
        captain = p(20, 4, 0, minutes=0)
        vice = mids[0]
        f2 = p(21, 4, 4)
        bench = [p(30, 1, 9), p(31, 3, 7), p(32, 2, 1), p(33, 4, 5)]
        lineup = Lineup([gk, d1, d2, d3, *mids, captain, f2], bench, captain, vice)
        # The blank defender must be replaced by the bench defender (3-DEF minimum)
        # even though the midfielder sits ahead of him; the blank forward by the
        # first bench outfielder, the midfielder. The vice's 3 points double.
        expected = 2 + 2 + 2 + 15 + 4 + 1 + 7 + 3
        self.assertEqual(score_lineup(lineup), expected)


class BacktestHelperTests(TestCase):
    def test_bootstrap_interval_contains_mean(self):
        result = _bootstrap(np.array([1.0, 2.0, 3.0, 4.0]), np.random.default_rng(0))
        self.assertLessEqual(result["low"], result["mean"])
        self.assertGreaterEqual(result["high"], result["mean"])

    def test_captain_picks_score_a_missing_player_as_zero(self):
        preds = pd.DataFrame([
            {"season": 2024, "gameweek": 1, "code": 1, "web_name": "A", "position": 4, "pred": 7.0, "total_points": 2,
             "mins_l1": 90, "mins_m3": 90, "start_price": 14.0, "pts_m6": 6.0},
            {"season": 2024, "gameweek": 1, "code": 2, "web_name": "B", "position": 3, "pred": 5.0, "total_points": 12,
             "mins_l1": 90, "mins_m3": 90, "start_price": 10.0, "pts_m6": 8.0},
        ])
        squads = pd.DataFrame([{"season": 2024, "gameweek": 1, "manager": 0, "code": 99, "is_captain": 1}])
        row = captain_picks(preds, squads).iloc[0]
        self.assertEqual(row["model_name"], "A")
        self.assertEqual(row["model_points"], 2)
        self.assertEqual(row["form_name"], "B")
        self.assertEqual(row["elite_points"], 0, "elite captain without a fixture scores nothing")
        self.assertEqual(row["best_points"], 12)


class ShadowPickTests(TestCase):
    def setUp(self):
        team = Team.objects.create(id=1, code=11, name="T", short_name="T")
        self.players = []
        for pid, pos, cost in ((1, 4, 150), (2, 3, 130), (3, 2, 60)):
            self.players.append(Athlete.objects.create(
                id=pid, code=500 + pid, first_name="F", second_name="S", web_name=f"P{pid}",
                element_type=pos, team=team, now_cost=cost, status="a",
            ))
            AthleteStat.objects.create(athlete_id=pid, game_week=6, minutes=90, starts=1, total_points=5)
        self.deadline = timezone.now() + timedelta(days=2)
        GameweekSummary.objects.create(season=2026, gameweek=7, deadline_time=self.deadline)
        DeadlineSnapshot.objects.create(season=2026, gameweek=7, element=3, code=503, ep_next=9.0, captured_at=timezone.now())
        DeadlineSnapshot.objects.create(season=2026, gameweek=7, element=1, code=501, ep_next=6.0, captured_at=timezone.now())

    def forecast(self):
        return pd.DataFrame([{"element": 1, "pred": 6.5}, {"element": 2, "pred": 7.5}, {"element": 3, "pred": 3.0}])

    def test_picks_skip_unavailable_players(self):
        Athlete.objects.filter(id=2).update(status="i")
        log_picks(2026, 7, self.forecast(), timezone.now())
        picks = {p.strategy: p.web_name for p in ShadowPick.objects.all()}
        self.assertEqual(picks, {"model": "P1", "ep_next": "P3", "premium_form": "P1"})

    def test_settling_scores_picks_and_adds_most_captained(self):
        log_picks(2026, 7, self.forecast(), timezone.now())
        GameweekSummary.objects.filter(gameweek=7).update(finished=True, most_captained=3)
        GameweekHistory.objects.create(season=2026, gameweek=7, code=502, element=2, web_name="P2", team_code=11,
                                       position=3, total_points=13)
        settle_picks(2026, {7})
        scored = {p.strategy: p.actual_points for p in ShadowPick.objects.all()}
        self.assertEqual(scored, {"model": 13, "ep_next": 0, "premium_form": 0, "most_captained": 0})

    def test_lab_hides_unvalidated_pick_until_the_deadline(self):
        log_picks(2026, 7, self.forecast(), timezone.now())
        payload = self.client.get("/api/forecast-lab/").json()
        self.assertEqual(payload["record"], [])
        self.assertTrue(payload["nextPickLogged"])
        GameweekSummary.objects.filter(gameweek=7).update(deadline_time=timezone.now() - timedelta(hours=1))
        payload = self.client.get("/api/forecast-lab/").json()
        self.assertEqual(payload["record"][0]["picks"]["model"]["player"], "P2")

    def test_landing_shows_forecast_captain_only_when_accepted(self):
        ForecastPrediction.objects.create(season=2026, gameweek=7, element=2, code=502, predicted_points=7.5,
                                          horizon=1, model_version="v2.0")
        self.assertIsNone(self.client.get("/api/landing/").json()["captain_recommendation"])
        ModelEvaluation.objects.create(name="points_forecast", version="v2.0", accepted=True,
                                       summary={"accepted": {"captain": True}})
        captain = self.client.get("/api/landing/").json()["captain_recommendation"]
        self.assertEqual(captain["web_name"], "P2")
        self.assertEqual(captain["source"], "points_forecast")


class DeadlineTests(TestCase):
    def test_next_deadline_is_the_earliest_future_one(self):
        now = timezone.now()
        events = [
            {"id": 6, "deadline_time": (now - timedelta(days=5)).isoformat()},
            {"id": 8, "deadline_time": (now + timedelta(days=9)).isoformat()},
            {"id": 7, "deadline_time": (now + timedelta(days=2)).isoformat()},
        ]
        self.assertEqual(next_deadline(events, now)[0], 7)
