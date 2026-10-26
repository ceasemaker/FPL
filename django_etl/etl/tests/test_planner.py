from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from ..models import Athlete, Fixture, GameweekSummary, Team
from ..services import planner


class PlannerRulesTests(TestCase):
    def test_selling_price_keeps_half_the_rise(self):
        self.assertEqual([planner.selling_price(p, n) for p, n in ((50, 50), (50, 53), (50, 54), (50, 48))], [50, 51, 52, 48])

    def test_free_transfers_bank_up_to_five_and_hits_reset(self):
        quiet = [{"event": gw, "event_transfers": 0} for gw in range(1, 10)]
        self.assertEqual(planner.free_transfers(quiet, [], 4), 3)
        self.assertEqual(planner.free_transfers(quiet, [], 9), 5)  # capped
        busy = quiet[:2] + [{"event": 3, "event_transfers": 3}] + quiet[3:]
        self.assertEqual(planner.free_transfers(busy, [], 4), 1)  # 2 free, 3 made: a hit, then +1
        self.assertEqual(planner.free_transfers(busy, [{"name": "wildcard", "event": 3}], 4), 3)  # wildcard keeps them

    def test_chips_once_per_half(self):
        used = [{"name": "wildcard", "event": 5}, {"name": "bboost", "event": 21}]
        first = {c["key"]: c["available"] for c in planner.chips_left(used, 10)}
        second = {c["key"]: c["available"] for c in planner.chips_left(used, 25)}
        self.assertEqual((first["wildcard"], first["bboost"], second["wildcard"], second["bboost"]), (False, True, True, False))


class FakeFPL:
    def get_manager_info(self, manager_id):
        if manager_id == 404:
            raise RuntimeError("404")
        return {"player_first_name": "Ann", "player_last_name": "Manager", "name": "Ann's XI", "summary_overall_rank": 1000}

    def get_manager_picks(self, manager_id, event):
        return {"active_chip": None, "entry_history": {"bank": 15, "value": 1003},
                "picks": [{"element": 10, "position": 1, "is_captain": True}, {"element": 11, "position": 2}]}

    def get_manager_history(self, manager_id):
        return {"current": [{"event": 1, "event_transfers": 0}, {"event": 2, "event_transfers": 1}], "chips": []}

    def get_manager_transfers(self, manager_id):
        return [{"element_in": 11, "element_in_cost": 60, "time": "2026-08-20T10:00:00Z"}]


class PlannerPayloadTests(TestCase):
    def setUp(self):
        cache.clear()
        now = timezone.now()
        GameweekSummary.objects.create(season=2026, gameweek=2, deadline_time=now - timedelta(days=3))
        GameweekSummary.objects.create(season=2026, gameweek=3, deadline_time=now + timedelta(days=3))
        ars = Team.objects.create(id=1, code=3, name="Arsenal", short_name="ARS")
        che = Team.objects.create(id=2, code=8, name="Chelsea", short_name="CHE")
        Athlete.objects.create(id=10, code=100, web_name="Raya", team=ars, element_type=1, now_cost=62, cost_change_start=2)
        Athlete.objects.create(id=11, code=101, web_name="Palmer", team=che, element_type=3, now_cost=65)
        Fixture.objects.create(id=1, event=3, team_h=ars, team_a=che, team_h_difficulty=3, team_a_difficulty=4, kickoff_time=now + timedelta(days=4))

    def test_squad_with_purchase_and_selling_prices(self):
        d = planner.build_payload(1, FakeFPL())
        self.assertEqual((d["teamName"], d["nextGameweek"], d["bank"], d["freeTransfers"]), ("Ann's XI", 3, 15, 1))
        raya, palmer = d["squad"]
        self.assertEqual((raya["purchase"], raya["selling"], raya["captain"]), (60, 61, True))  # kept since the start: start price 6.0
        self.assertEqual((palmer["purchase"], palmer["selling"]), (60, 62))
        self.assertEqual(d["fixtures"]["3"][3]["fixtures"][0], {"opp": "CHE", "oppCode": "8", "home": True, "difficulty": 3})
        self.assertEqual({p["name"] for p in d["players"]}, {"Raya", "Palmer"})

    def test_unknown_manager(self):
        with self.assertRaises(planner.ManagerNotFound):
            planner.build_payload(404, FakeFPL())


