from __future__ import annotations

from django.test import TestCase

from ..models import PlMatch
from ..services.match_details import (
    _card_kind, compact_sheet, parse_events, parse_events_feed, parse_lineups, parse_momentum, parse_team_stats,
)

LINEUPS = {
    "home_team": {"teamId": "14", "formation": {"formation": "4-3-3", "lineup": [["1"], ["2", "3"]], "subs": ["9"]},
                  "players": [{"id": "1", "firstName": "Ali", "lastName": "Keeper", "shirtNum": "1", "isCaptain": False, "position": "Goalkeeper"},
                              {"id": "2", "firstName": "Bo", "lastName": "Back", "shirtNum": "4", "isCaptain": True, "position": "Defender"},
                              {"id": "3", "firstName": "Cy", "lastName": "Red", "shirtNum": "5", "position": "Defender"},
                              {"id": "9", "firstName": "Di", "lastName": "Sub", "knownName": "Dimi", "shirtNum": "20", "position": "Forward"}]},
    "away_team": {"teamId": "43", "formation": {"formation": "4-4-2", "lineup": [["50"]], "subs": []},
                  "players": [{"id": "50", "firstName": "Ed", "lastName": "Away", "shirtNum": "1", "position": "Goalkeeper"}]},
}
FEED = {"liveData": {
    "lineUp": [{"player": [{"opPlayerId": "2", "position": "Defender", "positionSide": "Left", "formationPlace": "3"}]}],
    "substitute": [{"opContestantId": "14", "periodId": 2, "timeMin": 70, "opPlayerOnId": "9", "playerOnName": "Dimi",
                    "opPlayerOffId": "2", "playerOffName": "B. Back", "subReason": "Tactical", "timestamp": "T3"}],
    "card": [{"opContestantId": "14", "periodId": 2, "timeMin": 62, "type": "Y2C", "opPlayerId": "3", "playerName": "C. Red",
              "cardReason": "Foul", "timestamp": "T2"},
             {"opContestantId": "43", "periodId": 1, "timeMin": 8, "type": "YC", "opPlayerId": "50", "playerName": "E. Away",
              "cardReason": "Dissent", "timestamp": "T1"}],
    "VAR": [{"opContestantId": "43", "periodId": 2, "timeMin": 80, "type": "Goal awarded", "outcome": "No goal",
             "opPlayerId": "50", "playerName": "E. Away", "timestamp": "T4"}],
    "predictions": [{"type": "Momentum", "periodId": 2, "timeMin": 46, "prediction": [{"type": "Home", "probability": "0.02"}, {"type": "Away", "probability": "0.01"}]},
                    {"type": "Momentum", "periodId": 1, "timeMin": 1, "prediction": [{"type": "Home", "probability": "0.001"}, {"type": "Away", "probability": "0.002"}]}],
}}


class MatchDetailParsingTests(TestCase):
    def setUp(self):
        self.match = PlMatch(season=2026, match_id="1", home_team_id="14", away_team_id="43")

    def test_lineups_place_starters_and_track_minutes_on_and_off(self):
        rows = {r["player_id"]: r for r in parse_lineups(LINEUPS, FEED, self.match)}
        self.assertEqual((rows["1"]["formation_row"], rows["2"]["formation_row"], rows["3"]["formation_col"]), (0, 1, 1))
        self.assertTrue(rows["2"]["captain"])
        self.assertEqual((rows["2"]["position_side"], rows["2"]["formation_place"], rows["2"]["minute_off"]), ("Left", 3, 70))
        self.assertEqual(rows["3"]["minute_off"], 62, "sent off counts as coming off")
        self.assertFalse(rows["9"]["starter"])
        self.assertEqual((rows["9"]["name"], rows["9"]["minute_on"]), ("Dimi", 70))
        self.assertEqual(rows["50"]["team_id"], "43")

    def test_events_in_match_order_with_reasons(self):
        events = parse_events(FEED)
        self.assertEqual([(e["minute"], e["kind"], e["detail"]) for e in events],
                         [(8, "yellow", "Dissent"), (62, "second_yellow", "Foul"), (70, "sub", "Tactical"), (80, "var", "Goal awarded: No goal")])
        self.assertEqual(events[2]["other_player_id"], "2")

    def test_momentum_sorted_by_period_and_minute(self):
        self.assertEqual(parse_momentum(FEED), [[1, 1, 0.001, 0.002], [2, 46, 0.02, 0.01]])

    def test_team_stats_by_side_with_formation(self):
        rows = parse_team_stats([{"side": "Away", "stats": {"expectedGoals": 1.2}}, {"side": "Home", "stats": {"expectedGoals": 0.4}}],
                                LINEUPS, self.match)
        self.assertEqual([(r["team_id"], r["is_home"], r["formation"], r["stats"]["expectedGoals"]) for r in rows],
                         [("43", False, "4-4-2", 1.2), ("14", True, "4-3-3", 0.4)])

    def test_sheets_drop_zeros(self):
        self.assertEqual(compact_sheet({"touches": 31.0, "winning_goal": 0.0, "goals": 0}), {"touches": 31.0})


