"""
Fetch and store betting odds for upcoming fixtures.

This script:
1. Queries upcoming fixtures from SofasportFixture
2. Fetches odds from Sofascore's free public API (no API key required)
3. Stores 1X2, Over/Under, and BTTS odds in FixtureOdds model
4. Tracks previous odds for movement detection (arrows)

Usage:
    python fetch_fixture_odds.py --days=21  # Daily odds for the next 21 days
    python fetch_fixture_odds.py --status  # Read tally; makes no network call
    python fetch_fixture_odds.py --event-id=12345  # Fetch odds for specific fixture
"""

from __future__ import annotations

import os
import sys
import time
import json
import logging
import random
import re
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from pathlib import Path

import django
import requests
from dotenv import load_dotenv

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fpl_platform.settings")
django.setup()

from django.utils import timezone
from etl.models import Fixture, FixtureOdds, RawEndpointSnapshot, SofasportFixture, Team

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

SOFASPORT_API_KEY = os.getenv("SOFASPORT_API_KEY")
SOFASPORT_API_HOST = os.getenv("SOFASPORT_API_HOST", "sofasport.p.rapidapi.com")
SOFASCORE_PUBLIC_BASE_URL = os.getenv(
    "SOFASCORE_PUBLIC_BASE_URL", "https://api.sofascore.com/api/v1"
).rstrip("/")
SOFASCORE_ODDS_SOURCE = os.getenv("SOFASCORE_ODDS_SOURCE", "public").lower()
SOFASCORE_TOURNAMENT_ID = int(os.getenv("SOFASCORE_TOURNAMENT_ID", "17"))
SOFASCORE_SEASON_ID = int(os.getenv("SOFASCORE_SEASON_ID", "96668"))

# API configuration
API_HEADERS = {
    "x-rapidapi-key": SOFASPORT_API_KEY,
    "x-rapidapi-host": SOFASPORT_API_HOST
}

PUBLIC_API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

# Five calls/minute means at least 12 seconds between starts. The small buffer
# keeps us below the ceiling despite clock/scheduler jitter.
RATE_LIMIT_DELAY = max(12.0, float(os.getenv("SOFASCORE_RATE_LIMIT_DELAY", "12.5")))
MAX_CALLS_PER_DAY = max(1, int(os.getenv("SOFASCORE_MAX_CALLS_PER_DAY", "40")))
CALL_AUDIT_ENDPOINT = "sofascore_public_odds_call"
RUN_AUDIT_ENDPOINT = "sofascore_public_odds_daily_run"
TEAM_MAPPING_PATH = Path(__file__).resolve().parent.parent / "mappings" / "team_mapping.json"


class DailyCallLimitReached(RuntimeError):
    """Raised before a request that would exceed the persistent daily cap."""


class PublicRequestThrottle:
    """Database-backed request pacing and call tally shared by local/Docker runs."""

    def __init__(
        self,
        *,
        run_date: str | None = None,
        min_interval: float = RATE_LIMIT_DELAY,
        max_calls: int = MAX_CALLS_PER_DAY,
    ) -> None:
        self.run_date = run_date or timezone.localdate().isoformat()
        self.min_interval = max(12.0, float(min_interval))
        self.max_calls = max(1, int(max_calls))
        self.blocked = False
        self.exhausted = False

    @property
    def calls_today(self) -> int:
        return RawEndpointSnapshot.objects.filter(
            endpoint=CALL_AUDIT_ENDPOINT,
            identifier=self.run_date,
        ).count()

    def before_request(self, event_id: int, url: str) -> RawEndpointSnapshot:
        if self.calls_today >= self.max_calls:
            self.exhausted = True
            raise DailyCallLimitReached(
                f"daily public odds call cap ({self.max_calls}) reached"
            )

        latest = (
            RawEndpointSnapshot.objects.filter(
                endpoint=CALL_AUDIT_ENDPOINT,
            )
            .order_by("-created_at")
            .first()
        )
        if latest is not None:
            elapsed = (timezone.now() - latest.created_at).total_seconds()
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)

        # Record before transmission so a timeout/crash still consumes budget.
        return RawEndpointSnapshot.objects.create(
            endpoint=CALL_AUDIT_ENDPOINT,
            identifier=self.run_date,
            payload={
                "event_id": event_id,
                "url": url,
                "status": "started",
            },
        )

    @staticmethod
    def finish_request(
        audit: RawEndpointSnapshot,
        *,
        status_code: int | None,
        error: str | None = None,
    ) -> None:
        audit.payload = {
            **audit.payload,
            "status": "finished" if error is None else "error",
            "status_code": status_code,
            "error": error,
        }
        audit.save(update_fields=["payload", "updated_at"])


