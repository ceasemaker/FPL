from __future__ import annotations

from collections import Counter

from django.core.cache import cache
from django.test import TestCase

from ..models import Athlete, Team, Top100Manager, Top100Pick
from ..services.home_squads import pick_xi


class PickXiTests(TestCase):
    def test_best_legal_formation_and_bench_order(self):
        # Five strong midfielders, weak defenders: the XI still needs three defenders.
        squad = ([{"id": i, "type": 1, "s": 10 - i} for i in (1, 2)]
                 + [{"id": i, "type": 2, "s": 1} for i in range(10, 15)]
                 + [{"id": i, "type": 3, "s": 9} for i in range(20, 25)]
                 + [{"id": i, "type": 4, "s": 8} for i in range(30, 33)])
        xi, bench = pick_xi(squad, lambda p: p["s"])
        types = _types(squad, xi)
        self.assertEqual((len(xi), types[1], types[2], types[3], types[4]), (11, 1, 3, 5, 2))
        self.assertEqual(bench[0], 2)  # the second goalkeeper sits first on the bench
        self.assertEqual(len(bench), 4)


def _types(squad, ids):
    by_id = {p["id"]: p["type"] for p in squad}
    return Counter(by_id[i] for i in ids)


class HomeSquadsApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.liv = Team.objects.create(id=1, code=14, name="Liverpool", short_name="LIV")
        self.ars = Team.objects.create(id=2, code=3, name="Arsenal", short_name="ARS")
        self.players = []
        n = 0
        # One more of each position than a squad holds, all at Liverpool but the first.
        for t, count in ((1, 3), (2, 6), (3, 6), (4, 4)):
            for k in range(count):
                n += 1
                self.players.append(Athlete.objects.create(
                    id=n, code=1000 + n, first_name="P", second_name=str(n), web_name=f"P{n}", now_cost=50,
                    element_type=t, team=self.ars if n == 1 else self.liv, team_code=14, total_points=100 - n))

    def test_team_of_the_season_is_the_top_scorers_in_each_position(self):
        d = self.client.get("/api/home/squads/").json()["season"]
        self.assertEqual([p["type"] for p in d["players"]].count(2), 5)
        self.assertEqual(len(d["players"]), 15)
        self.assertNotIn(3, [p["id"] for p in d["players"]])  # the third goalkeeper misses out
        self.assertEqual((len(d["xi"]), len(d["bench"])), (11, 4))
        self.assertEqual(d["captain"], 1)  # most points overall
        self.assertEqual(d["players"][0]["teamShort"], "ARS")

    def test_top100_counts_free_hit_managers_with_their_previous_squad(self):
        normal = Top100Manager.objects.create(entry_id=1, game_week=9, player_name="A", entry_name="A", rank=1)
        free_hit = Top100Manager.objects.create(entry_id=2, game_week=9, player_name="B", entry_name="B", rank=2, active_chip="freehit")
        before = Top100Manager.objects.create(entry_id=2, game_week=8, player_name="B", entry_name="B", rank=3)
        squad = [p for p in self.players if p.id not in (3, 9, 15, 19)]  # 2/5/5/3
        for i, a in enumerate(squad, 1):
            Top100Pick.objects.create(manager=normal, athlete=a, game_week=9, position=i, is_captain=a.id == 16)
            Top100Pick.objects.create(manager=before, athlete=a, game_week=8, position=i, is_captain=a.id == 16)
        Top100Pick.objects.create(manager=free_hit, athlete=self.players[2], game_week=9, position=1)  # Free Hit only
        d = self.client.get("/api/home/squads/").json()["top100"]
        ids = [p["id"] for p in d["players"]]
        self.assertEqual((d["gameweek"], d["managers"], d["freeHit"]), (9, 2, 1))
        self.assertNotIn(3, ids)  # owned only in a Free Hit squad
        self.assertEqual(len(ids), 15)
        self.assertEqual(d["captain"], 16)
        self.assertEqual({p["owned"] for p in d["players"]}, {100})

    def test_only_the_latest_sync_counts(self):
        from django.utils import timezone

        current = Top100Manager.objects.create(entry_id=1, game_week=9, player_name="A", entry_name="A", rank=1)
        dropped = Top100Manager.objects.create(entry_id=5, game_week=9, player_name="E", entry_name="E", rank=1, active_chip="freehit")
        Top100Manager.objects.filter(id=dropped.id).update(updated_at=timezone.now() - timezone.timedelta(days=2))
        squad = [p for p in self.players if p.id not in (3, 9, 15, 19)]
        for i, a in enumerate(squad, 1):
            Top100Pick.objects.create(manager=current, athlete=a, game_week=9, position=i)
        Top100Pick.objects.create(manager=dropped, athlete=self.players[2], game_week=9, position=1)
        d = self.client.get("/api/home/squads/").json()["top100"]
        self.assertEqual((d["managers"], d["freeHit"]), (1, 0))
        self.assertNotIn(3, [p["id"] for p in d["players"]])

    def test_no_top100_data_yet(self):
        self.assertIsNone(self.client.get("/api/home/squads/").json()["top100"])