class PlannerExtrasTests(TestCase):
    def setUp(self):
        cache.clear()
        from datetime import datetime, timezone as tz
        from ..models import ForecastPrediction, MatchLineupPlayer, ModelEvaluation, PlMatch
        now = timezone.now()
        GameweekSummary.objects.create(season=2026, gameweek=2, deadline_time=now - timedelta(days=3))
        GameweekSummary.objects.create(season=2026, gameweek=3, deadline_time=now + timedelta(days=3))
        ars = Team.objects.create(id=1, code=3, name="Arsenal", short_name="ARS")
        Athlete.objects.create(id=10, code=100, web_name="Saka", team=ars, element_type=3, now_cost=100, ep_next=5)
        Athlete.objects.create(id=11, code=101, web_name="Nwaneri", team=ars, element_type=3, now_cost=50, ep_next=2)
        ForecastPrediction.objects.create(season=2026, gameweek=3, element=10, code=100, predicted_points=6.4, model_version="v3")
        ModelEvaluation.objects.create(name="points_forecast", version="v3", summary={"accuracy": {"player_weeks": 100, "model_mae": 1.4, "form_mae": 1.5}})
        for i in range(6):
            m = PlMatch.objects.create(season=2026, match_id=str(i), home_team_id="3", away_team_id="99", home_score=1, away_score=0,
                                       kickoff=now - timedelta(days=30 - i * 4), details_synced=True)
            MatchLineupPlayer.objects.create(match=m, team_id="3", player_id="100", name="Saka", starter=i != 5, minute_off=80 if i == 4 else None)
        PlMatch.objects.create(season=2026, match_id="up", competition_id=5, home_team_id="3", away_team_id="98", kickoff=now + timedelta(days=5))

    def test_projections_carry_the_record_and_fpl_fallback(self):
        d = planner.projections(3)
        self.assertEqual(d["points"]["10"], {"3": 6.4})
        self.assertEqual((d["points"]["11"], d["fplOnly"]), ({"3": 2.0}, [11]))  # no forecast: FPL's expected points
        self.assertEqual((d["record"]["modelError"], d["record"]["formError"]), (1.4, 1.5))

    def test_rotation_counts_the_last_five_and_upcoming_games(self):
        r = planner.rotation(3, {})["10"]
        self.assertEqual((r["starts"], r["clubGames"], r["next14"]), (4, 5, 1))  # benched in the latest game
        self.assertEqual(r["minutes"], 80 + 90 * 3)


class FakeLeagueFPL(FakeFPL):
    def get_manager_info(self, manager_id):
        return {**super().get_manager_info(manager_id), "leagues": {"classic": [
            {"id": 7, "name": "Office", "league_type": "x", "entry_rank": 2}, {"id": 314, "name": "Overall", "league_type": "s"}]}}

    def get_league_standings(self, league_id, page=1):
        return {"league": {"name": "Office"}, "standings": {"results": [
            {"entry": 1, "player_name": "Ann", "entry_name": "Ann's XI", "rank": 2, "total": 500, "event_total": 50},
            {"entry": 2, "player_name": "Bo", "entry_name": "Bo FC", "rank": 1, "total": 520, "event_total": 60}]}}

    def get_manager_picks(self, manager_id, event):
        if manager_id == 2:
            return {"picks": [{"element": 12, "is_captain": True}, {"element": 10}]}
        return super().get_manager_picks(manager_id, event)


class PlannerLeagueTests(TestCase):
    def setUp(self):
        cache.clear()
        now = timezone.now()
        GameweekSummary.objects.create(season=2026, gameweek=3, deadline_time=now + timedelta(days=3))
        ars = Team.objects.create(id=1, code=3, name="Arsenal", short_name="ARS")
        for i, n in ((10, "Raya"), (11, "Palmer"), (12, "Haaland")):
            Athlete.objects.create(id=i, code=100 + i, web_name=n, team=ars, element_type=3, now_cost=60)

    def test_only_invitational_leagues(self):
        self.assertEqual(planner.manager_leagues(1, FakeLeagueFPL()), [{"id": 7, "name": "Office", "rank": 2}])

    def test_rival_differentials_and_captains(self):
        d = planner.league_view(7, 1, FakeLeagueFPL())
        self.assertEqual(d["rivals"], 1)
        self.assertEqual([(r["name"], r["share"]) for r in d["theyHave"]], [("Haaland", 100)])
        self.assertEqual([r["name"] for r in d["onlyYou"]], ["Palmer"])  # Raya is shared with the rival
        self.assertEqual(d["captains"][0]["name"], "Haaland")