def _normalize_team_name(name: str | None) -> str:
    normalized = (name or "").lower()
    normalized = normalized.replace("&", "and")
    normalized = re.sub(r"\b(fc|afc|football club)\b", "", normalized)
    return re.sub(r"[^a-z0-9]", "", normalized)


def _team_id_from_sofascore(sofa_id: int | None, sofa_name: str | None) -> int | None:
    if sofa_id is not None:
        try:
            mapping = json.loads(TEAM_MAPPING_PATH.read_text(encoding="utf-8"))
            mapped = (mapping.get(str(sofa_id)) or {}).get("fpl_id")
            if mapped and Team.objects.filter(id=mapped).exists():
                return int(mapped)
        except (OSError, ValueError, TypeError):
            pass

    target = _normalize_team_name(sofa_name)
    if not target:
        return None
    for team in Team.objects.only("id", "name", "short_name"):
        candidates = {
            _normalize_team_name(team.name),
            _normalize_team_name(team.short_name),
        }
        if target in candidates:
            return team.id
    return None


def fetch_public_upcoming_events(throttle: PublicRequestThrottle) -> list[dict]:
    """One schedule request, sharing the same persistent budget as odds calls."""
    url = (
        f"{SOFASCORE_PUBLIC_BASE_URL}/unique-tournament/{SOFASCORE_TOURNAMENT_ID}"
        f"/season/{SOFASCORE_SEASON_ID}/events/next/0"
    )
    audit = None
    try:
        audit = throttle.before_request("premier-league-schedule", url)
        response = requests.get(url, headers=PUBLIC_API_HEADERS, timeout=20)
        throttle.finish_request(audit, status_code=response.status_code)
        if response.status_code == 403:
            throttle.blocked = True
            logger.error("Free Sofascore API blocked the fixture schedule request")
            return []
        response.raise_for_status()
        payload = response.json()
        return payload.get("events") or (payload.get("data") or {}).get("events") or []
    except DailyCallLimitReached as exc:
        logger.warning("Skipping fixture mapping refresh: %s", exc)
        return []
    except (requests.RequestException, ValueError) as exc:
        if audit is not None and audit.payload.get("status") == "started":
            throttle.finish_request(audit, status_code=None, error=str(exc))
        logger.error("Failed to refresh free Sofascore fixtures: %s", exc)
        return []


def refresh_public_fixture_mappings(
    throttle: PublicRequestThrottle,
    *,
    now,
    cutoff,
) -> dict[str, int]:
    """Fill missing Sofa event IDs for current official FPL fixtures."""
    fpl_fixtures = list(
        Fixture.objects.filter(
            kickoff_time__gte=now,
            kickoff_time__lte=cutoff,
        ).select_related("team_h", "team_a")
    )
    if not fpl_fixtures:
        return {"schedule_calls": 0, "mappings_created": 0, "unmapped": 0}

    mapped_fixture_ids = set(
        SofasportFixture.objects.filter(
            fixture_id__in=[fixture.id for fixture in fpl_fixtures]
        ).values_list("fixture_id", flat=True)
    )
    missing = [fixture for fixture in fpl_fixtures if fixture.id not in mapped_fixture_ids]
    if not missing:
        return {"schedule_calls": 0, "mappings_created": 0, "unmapped": 0}

    calls_before = throttle.calls_today
    events = fetch_public_upcoming_events(throttle)
    created = 0
    matched_fixture_ids: set[int] = set()
    for event in events:
        home_data = event.get("homeTeam") or {}
        away_data = event.get("awayTeam") or {}
        home_team_id = _team_id_from_sofascore(home_data.get("id"), home_data.get("name"))
        away_team_id = _team_id_from_sofascore(away_data.get("id"), away_data.get("name"))
        timestamp = event.get("startTimestamp")
        event_id = event.get("id")
        if not all((home_team_id, away_team_id, home_data.get("id"), away_data.get("id"), timestamp, event_id)):
            continue
        event_kickoff = datetime.fromtimestamp(int(timestamp), tz=dt_timezone.utc)
        candidates = [
            fixture for fixture in missing
            if fixture.team_h_id == home_team_id
            and fixture.team_a_id == away_team_id
            and fixture.kickoff_time is not None
            and abs((fixture.kickoff_time - event_kickoff).total_seconds()) <= 36 * 3600
        ]
        if not candidates:
            continue
        fpl_fixture = min(
            candidates,
            key=lambda fixture: abs((fixture.kickoff_time - event_kickoff).total_seconds()),
        )
        home_score = event.get("homeScore") or {}
        away_score = event.get("awayScore") or {}
        _, was_created = SofasportFixture.objects.update_or_create(
            sofasport_event_id=int(event_id),
            defaults={
                "fixture": fpl_fixture,
                "competition": "PL",
                "competition_name": "Premier League",
                "sofasport_tournament_id": SOFASCORE_TOURNAMENT_ID,
                "sofasport_season_id": SOFASCORE_SEASON_ID,
                "home_team_name": home_data.get("name"),
                "away_team_name": away_data.get("name"),
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "sofasport_home_team_id": int(home_data["id"]),
                "sofasport_away_team_id": int(away_data["id"]),
                "start_timestamp": int(timestamp),
                "kickoff_time": event_kickoff,
                "match_status": (event.get("status") or {}).get("type"),
                "home_score_current": home_score.get("current"),
                "away_score_current": away_score.get("current"),
                "has_xg": bool(event.get("hasXg")),
                "has_player_statistics": bool(event.get("hasEventPlayerStatistics")),
                "has_heatmap": bool(event.get("hasEventPlayerHeatMap")),
                "raw_data": event,
            },
        )
        matched_fixture_ids.add(fpl_fixture.id)
        created += int(was_created)

    return {
        "schedule_calls": throttle.calls_today - calls_before,
        "mappings_created": created,
        "unmapped": len(missing) - len(matched_fixture_ids),
    }


