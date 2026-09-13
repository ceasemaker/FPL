"""Once-daily Football-Data.co.uk Premier League CSV ingestion.

Football-Data publishes completed-match odds, not reliable future-fixture
prices. This source is therefore stored for historical calibration/backtests
and must never be treated as a live pre-deadline market feed.
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import date
from typing import Any

import requests
from django.utils import timezone

from ..models import RawEndpointSnapshot


BASE_URL = "https://www.football-data.co.uk/mmz4281"
SNAPSHOT_ENDPOINT = "football_data_e0_season"
RUN_ENDPOINT = "football_data_e0_daily_run"
USER_AGENT = "FPL-Decision-System/1.0 daily-local-research"

KEEP_COLUMNS = (
    "Div", "Date", "Time", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
    "HxG", "AxG",
    "AvgH", "AvgD", "AvgA", "MaxH", "MaxD", "MaxA",
    "Avg>2.5", "Avg<2.5", "Max>2.5", "Max<2.5",
    "AvgCH", "AvgCD", "AvgCA", "MaxCH", "MaxCD", "MaxCA",
    "AvgC>2.5", "AvgC<2.5", "MaxC>2.5", "MaxC<2.5",
)


def season_code(on_date: date | None = None) -> str:
    """Return Football-Data's four-digit season folder, e.g. ``2627``."""
    on_date = on_date or timezone.localdate()
    start_year = on_date.year if on_date.month >= 7 else on_date.year - 1
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def csv_url(code: str) -> str:
    return f"{BASE_URL}/{code}/E0.csv"


def parse_premier_league_csv(content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig", errors="replace")
    rows: list[dict[str, str]] = []
    for raw in csv.DictReader(io.StringIO(text)):
        if not raw.get("Date") or not raw.get("HomeTeam") or not raw.get("AwayTeam"):
            continue
        rows.append({column: (raw.get(column) or "").strip() for column in KEEP_COLUMNS})
    return rows


def _attempted_today(run_date: str) -> bool:
    return RawEndpointSnapshot.objects.filter(
        endpoint=RUN_ENDPOINT,
        identifier=run_date,
    ).exists()


def sync_current_season(
    *,
    force: bool = False,
    on_date: date | None = None,
    http_get=requests.get,
) -> dict[str, Any]:
    """Download one CSV and replace the current season snapshot atomically."""
    on_date = on_date or timezone.localdate()
    run_date = on_date.isoformat()
    code = season_code(on_date)
    url = csv_url(code)

    if not force and _attempted_today(run_date):
        return {"status": "skipped_daily", "date": run_date, "requests": 0, "season": code}

    # Claim today's attempt before network I/O, making crashes/restarts safe.
    run = RawEndpointSnapshot.objects.create(
        endpoint=RUN_ENDPOINT,
        identifier=run_date,
        payload={"status": "started", "requests": 1, "season": code, "url": url},
    )
    try:
        response = http_get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*;q=0.8"},
            timeout=30,
        )
        response.raise_for_status()
        content = response.content
        rows = parse_premier_league_csv(content)
        digest = hashlib.sha256(content).hexdigest()
        completed = sum(1 for row in rows if row.get("FTHG") != "" and row.get("FTAG") != "")
        future = len(rows) - completed

        latest = (
            RawEndpointSnapshot.objects.filter(endpoint=SNAPSHOT_ENDPOINT, identifier=code)
            .order_by("-created_at")
            .first()
        )
        changed = latest is None or (latest.payload or {}).get("sha256") != digest
        snapshot_payload = {
            "source_url": url,
            "season": code,
            "sha256": digest,
            "fetched_at": timezone.now().isoformat(),
            "rows": rows,
            "row_count": len(rows),
            "completed_rows": completed,
            "future_rows": future,
        }
        if latest is None:
            RawEndpointSnapshot.objects.create(
                endpoint=SNAPSHOT_ENDPOINT,
                identifier=code,
                payload=snapshot_payload,
            )
        else:
            latest.payload = snapshot_payload
            latest.save(update_fields=["payload", "updated_at"])

        result = {
            "status": "completed",
            "date": run_date,
            "requests": 1,
            "season": code,
            "rows": len(rows),
            "completed_rows": completed,
            "future_rows": future,
            "changed": changed,
        }
        run.payload = {**run.payload, **result}
        run.save(update_fields=["payload", "updated_at"])
        return result
    except Exception as exc:
        run.payload = {**run.payload, "status": "error", "error": str(exc)}
        run.save(update_fields=["payload", "updated_at"])
        raise


def latest_snapshot(code: str | None = None) -> dict[str, Any] | None:
    code = code or season_code()
    row = (
        RawEndpointSnapshot.objects.filter(endpoint=SNAPSHOT_ENDPOINT, identifier=code)
        .order_by("-created_at")
        .first()
    )
    return row.payload if row is not None else None
