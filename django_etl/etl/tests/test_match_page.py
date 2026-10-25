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


class MatchCalendarTests(TestCase):
    def setUp(self):
        from datetime import datetime, timezone as tz
        from ..models import Team
        cache.clear()
        Team.objects.create(id=1, code=14, name="Liverpool", short_name="LIV")
        Team.objects.create(id=2, code=43, name="Man City", short_name="MCI")
        when = lambda d: datetime(2026, 10, d, 19, 0, tzinfo=tz.utc)
        PlMatch.objects.create(season=2026, match_id="1", home_team_id="14", away_team_id="43", kickoff=when(1), home_score=1, away_score=0)
        PlMatch.objects.create(season=2026, match_id="2", competition_id=5, competition_name="UEFA Champions League", round_name="Round",
                               matchweek=2, home_team_id="999", away_team_id="14", home_team_name="Inter", home_team_short="INT", kickoff=when(4))
        PlMatch.objects.create(season=2026, match_id="3", competition_id=5, home_team_id="998", away_team_id="997", kickoff=when(4))

    def test_window_holds_every_competition_for_league_clubs(self):
        d = self.client.get("/api/matches/calendar/?start=2026-10-02&days=7").json()
        self.assertEqual([c["short"] for c in d["clubs"]], ["LIV", "MCI"])
        self.assertEqual([m["matchId"] for m in d["matches"]], ["2"])
        m = d["matches"][0]
        self.assertEqual((m["round"], m["home"]["name"], m["status"]), ("Matchday 2", "Inter", "upcoming"))
        self.assertTrue(d["previous"]["14"].startswith("2026-10-01"))

    def test_bad_start_is_400(self):
        self.assertEqual(self.client.get("/api/matches/calendar/?start=soon").status_code, 400)


class TeamPageTests(TestCase):
    def setUp(self):
        from datetime import datetime, timezone as tz
        from ..models import Team
        cache.clear()
        Team.objects.create(id=1, code=14, name="Liverpool", short_name="LIV")
        Team.objects.create(id=2, code=43, name="Man City", short_name="MCI")
        when = lambda d: datetime(2026, 10, d, 19, 0, tzinfo=tz.utc)
        league = PlMatch.objects.create(season=2026, match_id="1", home_team_id="14", away_team_id="43", kickoff=when(1), home_score=2, away_score=0)
        MatchTeamStat.objects.create(match=league, team_id="14", is_home=True, stats={"expectedGoals": 1.5, "totalScoringAtt": 12})
        MatchTeamStat.objects.create(match=league, team_id="43", is_home=False, stats={"expectedGoals": 0.5, "totalScoringAtt": 6})
        cup = PlMatch.objects.create(season=2026, match_id="2", competition_id=5, competition_name="UEFA Champions League",
                                     home_team_id="999", away_team_id="14", home_team_name="Inter", kickoff=when(4), home_score=1, away_score=1,
                                     result_type="PenaltyShootout", home_penalties=3, away_penalties=4)
        MatchTeamStat.objects.create(match=cup, team_id="14", is_home=False, stats={"totalScoringAtt": 9})
        MatchLineupPlayer.objects.create(match=cup, team_id="14", player_id="5", name="Mo Salah", starter=True)
        MatchGoal.objects.create(match=cup, order=1, team_id="14", is_home=False, minute=11, period="FirstHalf",
                                 goal_type="Goal", player_id="5", home_after=0, away_after=1)

    def test_season_in_every_competition(self):
        d = self.client.get("/api/teams/14/").json()
        self.assertEqual((d["team"]["name"], d["position"], d["seasons"]), ("Liverpool", 1, [2026]))
        league, cup = d["matches"]
        self.assertEqual((league["res"], league["gf"], league["for"]["expectedGoals"], league["against"]["totalScoringAtt"]), ("W", 2, 1.5, 6))
        self.assertEqual((cup["res"], cup["opp"]["name"], cup["home"]), ("W", "Inter", False))  # won on penalties
        self.assertIsNone(cup["for"]["expectedGoals"])  # no xG outside the league, not zero
        salah = next(p for p in d["squad"] if p["optaId"] == "5")
        self.assertEqual((salah["apps"], salah["minutes"], salah["goals"]), (1, 120, 1))

    def test_index_in_table_order(self):
        clubs = self.client.get("/api/teams/").json()["clubs"]
        self.assertEqual([(c["short"], c["pos"]) for c in clubs], [("LIV", 1), ("MCI", 2)])

    def test_unknown_team_is_404(self):
        self.assertEqual(self.client.get("/api/teams/777/").status_code, 404)


class PlayerPageTests(TestCase):
    def setUp(self):
        from datetime import datetime, timezone as tz
        from ..models import Athlete, Team
        cache.clear()
        team = Team.objects.create(id=1, code=14, name="Liverpool", short_name="LIV")
        self.athlete = Athlete.objects.create(id=99, code=5, first_name="Mo", second_name="Salah", web_name="Salah", team=team,
                                              element_type=3, now_cost=130, total_points=50, selected_by_percent=40, status="a")
        when = lambda d: datetime(2026, 10, d, 19, 0, tzinfo=tz.utc)
        cup = PlMatch.objects.create(season=2026, match_id="2", competition_id=5, competition_name="UEFA Champions League",
                                     home_team_id="999", away_team_id="14", home_team_name="Inter", kickoff=when(4), home_score=0, away_score=2)
        MatchLineupPlayer.objects.create(match=cup, team_id="14", player_id="5", name="Mo Salah", starter=True, minute_off=75)
        MatchGoal.objects.create(match=cup, order=1, team_id="14", is_home=False, minute=11, period="FirstHalf", goal_type="Goal",
                                 player_id="5", home_after=0, away_after=1)
        PlMatch.objects.create(season=2026, match_id="3", home_team_id="14", away_team_id="43", kickoff=when(9))

    def test_player_season_in_every_competition(self):
        d = self.client.get("/api/players/99/page/").json()
        self.assertEqual((d["name"], d["position"], d["price"], d["team"]["name"]), ("Mo Salah", "MID", 13.0, "Liverpool"))
        self.assertEqual([(r["competition"], r["minutes"], r["goals"], r["res"]) for r in d["log"]], [("UEFA Champions League", 75, 1, "W")])
        self.assertEqual(d["byCompetition"][0]["apps"], 1)
        self.assertEqual([u["matchId"] for u in d["upcoming"]], ["3"])
        self.assertFalse(d["compare"]["qualified"])

    def test_unknown_player_is_404(self):
        self.assertEqual(self.client.get("/api/players/12345/page/").status_code, 404)