EVENTS = {
    "homeTeam": {"cards": [{"playerId": "3", "type": "Yellow", "period": "FirstHalf", "time": "30", "timestamp": "T1"},
                           {"playerId": "3", "type": "YellowRed", "period": "ExtraFirstHalf", "time": "98", "timestamp": "T3"}],
                 "subs": [{"playerOnId": "9", "playerOffId": "2", "period": "SecondHalf", "time": "70", "timestamp": "T2"}]},
    "awayTeam": {"cards": [], "subs": []},
}


class CupMatchParsingTests(TestCase):
    """Cup and European matches: no raw Opta feed, so cards and subs come from the events feed."""

    def setUp(self):
        self.match = PlMatch(season=2026, match_id="2", home_team_id="14", away_team_id="43", competition_id=5)

    def test_card_kinds(self):
        self.assertEqual([_card_kind(t) for t in ("Yellow", "YellowRed", "SecondYellow", "Red", "")],
                         ["yellow", "second_yellow", "second_yellow", "red", "yellow"])

    def test_cards_and_subs_with_extra_time(self):
        names = {"2": "Bo Back", "3": "Cy Red", "9": "Dimi"}
        rows = parse_events_feed(EVENTS, self.match, names)
        self.assertEqual([(r["kind"], r["period"], r["minute"]) for r in rows],
                         [("yellow", 1, 30), ("sub", 2, 70), ("second_yellow", 3, 98)])
        self.assertEqual((rows[1]["player_name"], rows[1]["other_player_name"]), ("Dimi", "Bo Back"))
        self.assertEqual(rows[0]["detail"], "")  # no card reasons outside the league feed

    def test_lineup_minutes_from_events_feed(self):
        rows = {r["player_id"]: r for r in parse_lineups(LINEUPS, {}, self.match, EVENTS)}
        self.assertEqual((rows["9"]["minute_on"], rows["2"]["minute_off"], rows["3"]["minute_off"]), (70, 70, 98))
        self.assertIsNone(rows["1"]["minute_off"])


class FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def iter_season_matches(self, competition, season):
        return iter(self.rows.get(competition, []))

    def get_match_events(self, match_id):
        return {"homeTeam": {"goals": []}, "awayTeam": {"goals": []}}


def row(match_id, home, away, period="PreMatch", **extra):
    return {"matchId": match_id, "period": period, "kickoff": "2026-10-01 20:00:00",
            "homeTeam": {"id": home, "name": f"Club {home}", "abbr": f"C{home}", "score": 0},
            "awayTeam": {"id": away, "name": f"Club {away}", "abbr": f"C{away}", "score": 0}, **extra}


class CompetitionSyncTests(TestCase):
    def test_cup_ties_kept_only_for_premier_league_clubs(self):
        from ..services.match_goals import sync_season
        client = FakeClient({8: [row("10", "14", "43")],
                             5: [row("20", "14", "999", round="League Phase"), row("21", "998", "999"),
                                 row("22", "999", "14", period="FullTime", resultType="PenaltyShootout",
                                     homePenaltyScore=2, awayPenaltyScore=4)]})
        logs = []
        sync_season(2026, client, log=logs.append, competition=5)
        self.assertFalse(PlMatch.objects.exists())  # the league must be synced first
        sync_season(2026, client, log=logs.append)
        sync_season(2026, client, log=logs.append, competition=5)
        cup = PlMatch.objects.get(match_id="20")
        self.assertEqual((cup.competition_id, cup.competition_name, cup.round_name, cup.away_team_name),
                         (5, "Champions League", "League Phase", "Club 999"))
        self.assertFalse(PlMatch.objects.filter(match_id="21").exists())
        shootout = PlMatch.objects.get(match_id="22")
        self.assertEqual((shootout.home_penalties, shootout.away_penalties, shootout.goals_synced), (2, 4, True))