def fetch_odds_from_api(
    event_id: int,
    source: str | None = None,
    throttle: PublicRequestThrottle | None = None,
) -> dict | None:
    """
    Fetch odds for a specific event from SofaSport API.
    
    Args:
        event_id: SofaSport event ID
        
    Returns:
        dict with odds data or None if request fails
    """
    source = (source or SOFASCORE_ODDS_SOURCE).lower()
    if source == "public":
        # Provider 1 is the same default bookmaker used by the RapidAPI route.
        # Sofa event/team/tournament/season IDs are unchanged.
        url = f"{SOFASCORE_PUBLIC_BASE_URL}/event/{event_id}/1/odds"
        headers = PUBLIC_API_HEADERS
        params = None
    elif source == "rapidapi":
        url = f"https://{SOFASPORT_API_HOST}/v1/events/odds/all"
        headers = API_HEADERS
        params = {
            "event_id": str(event_id),
            "provider_id": "1",
            "odds_format": "decimal",
        }
    else:
        logger.error("Unknown SOFASCORE_ODDS_SOURCE=%r (use public or rapidapi)", source)
        return None

    for attempt in range(3):
        audit = None
        try:
            if source == "public" and throttle is not None:
                audit = throttle.before_request(event_id, url)
            response = requests.get(url, headers=headers, params=params, timeout=20)
            if audit is not None:
                throttle.finish_request(audit, status_code=response.status_code)
            if response.status_code == 403 and source == "public":
                if throttle is not None:
                    throttle.blocked = True
                logger.error(
                    "Free Sofascore API blocked this host for event %s (HTTP 403); "
                    "stopping without retries",
                    event_id,
                )
                return None
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 2:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 2 ** attempt
                except ValueError:
                    delay = 2 ** attempt
                time.sleep(min(60.0, delay + random.uniform(0, 0.5)))
                continue
            response.raise_for_status()
            return response.json()
        except DailyCallLimitReached as e:
            logger.warning("Skipping event %s: %s", event_id, e)
            return None
        except (requests.exceptions.RequestException, ValueError) as e:
            if audit is not None and audit.payload.get("status") == "started":
                throttle.finish_request(audit, status_code=None, error=str(e))
            logger.error("Failed to fetch %s odds for event %s: %s", source, event_id, e)
            return None
    return None


def _market_rows(odds_data: dict) -> list[dict]:
    """Return markets from either the public or RapidAPI response envelope."""
    data = odds_data.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("markets"), list):
        return data["markets"]
    markets = odds_data.get("markets")
    return markets if isinstance(markets, list) else []


