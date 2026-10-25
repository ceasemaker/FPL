from __future__ import annotations

from django.core.cache import cache
from django.test import TestCase

from ..models import MatchEvent, MatchGoal, MatchLineupPlayer, MatchTeamStat, PlayerMatchStat, PlMatch, TeamSeasonStat


class MatchPageApiTests(TestCase):
    def setUp(self):
        cache.clear()
        for tid, name in (("14", "Liverpool"), ("43", "Manchester City")):
            TeamSeasonStat.objects.create(competition_id=8, season=2026, opta_team_id=tid, name=name, stats={})
        self.match = PlMatch.objects.create(season=2026, match_id="1", home_team_id="14", away_team_id="43",
                                            home_score=0, away_score=1, goals_synced=True, details_synced=True,
                                            momentum=[[1, 1, 0.01, 0.02]])
        MatchLineupPlayer.objects.create(match=self.match, team_id="43", player_id="9", name="Erling Haaland", shirt="9",
                                         position="Forward", formation_row=4, formation_col=0, starter=True)
        MatchGoal.objects.create(match=self.match, order=1, team_id="43", is_home=False, minute=65, period="SecondHalf",
                                 goal_type="Goal", player_id="9", home_after=0, away_after=1)
        MatchEvent.objects.create(match=self.match, team_id="14", kind="second_yellow", minute=62, period=2,
                                  player_name="R. Gravenberch", detail="Foul")
        MatchTeamStat.objects.create(match=self.match, team_id="43", is_home=False, formation="4-2-3-1", stats={"expectedGoals": 1.28})
        PlayerMatchStat.objects.create(match=self.match, player_id="9", source_player_id=1, team_id="43", minutes=80,
                                       started=True, stats={"goals": 1, "total_scoring_att": 2})
        PlMatch.objects.create(season=2026, match_id="2", home_team_id="43", away_team_id="14")

    def test_finished_match_payload(self):
        d = self.client.get("/api/matches/1/").json()
        self.assertEqual((d["status"], d["score"], d["home"]["name"], d["away"]["name"]), ("finished", [0, 1], "Liverpool", "Manchester City"))
        self.assertEqual(d["goals"][0]["scorer"], "Erling Haaland")
        self.assertEqual(d["events"][0]["kind"], "second_yellow")
        self.assertEqual(d["teamStats"]["43"]["formation"], "4-2-3-1")
        self.assertEqual((d["players"][0]["goals"], d["players"][0]["shots"], d["players"][0]["position"]), (1, 2, "FWD"))
        self.assertIsNone(d["odds"])

    def test_upcoming_match_has_context_but_no_score(self):
        d = self.client.get("/api/matches/2/").json()
        self.assertEqual((d["status"], d["score"]), ("upcoming", None))
        self.assertEqual(d["h2h"][0]["matchId"], "1")

    def test_unknown_match_is_404(self):
        self.assertEqual(self.client.get("/api/matches/999/").status_code, 404)

    def test_cup_match_against_a_club_outside_the_league(self):
        cup = PlMatch.objects.create(season=2026, match_id="3", competition_id=5, competition_name="UEFA Champions League",
                                     round_name="Round", matchweek=4, home_team_id="2000", away_team_id="14",
                                     home_team_name="Club Brugge", home_team_short="CLB", home_score=2, away_score=3,
                                     goals_synced=True, details_synced=True)
        MatchLineupPlayer.objects.create(match=cup, team_id="14", player_id="5", name="Mo Salah", starter=True, minute_off=80)
        MatchGoal.objects.create(match=cup, order=1, team_id="14", is_home=False, minute=11, period="FirstHalf",
                                 goal_type="Goal", player_id="5", home_after=0, away_after=1)
        d = self.client.get("/api/matches/3/").json()
        self.assertEqual((d["competition"], d["round"], d["gameweek"], d["home"]["name"]),
                         ("UEFA Champions League", "Matchday 4", None, "Club Brugge"))
        self.assertIsNone(d["form"]["home"])  # only its games against PL clubs are stored
        self.assertEqual(d["form"]["away"][0]["matchId"], "1")
        self.assertEqual([(p["name"], p["minutes"], p["goals"], p["shots"]) for p in d["players"]], [("Mo Salah", 80, 1, None)])