class PlannerSyncTests(TestCase):
    def test_create_read_replace(self):
        import json
        made = self.client.post("/api/planner/sync/", json.dumps({"managerId": 5, "plans": {"active": "A"}}), content_type="application/json").json()
        code = made["code"]
        self.assertEqual(len(code), 10)
        self.assertEqual(self.client.get(f"/api/planner/sync/{code}/").json()["plans"], {"active": "A"})
        self.client.put(f"/api/planner/sync/{code}/", json.dumps({"plans": {"active": "B"}}), content_type="application/json")
        self.assertEqual(self.client.get(f"/api/planner/sync/{code.upper()}/").json()["plans"], {"active": "B"})
        self.assertEqual(self.client.get("/api/planner/sync/nope/").status_code, 404)
        # The watchlist rides on the same code; saving one half leaves the other alone.
        self.assertIsNone(self.client.get(f"/api/planner/sync/{code}/").json()["watchlist"])
        self.client.put(f"/api/planner/sync/{code}/", json.dumps({"watchlist": [7, 3, 7, "x", True, -1]}), content_type="application/json")
        got = self.client.get(f"/api/planner/sync/{code}/").json()
        self.assertEqual((got["watchlist"], got["plans"]), ([7, 3], {"active": "B"}))
        self.client.put(f"/api/planner/sync/{code}/", json.dumps({"plans": {"active": "C"}}), content_type="application/json")
        self.assertEqual(self.client.get(f"/api/planner/sync/{code}/").json()["watchlist"], [7, 3])
        only = self.client.post("/api/planner/sync/", json.dumps({"watchlist": [9]}), content_type="application/json").json()
        got = self.client.get(f"/api/planner/sync/{only['code']}/").json()
        self.assertEqual((got["watchlist"], got["plans"], got["managerId"]), ([9], {}, None))
        big = json.dumps({"plans": {"x": "y" * 70000}})
        self.assertEqual(self.client.post("/api/planner/sync/", big, content_type="application/json").status_code, 413)


class PriceForecastTests(TestCase):
    def test_backtest_needs_enough_days_and_records_the_result(self):
        from ..models import ModelEvaluation, PriceSnapshot
        from ..services import price_forecast
        team = Team.objects.create(id=1, code=3, name="Arsenal", short_name="ARS")
        a = Athlete.objects.create(id=10, code=100, web_name="Saka", team=team, element_type=3, now_cost=100)
        start = timezone.now() - timedelta(days=10)
        for d in range(10):
            PriceSnapshot.objects.create(athlete=a, snapshot_time=start + timedelta(days=d), cost=100 + d // 5,
                                         transfers_in_total=1000 * d, transfers_out_total=0, selected_by_percent=10, form=5)
        result = price_forecast.backtest()
        self.assertFalse(result["accepted"])
        self.assertIn("need 14", result["reason"])
        self.assertFalse(ModelEvaluation.objects.get(name="price_forecast").accepted)
        self.assertIsNone(price_forecast.current())  # never shown without an accepted backtest


class DefconTests(TestCase):
    def test_fields_from_fpl_explain_and_hit_rates(self):
        from ..models import AthleteStat
        from ..services import defcon
        from ..services.etl_runner import defcon_fields
        element = {"stats": {"defensive_contribution": 14, "clearances_blocks_interceptions": 11, "tackles": 3, "recoveries": 3},
                   "explain": [{"fixture": 1, "stats": [{"identifier": "minutes", "value": 90, "points": 2},
                                                         {"identifier": "defensive_contribution", "value": 14, "points": 2}]}]}
        self.assertEqual(defcon_fields(element), {"defensive_contribution": 14, "clearances_blocks_interceptions": 11, "tackles": 3,
                                                  "recoveries": 3, "dc_points": 2, "dc_hits": 1, "matches_played": 1})
        cache.clear()
        team = Team.objects.create(id=1, code=3, name="Arsenal", short_name="ARS")
        a = Athlete.objects.create(id=4, code=104, web_name="Gabriel", team=team, element_type=2, now_cost=70)
        for gw, (dc, hit) in enumerate([(14, 1), (8, 0), (11, 1), (12, 1)], start=1):
            AthleteStat.objects.create(athlete=a, game_week=gw, minutes=90, defensive_contribution=dc, dc_hits=hit,
                                       dc_points=2 * hit, matches_played=1)
        p = defcon.build_payload()["players"][0]
        self.assertEqual((p["position"], p["threshold"], p["matches"], p["hits"], p["hitRate"], p["perMatch"], p["points"]),
                         ("DEF", 10, 4, 3, 0.75, 11.2, 6))


