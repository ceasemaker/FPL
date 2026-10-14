from __future__ import annotations

from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase

from ..models import Athlete, PlayerSeasonStat, Team
from ..services.pl_stats_client import PLStatsClient


def _response(payload, status=200):
    response = Mock(status_code=status)
    response.json.return_value = payload
    response.raise_for_status = Mock()
    return response


class PLStatsClientTests(TestCase):
    def test_iter_season_players_follows_the_cursor(self) -> None:
        client = PLStatsClient(delay=0)
        pages = [
            _response({"pagination": {"_next": "abc"}, "data": [{"playerMetadata": {"id": "1"}}]}),
            _response({"pagination": {"_next": None}, "data": [{"playerMetadata": {"id": "2"}}]}),
        ]
        with patch.object(client.session, "get", side_effect=pages) as get:
            ids = [p["id"] for p in client.iter_season_players(8, 2025)]

        self.assertEqual(ids, ["1", "2"])
        self.assertEqual(get.call_args_list[1].kwargs["params"]["_next"], "abc")

    def test_missing_player_returns_empty_stats(self) -> None:
        client = PLStatsClient(delay=0)
        with patch.object(client.session, "get", return_value=_response(None, status=404)):
            self.assertEqual(client.get_player_season_stats(8, 2025, "999"), {})


class SyncPLSeasonStatsCommandTests(TestCase):
    def setUp(self) -> None:
        team = Team.objects.create(id=11, code=43, name="Man City", short_name="MCI")
        self.haaland = Athlete.objects.create(
            id=411, code=223094, web_name="Haaland", first_name="Erling", second_name="Haaland",
            element_type=4, team=team, team_code=43, now_cost=150,
        )

    def _run(self) -> str:
        players = [
            {"id": "223094", "name": "Erling Haaland", "position": "Forward", "currentTeam": {"name": "Manchester City"}},
            {"id": "100", "name": "Departed Player", "position": "Defender", "currentTeam": {"name": "Elsewhere"}},
        ]
        sheets = {
            "223094": {"goals": 27.0, "expectedGoals": 25.74, "expectedGoalsOnTarget": 23.29},
            "100": {"goals": 1.0},
        }
        out = StringIO()
        with patch.object(PLStatsClient, "iter_season_players", return_value=iter(players)), patch.object(
            PLStatsClient, "get_player_season_stats", side_effect=lambda c, s, pid: sheets[pid]
        ):
            call_command("sync_pl_season_stats", "--season", "2025", "--delay", "0", stdout=out)
        return out.getvalue()

    def test_loads_and_links_season_stats(self) -> None:
        output = self._run()

        self.assertIn("2 created", output)
        haaland = PlayerSeasonStat.objects.get(opta_player_id="223094", season=2025)
        self.assertEqual(haaland.athlete, self.haaland)
        self.assertEqual(haaland.stats["expectedGoalsOnTarget"], 23.29)
        departed = PlayerSeasonStat.objects.get(opta_player_id="100")
        self.assertIsNone(departed.athlete)

    def test_rerun_updates_instead_of_duplicating(self) -> None:
        self._run()
        output = self._run()

        self.assertIn("0 created, 2 updated", output)
        self.assertEqual(PlayerSeasonStat.objects.count(), 2)
