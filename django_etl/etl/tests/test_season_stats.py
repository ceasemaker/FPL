from __future__ import annotations

from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ..models import Athlete, PlayerSeasonStat, Team
from ..services.pl_stats_client import ClassicStatsClient, PLStatsClient


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


class ClassicStatsClientTests(TestCase):
    def test_season_id_matches_either_label_format(self) -> None:
        client = ClassicStatsClient(delay=0)
        seasons = {"content": [
            {"label": "English Premier League Season 2026/2027", "id": 841.0},
            {"label": "2025/26", "id": 777.0},
        ]}
        with patch.object(client.session, "get", return_value=_response(seasons)):
            self.assertEqual(client.season_id(1, 2026), 841)
            self.assertEqual(client.season_id(1, 2025), 777)
            self.assertIsNone(client.season_id(1, 2019))

    def test_iter_players_with_minutes_walks_every_page(self) -> None:
        client = ClassicStatsClient(delay=0)
        pages = [
            _response({"stats": {"pageInfo": {"numPages": 2}, "content": [{"owner": {"id": 1.0}}]}}),
            _response({"stats": {"pageInfo": {"numPages": 2}, "content": [{"owner": {"id": 2.0}}]}}),
        ]
        with patch.object(client.session, "get", side_effect=pages):
            ids = [o["id"] for o in client.iter_players_with_minutes(2, 846)]
        self.assertEqual(ids, [1.0, 2.0])

    def test_player_sheet_becomes_a_name_value_dict(self) -> None:
        client = ClassicStatsClient(delay=0)
        sheet = {"stats": [{"name": "goals", "value": 3.0}, {"name": "touches", "value": 210.0}]}
        with patch.object(client.session, "get", return_value=_response(sheet)):
            self.assertEqual(client.get_player_season_stats(1, 2, 846), {"goals": 3.0, "touches": 210.0})


class SyncSeasonStatsCommandTests(TestCase):
    def setUp(self) -> None:
        team = Team.objects.create(id=11, code=43, name="Man City", short_name="MCI")
        self.haaland = Athlete.objects.create(
            id=411, code=223094, web_name="Haaland", first_name="Erling", second_name="Haaland",
            element_type=4, team=team, team_code=43, now_cost=150,
        )

    def _run_sdp(self) -> str:
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
            call_command("sync_season_stats", "--season", "2025", "--delay", "0", stdout=out)
        return out.getvalue()

    def test_loads_and_links_sdp_season_stats(self) -> None:
        output = self._run_sdp()

        self.assertIn("2 created", output)
        haaland = PlayerSeasonStat.objects.get(source="sdp", opta_player_id="223094", season=2025)
        self.assertEqual(haaland.athlete, self.haaland)
        self.assertEqual(haaland.competition_id, 8)
        self.assertEqual(haaland.stats["expectedGoalsOnTarget"], 23.29)
        self.assertIsNone(PlayerSeasonStat.objects.get(opta_player_id="100").athlete)

    def test_rerun_updates_instead_of_duplicating(self) -> None:
        self._run_sdp()
        output = self._run_sdp()

        self.assertIn("0 created, 2 updated", output)
        self.assertEqual(PlayerSeasonStat.objects.count(), 2)

    def test_classic_champions_league_rows_sit_beside_sdp_rows(self) -> None:
        self._run_sdp()
        owners = [
            {"id": 65970.0, "name": {"display": "Erling Haaland"}, "info": {"position": "F"},
             "currentTeam": {"name": "Manchester City"}, "altIds": {"opta": "p223094"}},
            {"id": 5.0, "name": {"display": "No Opta Id"}, "info": {"position": "M"}, "currentTeam": {}},
        ]
        out = StringIO()
        with patch.object(ClassicStatsClient, "season_id", return_value=846), patch.object(
            ClassicStatsClient, "iter_players_with_minutes", return_value=iter(owners)
        ), patch.object(
            ClassicStatsClient, "get_player_season_stats", return_value={"goals": 2.0, "touches": 150.0}
        ):
            call_command(
                "sync_season_stats", "--season", "2025", "--source", "classic",
                "--competition", "champions-league", "--delay", "0", stdout=out,
            )

        ucl = PlayerSeasonStat.objects.get(source="classic", opta_player_id="223094")
        self.assertEqual(ucl.competition_id, 5)
        self.assertEqual(ucl.source_player_id, "65970")
        self.assertEqual(ucl.position, "Forward")
        self.assertEqual(ucl.athlete, self.haaland)
        self.assertTrue(PlayerSeasonStat.objects.filter(source="classic", opta_player_id="pl5").exists())
        # The SDP Premier League row for the same player is untouched.
        self.assertTrue(PlayerSeasonStat.objects.filter(source="sdp", opta_player_id="223094", competition_id=8).exists())

    def test_classic_season_missing_is_an_error(self) -> None:
        with patch.object(ClassicStatsClient, "season_id", return_value=None), self.assertRaises(CommandError):
            call_command(
                "sync_season_stats", "--season", "1999", "--source", "classic",
                "--competition", "championship", "--delay", "0", stdout=StringIO(),
            )