def _decimal_odd(choice: dict) -> Decimal | None:
    """Normalize public fractional odds and RapidAPI decimal odds."""
    decimal_value = choice.get("decimalValue")
    if decimal_value not in (None, ""):
        try:
            return Decimal(str(decimal_value))
        except Exception:
            return None

    value = choice.get("fractionalValue")
    if value in (None, ""):
        value = choice.get("odds") or choice.get("value")
    if value in (None, ""):
        return None
    value = str(value).strip()
    try:
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            return Decimal("1") + (Decimal(numerator) / Decimal(denominator))
        return Decimal(value)
    except Exception:
        return None


def parse_odds_response(odds_data: dict) -> dict:
    """
    Parse odds API response and extract relevant markets.
    
    Args:
        odds_data: Raw API response
        
    Returns:
        dict with parsed odds for different markets
    """
    parsed = {
        "home_odds": None,
        "draw_odds": None,
        "away_odds": None,
        "over_under_line": None,
        "over_odds": None,
        "under_odds": None,
        "btts_yes_odds": None,
        "btts_no_odds": None,
    }
    
    for market in _market_rows(odds_data):
        market_name = market.get("marketName", "").lower()
        market_group = market.get("marketGroup", "").lower()
        choices = market.get("choices", [])
        
        # 1X2 Market (Match Result)
        period = str(market.get("marketPeriod", "")).lower()
        is_full_time = (
            market_group == "1x2"
            or market_name in {"full time", "full-time", "match result"}
            or market.get("marketId") == 1
            or market.get("id") == 1
        )
        if is_full_time and (not period or period in {"full-time", "full time"}):
            for choice in choices:
                name = choice.get("name")
                odds_value = _decimal_odd(choice)
                
                if odds_value and name:
                    if name == "1":  # Home win
                        parsed["home_odds"] = odds_value
                    elif name == "X":  # Draw
                        parsed["draw_odds"] = odds_value
                    elif name == "2":  # Away win
                        parsed["away_odds"] = odds_value
        
        # Over/Under Market
        elif "over/under" in market_name and "2.5" in market_name:
            parsed["over_under_line"] = Decimal("2.5")
            for choice in choices:
                name = choice.get("name", "").lower()
                odds_value = _decimal_odd(choice)
                
                if odds_value:
                    if "over" in name:
                        parsed["over_odds"] = odds_value
                    elif "under" in name:
                        parsed["under_odds"] = odds_value
        
        # Both Teams To Score (BTTS)
        elif "both teams to score" in market_name or market_group == "both teams to score":
            for choice in choices:
                name = choice.get("name", "").lower()
                odds_value = _decimal_odd(choice)
                
                if odds_value:
                    if name == "yes" or "yes" in name:
                        parsed["btts_yes_odds"] = odds_value
                    elif name == "no" or "no" in name:
                        parsed["btts_no_odds"] = odds_value
    
    return parsed


def update_fixture_odds(fixture: SofasportFixture, odds_data: dict) -> bool:
    """
    Update or create FixtureOdds record for a fixture.
    
    Args:
        fixture: SofasportFixture instance
        odds_data: Parsed odds data
        
    Returns:
        True if successfully updated, False otherwise
    """
    try:
        odds_obj, created = FixtureOdds.objects.get_or_create(fixture=fixture)
        
        # Store previous odds before updating (for movement detection)
        if not created and odds_data["home_odds"]:
            odds_obj.prev_home_odds = odds_obj.home_odds
            odds_obj.prev_draw_odds = odds_obj.draw_odds
            odds_obj.prev_away_odds = odds_obj.away_odds
            odds_obj.prev_over_odds = odds_obj.over_odds
            odds_obj.prev_under_odds = odds_obj.under_odds
            odds_obj.prev_btts_yes_odds = odds_obj.btts_yes_odds
            odds_obj.prev_btts_no_odds = odds_obj.btts_no_odds
        
        # Update current odds
        if odds_data["home_odds"]:
            odds_obj.home_odds = odds_data["home_odds"]
        if odds_data["draw_odds"]:
            odds_obj.draw_odds = odds_data["draw_odds"]
        if odds_data["away_odds"]:
            odds_obj.away_odds = odds_data["away_odds"]
        if odds_data["over_under_line"]:
            odds_obj.over_under_line = odds_data["over_under_line"]
        if odds_data["over_odds"]:
            odds_obj.over_odds = odds_data["over_odds"]
        if odds_data["under_odds"]:
            odds_obj.under_odds = odds_data["under_odds"]
        if odds_data["btts_yes_odds"]:
            odds_obj.btts_yes_odds = odds_data["btts_yes_odds"]
        if odds_data["btts_no_odds"]:
            odds_obj.btts_no_odds = odds_data["btts_no_odds"]
        
        odds_obj.save()
        
        action = "Created" if created else "Updated"
        logger.info(f"{action} odds for {fixture}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update odds for {fixture}: {e}")
        return False