class TeamNewsTests(TestCase):
    def test_flags_set_pieces_and_deadline(self):
        from ..models import PlayerSeasonStat, PlMatch
        from ..services import team_news
        cache.clear()
        GameweekSummary.objects.create(season=2026, gameweek=9, deadline_time=timezone.now() + timedelta(days=2))
        team = Team.objects.create(id=1, code=3, name="Arsenal", short_name="ARS")
        saka = Athlete.objects.create(id=12, code=223340, web_name="Saka", team=team, element_type=3, status="d", chance_of_playing_next_round=75, news="Knock")
        Athlete.objects.create(id=13, code=204480, web_name="Rice", team=team, element_type=3, status="u", news="Left the club")
        PlMatch.objects.create(season=2026, match_id="1", home_team_id="3", away_team_id="8")
        PlayerSeasonStat.objects.create(source="sdp", competition_id=8, season=2026, opta_player_id="223340", athlete=saka, name="Saka",
                                        stats={"penaltiesTaken": 2, "cornersTakenInclShortCorners": 15})
        PlayerSeasonStat.objects.create(source="classic", competition_id=8, season=2026, opta_player_id="223340", athlete=saka, name="Saka",
                                        stats={"att_freekick_total": 1, "freekick_cross": 3})
        d = team_news.build_payload()
        club = d["clubs"][0]
        self.assertEqual(d["deadline"]["gameweek"], 9)
        self.assertEqual([f["name"] for f in club["flagged"]], ["Saka"])  # "unavailable" (left the club) is left out
        self.assertEqual((club["setPieces"]["penalties"][0]["count"], club["setPieces"]["corners"][0]["count"], club["setPieces"]["freeKicks"][0]["count"]), (2, 15, 4))


class RateTeamTests(TestCase):
    def test_best_xi_respects_formation(self):
        from ..services.rate_team import best_xi
        pos = {1: "GKP", 2: "GKP", **{i: "DEF" for i in range(3, 8)}, **{i: "MID" for i in range(8, 13)}, **{i: "FWD" for i in range(13, 16)}}
        pts = {i: 1.0 for i in range(1, 16)}
        pts.update({13: 9, 14: 8, 15: 7, 8: 6, 9: 6})  # three strong forwards and two midfielders
        total, xi, captain = best_xi(list(range(1, 16)), pos, pts)
        self.assertEqual(len(xi), 11)
        self.assertEqual(sum(1 for i in xi if pos[i] == "GKP"), 1)
        self.assertTrue(sum(1 for i in xi if pos[i] == "DEF") >= 3)
        self.assertEqual(captain, 13)
        self.assertEqual(total, sum(pts[i] for i in xi) + 9)


class WatchlistTests(TestCase):
    def test_players_in_the_order_watched(self):
        cache.clear()
        GameweekSummary.objects.create(season=2026, gameweek=9, deadline_time=timezone.now() + timedelta(days=2))
        ars = Team.objects.create(id=1, code=3, name="Arsenal", short_name="ARS")
        che = Team.objects.create(id=2, code=8, name="Chelsea", short_name="CHE")
        Athlete.objects.create(id=10, code=100, web_name="Saka", team=ars, element_type=3, now_cost=100, ep_next=6, status="d", news="Knock")
        Athlete.objects.create(id=11, code=101, web_name="Palmer", team=che, element_type=3, now_cost=105)
        Fixture.objects.create(id=1, event=9, team_h=ars, team_a=che, team_h_difficulty=3, team_a_difficulty=4, kickoff_time=timezone.now() + timedelta(days=3))
        d = self.client.get("/api/watchlist/?ids=11,10").json()
        self.assertEqual([p["name"] for p in d["players"]], ["Palmer", "Saka"])
        saka = d["players"][1]
        self.assertEqual((saka["status"], saka["projected"]["9"], saka["fixtures"]["9"][0]["opp"], saka["fixtures"]["9"][0]["home"]), ("d", 6.0, "CHE", True))
        self.assertEqual(self.client.get("/api/watchlist/?ids=x").status_code, 400)
