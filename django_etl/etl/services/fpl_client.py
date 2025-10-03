"""HTTP client for interacting with the official FPL API."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class FPLClient:
    BASE_URL = "https://fantasy.premierleague.com/api/"

    def __init__(self, timeout: int = 15) -> None:
        self.session = requests.Session()
        self.timeout = timeout

    def _get(self, path: str, **params: Any) -> Any:
        url = self.BASE_URL + path
        logger.debug("Requesting %s with params=%s", url, params or None)
        response = self.session.get(url, params=params or None, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_bootstrap_static(self) -> Any:
        return self._get("bootstrap-static/")

    def get_fixtures(self, event_id: int | None = None) -> Any:
        if event_id is None:
            return self._get("fixtures/")
        return self._get("fixtures/", event=event_id)

    def get_element_summary(self, element_id: int) -> Any:
        return self._get(f"element-summary/{element_id}/")

    def get_event_live(self, event_id: int) -> Any:
        return self._get(f"event/{event_id}/live/")

    def get_event_status(self) -> Any:
        return self._get("event-status/")

    def get_set_piece_notes(self) -> Any:
        return self._get("team/set-piece-notes/")

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "FPLClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close()