def _completed_today(run_date: str) -> bool:
    runs = RawEndpointSnapshot.objects.filter(
        endpoint=RUN_AUDIT_ENDPOINT,
        identifier=run_date,
    ).order_by("-created_at")
    return any((run.payload or {}).get("status") == "completed" for run in runs)


def _store_run_summary(run_date: str, payload: dict) -> None:
    RawEndpointSnapshot.objects.create(
        endpoint=RUN_AUDIT_ENDPOINT,
        identifier=run_date,
        payload=payload,
    )


def daily_status(run_date: str | None = None) -> dict:
    run_date = run_date or timezone.localdate().isoformat()
    latest_run = (
        RawEndpointSnapshot.objects.filter(
            endpoint=RUN_AUDIT_ENDPOINT,
            identifier=run_date,
        )
        .order_by("-created_at")
        .first()
    )
    return {
        "date": run_date,
        "calls_today": RawEndpointSnapshot.objects.filter(
            endpoint=CALL_AUDIT_ENDPOINT,
            identifier=run_date,
        ).count(),
        "max_calls_per_day": MAX_CALLS_PER_DAY,
        "minimum_seconds_between_calls": RATE_LIMIT_DELAY,
        "latest_run": latest_run.payload if latest_run is not None else None,
    }


def sync_upcoming_fixtures_odds(days_ahead: int = 21, *, force: bool = False) -> dict:
    """
    Fetch and store odds for all upcoming fixtures within specified days.
    
    Args:
        days_ahead: Number of days ahead to fetch odds for
        
    Returns:
        dict with success/failure counts
    """
    now = timezone.now()
    run_date = timezone.localdate(now).isoformat()
    if not force and _completed_today(run_date):
        calls_today = RawEndpointSnapshot.objects.filter(
            endpoint=CALL_AUDIT_ENDPOINT,
            identifier=run_date,
        ).count()
        logger.info("Odds collection already completed for %s; no network calls", run_date)
        return {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "skipped_daily": True,
            "api_calls": 0,
            "calls_today": calls_today,
        }

    cutoff = now + timedelta(days=days_ahead)
    throttle = PublicRequestThrottle(run_date=run_date) if SOFASCORE_ODDS_SOURCE == "public" else None
    calls_before = throttle.calls_today if throttle is not None else 0
    mapping_stats = {"schedule_calls": 0, "mappings_created": 0, "unmapped": 0}
    if throttle is not None:
        mapping_stats = refresh_public_fixture_mappings(
            throttle,
            now=now,
            cutoff=cutoff,
        )
        if throttle.blocked or throttle.exhausted:
            stopped_reason = "host_blocked" if throttle.blocked else "daily_call_cap"
            calls_today = throttle.calls_today
            result = {
                "success": 0,
                "failed": 1,
                "skipped": 0,
                "already_fetched": 0,
                "skipped_daily": False,
                "api_calls": calls_today - calls_before,
                "calls_today": calls_today,
                "stopped_reason": stopped_reason,
                **mapping_stats,
            }
            _store_run_summary(run_date, {**result, "status": "completed"})
            return result

    fixtures = SofasportFixture.objects.filter(
        kickoff_time__gte=now,
        kickoff_time__lte=cutoff
    ).select_related("odds").order_by('kickoff_time')
    
    total = fixtures.count()
    logger.info(f"Found {total} upcoming fixtures in next {days_ahead} days")
    
    if total == 0:
        logger.warning("No upcoming fixtures found. Run European fixtures sync first.")
        result = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "skipped_daily": False,
            "api_calls": (
                throttle.calls_today - calls_before if throttle is not None else 0
            ),
            "calls_today": throttle.calls_today if throttle is not None else 0,
            **mapping_stats,
        }
        _store_run_summary(run_date, {**result, "status": "completed"})
        return result
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    already_fetched_count = 0
    stopped_reason = None
    
    for i, fixture in enumerate(fixtures, 1):
        logger.info(f"[{i}/{total}] Processing {fixture}")
        
        # Check if fixture is too far in the past (already started/finished)
        if fixture.match_status in ["finished", "inprogress"]:
            logger.info(f"  → Skipping (status: {fixture.match_status})")
            skipped_count += 1
            continue

        if not force:
            try:
                if timezone.localdate(fixture.odds.last_updated) == timezone.localdate(now):
                    logger.info("  → Skipping (already collected today)")
                    skipped_count += 1
                    already_fetched_count += 1
                    continue
            except FixtureOdds.DoesNotExist:
                pass
        
        # Fetch odds from API
        odds_response = fetch_odds_from_api(
            fixture.sofasport_event_id,
            throttle=throttle,
        )
        
        if not odds_response:
            logger.warning(f"  → Failed to fetch odds")
            failed_count += 1
            if throttle is not None and throttle.blocked:
                stopped_reason = "host_blocked"
                logger.warning("Stopping the daily run after a public API block")
                break
            if throttle is not None and throttle.exhausted:
                stopped_reason = "daily_call_cap"
                logger.warning("Stopping the daily run at the persistent call cap")
                break
            continue
        
        # Parse odds
        parsed_odds = parse_odds_response(odds_response)
        
        # Check if we got valid 1X2 odds
        if not parsed_odds["home_odds"]:
            logger.warning(f"  → No valid odds found in response")
            failed_count += 1
            continue
        
        # Update database
        if update_fixture_odds(fixture, parsed_odds):
            success_count += 1
            logger.info(f"  → Success: {parsed_odds['home_odds']} / {parsed_odds['draw_odds']} / {parsed_odds['away_odds']}")
        else:
            failed_count += 1
        
        if SOFASCORE_ODDS_SOURCE != "public":
            time.sleep(RATE_LIMIT_DELAY)

    calls_today = throttle.calls_today if throttle is not None else 0
    api_calls = calls_today - calls_before if throttle is not None else success_count + failed_count
    result = {
        "success": success_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "already_fetched": already_fetched_count,
        "skipped_daily": False,
        "api_calls": api_calls,
        "calls_today": calls_today,
        "stopped_reason": stopped_reason,
        **mapping_stats,
    }
    # A blocked/capped pass still counts as today's attempt. This prevents Beat,
    # Docker restarts, or manual reruns from hammering the same host that day.
    _store_run_summary(run_date, {**result, "status": "completed"})

    logger.info(f"\n{'='*60}")
    logger.info(f"Odds sync complete!")
    logger.info(f"  ✅ Success: {success_count}")
    logger.info(f"  ❌ Failed: {failed_count}")
    logger.info(f"  ⏭️  Skipped: {skipped_count}")
    logger.info(f"  🌐 API calls this run/today: {api_calls}/{calls_today}")
    logger.info(f"{'='*60}\n")
    
    return result


