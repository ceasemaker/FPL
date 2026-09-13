"""Leakage guards for etl.ml.features.

These tests pin the as-of-deadline contract: nothing computed for gameweek N
may read the GW N stat row, any later row, or present-day Athlete state.
"""
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from etl.ml.features import (
    FEATURE_NAMES,
    extract_features,
    feature_vector,
    get_training_data,
    iter_training_rows,
)
from etl.models import Athlete, AthleteStat, ElementSummary, Fixture, Team
from etl.services.etl_runner import gameweek_context_from_history, sync_gameweek_context


def make_athlete(athlete_id, team, **overrides):
    defaults = dict(
        code=1000 + athlete_id,
        first_name="Test",
        second_name=f"Player{athlete_id}",
        web_name=f"P{athlete_id}",
        element_type=3,
        team=team,
        now_cost=999,  # deliberately unlike any history value
        transfers_in_event=123456,
        transfers_out_event=1,
    )
    defaults.update(overrides)
    return Athlete.objects.create(id=athlete_id, **defaults)


def make_stat(athlete, gw, points, **context):
    return AthleteStat.objects.create(
        athlete=athlete,
        game_week=gw,
        total_points=points,
        minutes=90,
        expected_goals=Decimal("0.5"),
        **context,
    )


class FeatureLeakageTests(TestCase):
    def setUp(self):
        self.home = Team.objects.create(id=1, code=1, name="Home", short_name="HOM")
        self.away = Team.objects.create(id=2, code=2, name="Away", short_name="AWY")
        self.athlete = make_athlete(1, self.home)
        context = {"selected": 100, "transfers_in": 10, "transfers_out": 4, "value": 50}
        make_stat(self.athlete, 1, 6, **context)
        make_stat(self.athlete, 2, 8, **{**context, "transfers_in": 20, "value": 51})
        make_stat(self.athlete, 3, 3, **{**context, "transfers_in": 30, "value": 52})
        for gw in (1, 2, 3):
            Fixture.objects.create(
                id=gw, event=gw, team_h=self.home, team_a=self.away,
                team_h_difficulty=2, team_a_difficulty=4,
            )

    def test_ppg_excludes_target_and_future_gameweeks(self):
        self.assertEqual(extract_features(1, 2)["ppg_to_date"], 6.0)  # GW1 only
        self.assertEqual(extract_features(1, 3)["ppg_to_date"], 7.0)  # GW1-2
        self.assertAlmostEqual(extract_features(1, 4)["ppg_to_date"], 17 / 3)  # GW1-3
        self.assertEqual(extract_features(1, 2)["games_to_date"], 1)

    def test_form_window_stops_before_target(self):
        self.assertEqual(extract_features(1, 3)["form_3gw"], 14)
        self.assertEqual(extract_features(1, 2)["minutes_3gw"], 90)

    def test_context_is_as_of_gameweek_not_live_athlete(self):
        gw2 = extract_features(1, 2)
        gw3 = extract_features(1, 3)
        self.assertEqual(gw2["context_source"], "gameweek")
        self.assertEqual((gw2["transfers_balance"], gw2["value"]), (16, 51))
        self.assertEqual((gw3["transfers_balance"], gw3["value"]), (26, 52))
        # Present-day Athlete values must never surface on a played gameweek.
        self.assertNotEqual(gw2["value"], self.athlete.now_cost)

    def test_no_feature_is_a_present_day_constant(self):
        """Every non-static feature must vary across gameweeks for one athlete."""
        gw2 = extract_features(1, 2)
        gw3 = extract_features(1, 3)
        static = {"position", "fixture_count", "home_fixtures", "opponent_fdr", "xg_3gw", "xa_3gw", "xgc_3gw"}
        for name in FEATURE_NAMES:
            if name in static:
                continue
            self.assertNotEqual(gw2[name], gw3[name], f"{name} constant across GW2/GW3")

    def test_dropped_leaky_fields_are_absent(self):
        for name in ("chance_of_playing", "selected_pct", "transfers_in_delta", "ppg_season"):
            self.assertNotIn(name, FEATURE_NAMES)
            self.assertNotIn(name, extract_features(1, 2))

    def test_live_fallback_only_for_next_unplayed_gameweek(self):
        nxt = extract_features(1, 4)
        self.assertEqual(nxt["context_source"], "live")
        self.assertEqual(nxt["value"], 999)
        self.assertEqual(nxt["transfers_balance"], 123455)

        # A played gameweek with no stored context gets no source, not live data.
        AthleteStat.objects.filter(game_week=2).update(value=None, transfers_in=None)
        played = extract_features(1, 2)
        self.assertIsNone(played["context_source"])
        self.assertEqual(played["value"], 0)

    def test_training_rows_skip_gw1_and_missing_context(self):
        rows = list(iter_training_rows())
        self.assertEqual([stat.game_week for stat, _ in rows], [2, 3])
        AthleteStat.objects.filter(game_week=3).update(value=None)
        self.assertEqual([stat.game_week for stat, _ in iter_training_rows()], [2])
        X, y = get_training_data()
        self.assertEqual(len(X), 1)
        self.assertEqual(len(X[0]), len(FEATURE_NAMES))
        self.assertEqual(y, [8])

    def test_feature_vector_order_matches_names(self):
        d = extract_features(1, 2)
        self.assertEqual(feature_vector(d), [d[n] for n in FEATURE_NAMES])


