"""HTTP client for the Premier League's stats API (the "SDP" pulselive host).

This is the backend premierleague.com itself uses; it is unauthenticated but
undocumented. Endpoints and caveats are recorded in PREMIER_LEAGUE_DATA_API.md
at the repo root. Requests are paced and retried because the API can change or
rate-limit without notice.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Iterator

import requests

logger = logging.getLogger(__name__)

PREMIER_LEAGUE = 8  # Opta competition id


class PLStatsClient:
    BASE_URL = "https://sdp-prem-prod.premier-league-prod.pulselive.com/api/"
    # The API only answers browser-origin requests from its own site.
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
                logger.warning("PL stats API %s failed (%s); retry %s in %.1fs", path, exc, attempt, wait)
                time.sleep(wait)
            finally:
                time.sleep(self.delay)
        return None

    def iter_season_players(self, competition: int, season: int) -> Iterator[dict]:
        """Every player with minutes in a season, via the paginated leaderboard.

        Yields the leaderboard's ``playerMetadata`` (id, name, position,
        current team). The leaderboard's own stats are a 64-key subset without
        xG, so callers fetch full sheets with ``get_player_season_stats``.
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

    def get_player_season_stats(self, competition: int, season: int, opta_player_id: str) -> dict:
        """Full season stat sheet (up to ~130 keys, including xG and xGOT)."""
        payload = self._get(
            f"v2/competitions/{competition}/seasons/{season}/players/{opta_player_id}/stats"
        ) or {}
        stats = payload.get("stats")
        return stats if isinstance(stats, dict) else {}
