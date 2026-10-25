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