class FixtureContextTests(TestCase):
    def setUp(self):
        self.t1 = Team.objects.create(id=1, code=1, name="A", short_name="AAA")
        self.t2 = Team.objects.create(id=2, code=2, name="B", short_name="BBB")
        self.t3 = Team.objects.create(id=3, code=3, name="C", short_name="CCC")
        self.athlete = make_athlete(1, self.t1)

    def test_double_gameweek_counts_both_fixtures(self):
        Fixture.objects.create(id=1, event=5, team_h=self.t1, team_a=self.t2, team_h_difficulty=2, team_a_difficulty=3)
        Fixture.objects.create(id=2, event=5, team_h=self.t3, team_a=self.t1, team_h_difficulty=3, team_a_difficulty=4)
        f = extract_features(1, 5)
        self.assertEqual(f["fixture_count"], 2)
        self.assertEqual(f["home_fixtures"], 1)
        self.assertEqual(f["opponent_fdr"], 3.0)

    def test_blank_gameweek_is_explicit(self):
        f = extract_features(1, 5)
        self.assertEqual(f["fixture_count"], 0)
        self.assertEqual(f["home_fixtures"], 0)


class GameweekContextSyncTests(TestCase):
    HISTORY = [
        {"round": 1, "fixture": 1, "selected": 100, "transfers_in": 5, "transfers_out": 2, "value": 50},
        {"round": 2, "fixture": 2, "selected": 120, "transfers_in": 30, "transfers_out": 1, "value": 51},
        # Double gameweek: history repeats the round-level snapshot per fixture.
        {"round": 2, "fixture": 3, "selected": 120, "transfers_in": 30, "transfers_out": 1, "value": 51},
    ]

    def setUp(self):
        self.t1 = Team.objects.create(id=1, code=1, name="A", short_name="AAA")
        self.t2 = Team.objects.create(id=2, code=2, name="B", short_name="BBB")
        self.athlete = make_athlete(1, self.t1)
        for fid, event in ((1, 1), (2, 2), (3, 2)):
            Fixture.objects.create(id=fid, event=event, team_h=self.t1, team_a=self.t2)

    def test_history_collapses_double_gameweek_without_double_counting(self):
        ctx = gameweek_context_from_history(self.HISTORY)
        self.assertEqual(set(ctx), {1, 2})
        self.assertEqual(ctx[2], {"selected": 120, "transfers_in": 30, "transfers_out": 1, "value": 51})

    def test_history_from_another_season_is_rejected(self):
        stale = [{"round": 7, "fixture": 999, "selected": 1, "transfers_in": 1, "transfers_out": 1, "value": 1}]
        valid = {(1, 1), (2, 2), (3, 2)}
        self.assertEqual(gameweek_context_from_history(stale, valid), {})
        self.assertEqual(set(gameweek_context_from_history(self.HISTORY, valid)), {1, 2})

    def test_sync_updates_existing_rows_only(self):
        make_stat(self.athlete, 2, 9)
        updated = sync_gameweek_context(self.athlete, self.HISTORY)
        self.assertEqual(updated, 1)
        gw2 = AthleteStat.objects.get(athlete=self.athlete, game_week=2)
        self.assertEqual(gw2.total_points, 9)
        self.assertEqual((gw2.selected, gw2.transfers_in, gw2.transfers_out, gw2.value), (120, 30, 1, 51))
        # No GW1 stat row existed, so none may be manufactured from history.
        self.assertFalse(AthleteStat.objects.filter(athlete=self.athlete, game_week=1).exists())

    def test_backfill_command_uses_stored_summaries(self):
        make_stat(self.athlete, 1, 2)
        make_stat(self.athlete, 2, 9)
        ElementSummary.objects.create(athlete=self.athlete, history=self.HISTORY)
        removed = make_athlete(2, self.t1, removed=True)
        make_stat(removed, 1, 0)
        ElementSummary.objects.create(athlete=removed, history=self.HISTORY)

        call_command("backfill_gameweek_context", "--dry-run")
        self.assertFalse(AthleteStat.objects.filter(value__isnull=False).exists())
        call_command("backfill_gameweek_context")
        self.assertEqual(AthleteStat.objects.filter(value__isnull=False).count(), 2)
        self.assertIsNone(AthleteStat.objects.get(athlete=removed, game_week=1).value)
