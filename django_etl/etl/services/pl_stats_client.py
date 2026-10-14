"""HTTP clients for the Premier League's stats APIs (pulselive).

These are the backends premierleague.com itself uses; they are
unauthenticated but undocumented. Endpoints, coverage and caveats are
recorded in PREMIER_LEAGUE_DATA_API.md at the repo root. Requests are paced
and retried because the APIs can change or rate-limit without notice.

- ``PLStatsClient``: the current site's "SDP" API. Opta ids; ~130 stats per
  player including xG, xA and xG on target. Premier League only in practice.
- ``ClassicStatsClient``: the older API. Pulselive ids (Opta id in
  ``altIds``); ~260 stats per player, no xG; also covers the Championship and
  Champions League.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Iterator

import requests

logger = logging.getLogger(__name__)

PREMIER_LEAGUE = 8  # Opta competition id

# Opta competition id (used for storage) -> classic API competition id.
COMPETITIONS = {
    "premier-league": {"opta": 8, "classic": 1},
    "championship": {"opta": 10, "classic": 12},
    "champions-league": {"opta": 5, "classic": 2},
}

CLASSIC_POSITIONS = {"G": "Goalkeeper", "D": "Defender", "M": "Midfielder", "F": "Forward"}


class _PulseliveClient:
    BASE_URL = ""
    # The APIs only answer browser-origin requests from their own site.
    HEADERS = {"Origin": "https://www.premierleague.com", "Accept": "application/json"}

    def __init__(self, timeout: int = 30, delay: float = 0.4, retries: int = 3) -> None:
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.timeout = timeout
        self.delay = delay
        self.retries = retries

    def _get(self, path: str, **params: Any) -> Any:
        url = self.BASE_URL + path
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(url, params=params or None, timeout=self.timeout)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                if attempt == self.retries:
                    raise
                wait = self.delay * 5 * attempt
                logger.warning("Pulselive %s failed (%s); retry %s in %.1fs", path, exc, attempt, wait)
                time.sleep(wait)
            finally:
                time.sleep(self.delay)
        return None


class PLStatsClient(_PulseliveClient):
    BASE_URL = "https://sdp-prem-prod.premier-league-prod.pulselive.com/api/"

    def iter_season_players(self, competition: int, season: int) -> Iterator[dict]:
        """Every player listed for a season, via the paginated leaderboard.

        Yields the leaderboard's ``playerMetadata`` (id, name, position,
        current team). The leaderboard's own stats are a 64-key subset without
        xG, so callers fetch full sheets with ``get_player_season_stats``.
        Cursor paging can repeat a player across pages; callers upsert.
        """
        cursor = None
        while True:
            params: dict[str, Any] = {"_limit": 100, "_sort": "timePlayed:desc"}
            if cursor:
                params["_next"] = cursor
            page = self._get(
                f"v2/competitions/{competition}/seasons/{season}/players/stats/leaderboard", **params
            ) or {}
            for row in page.get("data", []):
                yield row["playerMetadata"]
            cursor = (page.get("pagination") or {}).get("_next")
            if not cursor or not page.get("data"):
                return

    def get_season_teams(self, competition: int, season: int) -> list[dict]:
        """The clubs in a season (``id`` is the Opta team id)."""
        payload = self._get(f"v1/competitions/{competition}/seasons/{season}/teams", _limit=60) or {}
        rows = payload.get("data", payload) if isinstance(payload, dict) else payload
        return rows if isinstance(rows, list) else []

    def get_team_season_stats(self, competition: int, season: int, opta_team_id: str) -> dict:
        """A club's season sheet (~100 keys incl. xG, xGOT conceded, gamesPlayed)."""
        payload = self._get(
            f"v2/competitions/{competition}/seasons/{season}/teams/{opta_team_id}/stats"
        ) or {}
        stats = payload.get("stats")
        return stats if isinstance(stats, dict) else {}

    def get_player_season_stats(self, competition: int, season: int, opta_player_id: str) -> dict:
        """Full season stat sheet (up to ~130 keys, including xG and xGOT)."""
        payload = self._get(
            f"v2/competitions/{competition}/seasons/{season}/players/{opta_player_id}/stats"
        ) or {}
        stats = payload.get("stats")
        return stats if isinstance(stats, dict) else {}


class ClassicStatsClient(_PulseliveClient):
    BASE_URL = "https://footballapi.pulselive.com/football/"

    def season_id(self, competition: int, start_year: int) -> int | None:
        """The classic API's internal id for a season, e.g. 2026 -> 841 for the PL.

        Labels vary ("2025/26", "English Premier League Season 2026/2027"), so
        match on the first year.
        """
        payload = self._get(f"competitions/{competition}/compseasons", page=0, pageSize=100) or {}
        for season in payload.get("content", []):
            match = re.search(r"(\d{4})/\d{2,4}", season.get("label", ""))
            if match and int(match.group(1)) == start_year:
                return int(season["id"])
        return None

    def iter_players_with_minutes(self, competition: int, season_id: int) -> Iterator[dict]:
        """Every player with minutes in a season, via the minutes leaderboard.

        Yields the leaderboard's ``owner`` (pulselive id, name, position,
        current team, ``altIds.opta``). Players with no minutes are absent.
        """
        page = 0
        while True:
            payload = self._get(
                "stats/ranked/players/mins_played",
                page=page, pageSize=100, compSeasons=season_id, comps=competition, altIds="true",
            ) or {}
            block = payload.get("stats") or {}
            for row in block.get("content", []):
                yield row["owner"]
            page += 1
            if page >= (block.get("pageInfo") or {}).get("numPages", 0):
                return

    def get_player_season_stats(self, player_id: int, competition: int, season_id: int) -> dict:
        """A player's full season sheet as {stat name: value} (~260 stat names)."""
        payload = self._get(
            f"stats/player/{player_id}", comps=competition, compSeasons=season_id
        ) or {}
        return {
            row["name"]: row["value"]
            for row in payload.get("stats", [])
            if isinstance(row, dict) and "name" in row
        }