def sync_single_fixture_odds(event_id: int, *, force: bool = False) -> bool:
    """
    Fetch and store odds for a single fixture by event ID.
    
    Args:
        event_id: SofaSport event ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        fixture = SofasportFixture.objects.get(sofasport_event_id=event_id)
    except SofasportFixture.DoesNotExist:
        logger.error(f"Fixture with event_id {event_id} not found")
        return False
    
    logger.info(f"Fetching odds for {fixture}")
    
    run_date = timezone.localdate().isoformat()
    if not force and _completed_today(run_date):
        logger.warning("Daily odds run already completed; use --force for a deliberate manual retry")
        return False
    throttle = PublicRequestThrottle(run_date=run_date) if SOFASCORE_ODDS_SOURCE == "public" else None
    odds_response = fetch_odds_from_api(event_id, throttle=throttle)
    if not odds_response:
        return False
    
    parsed_odds = parse_odds_response(odds_response)
    if not parsed_odds["home_odds"]:
        logger.warning("No valid odds found")
        return False
    
    return update_fixture_odds(fixture, parsed_odds)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch betting odds for fixtures")
    parser.add_argument(
        "--days",
        type=int,
        default=8,
        help="Number of days ahead to fetch odds for (default: 8)"
    )
    parser.add_argument(
        "--event-id",
        type=int,
        help="Fetch odds for specific event ID only"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Deliberately bypass the once-daily completed-run guard"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print today's persisted call/run tally without making a request"
    )
    
    args = parser.parse_args()

    if args.status:
        print(json.dumps(daily_status(), sort_keys=True))
        sys.exit(0)
    
    if args.event_id:
        success = sync_single_fixture_odds(args.event_id, force=args.force)
        sys.exit(0 if success else 1)
    else:
        result = sync_upcoming_fixtures_odds(days_ahead=args.days, force=args.force)
        print(json.dumps(result, sort_keys=True))
        # Missing/unpriced markets and a blocked host are completed daily
        # attempts, not reasons for an orchestrator to retry and hammer again.
        sys.exit(0)
