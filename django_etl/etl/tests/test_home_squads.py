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


class SquadBeforeFreeHitTests(TestCase):
    def setUp(self):
        team = Team.objects.create(id=1, code=14, name="Liverpool", short_name="LIV")
        for i in (1, 2):
            Athlete.objects.create(id=i, code=i, first_name="P", second_name=str(i), web_name=f"P{i}", now_cost=50,
                                   element_type=3, team=team, team_code=14)

    def _client(self):
        from unittest.mock import MagicMock
        client = MagicMock()
        client.get_manager_picks.return_value = {"active_chip": None, "picks": [
            {"element": 1, "position": 1, "is_captain": True}, {"element": 2, "position": 12}, {"element": 999, "position": 13}]}
        return client

    def test_stores_the_previous_squad_once(self):
        from ..services.top100_etl import Top100Config, store_squad_before_free_hit

        client, config = self._client(), Top100Config(sleep_between_requests=0)
        row = {"entry": 7, "player_name": "New", "entry_name": "New FC", "rank": 40, "last_rank": 150}
        store_squad_before_free_hit(client, row, 9, config)
        store_squad_before_free_hit(client, row, 9, config)  # already stored: no second request
        client.get_manager_picks.assert_called_once_with(7, 8)
        manager = Top100Manager.objects.get(entry_id=7, game_week=8)
        self.assertEqual(manager.rank, 150)
        self.assertEqual(sorted(manager.picks.values_list("athlete_id", "position")), [(1, 1), (2, 12)])  # unknown player skipped


class Top100ManagersApiTests(TestCase):
    setUp = HomeSquadsApiTests.setUp

    def test_each_manager_with_their_own_squad(self):
        from ..models import AthleteStat

        first = Top100Manager.objects.create(entry_id=1, game_week=9, player_name="A", entry_name="A FC", rank=1, total_points=700,
                                             event_total=80, active_chip="freehit")
        second = Top100Manager.objects.create(entry_id=2, game_week=9, player_name="B", entry_name="B FC", rank=2)
        squad = [p for p in self.players if p.id not in (3, 9, 15, 19)]
        for i, a in enumerate(squad, 1):
            Top100Pick.objects.create(manager=first, athlete=a, game_week=9, position=i, is_captain=i == 14, is_vice_captain=i == 2,
                                      multiplier=2 if i == 14 else 1)
        Top100Pick.objects.create(manager=second, athlete=squad[0], game_week=9, position=1)  # incomplete: left out
        AthleteStat.objects.create(athlete=squad[13], game_week=9, total_points=12)
        d = self.client.get("/api/home/top100-managers/").json()["top100"]
        self.assertEqual(len(d["managers"]), 1)
        m = d["managers"][0]
        self.assertEqual((m["rank"], m["team"], m["total"], m["gwTotal"], m["chip"]), (1, "A FC", 700, 80, "freehit"))
        self.assertEqual((len(m["xi"]), len(m["bench"]), m["captain"], m["vice"]), (11, 4, squad[13].id, squad[1].id))
        self.assertEqual(m["xi"][0], squad[0].id)  # in pick order
        self.assertEqual(d["players"][str(squad[13].id)]["gwPoints"], 12)
