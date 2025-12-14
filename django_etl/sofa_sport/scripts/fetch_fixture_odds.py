"""
Fetch and store betting odds for upcoming fixtures.

This script:
1. Queries upcoming fixtures from SofasportFixture
2. Fetches odds from SofaSport API (/v1/events/odds/all)
3. Stores 1X2, Over/Under, and BTTS odds in FixtureOdds model
4. Tracks previous odds for movement detection (arrows)

Usage:
    python fetch_fixture_odds.py --days=7  # Fetch odds for next 7 days
    python fetch_fixture_odds.py --event-id=12345  # Fetch odds for specific fixture
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
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
from etl.models import SofasportFixture, FixtureOdds

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

# API configuration
API_HEADERS = {
    "x-rapidapi-key": SOFASPORT_API_KEY,
    "x-rapidapi-host": SOFASPORT_API_HOST
}

# Rate limiting: SofaSport allows 27 calls/second, but we'll be conservative
RATE_LIMIT_DELAY = 0.5  # seconds between requests


def fetch_odds_from_api(event_id: int) -> dict | None:
    """
    Fetch odds for a specific event from SofaSport API.
    
    Args:
        event_id: SofaSport event ID
        
    Returns:
        dict with odds data or None if request fails
    """
    url = "https://sofasport.p.rapidapi.com/v1/events/odds/all"
    params = {
        "event_id": str(event_id),
        "provider_id": "1",  # Default bookmaker
        "odds_format": "decimal"
    }
    
    try:
        response = requests.get(url, headers=API_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch odds for event {event_id}: {e}")
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
    
    if "data" not in odds_data:
        return parsed
    
    for market in odds_data["data"]:
        market_name = market.get("marketName", "").lower()
        market_group = market.get("marketGroup", "").lower()
        choices = market.get("choices", [])
        
        # 1X2 Market (Match Result)
        if market_group == "1x2" and market.get("marketPeriod") == "Full-time":
            for choice in choices:
                name = choice.get("name")
                odds_value = choice.get("fractionalValue")
                
                if odds_value and name:
                    if name == "1":  # Home win
                        parsed["home_odds"] = Decimal(str(odds_value))
                    elif name == "X":  # Draw
                        parsed["draw_odds"] = Decimal(str(odds_value))
                    elif name == "2":  # Away win
                        parsed["away_odds"] = Decimal(str(odds_value))
        
        # Over/Under Market
        elif "over/under" in market_name and "2.5" in market_name:
            parsed["over_under_line"] = Decimal("2.5")
            for choice in choices:
                name = choice.get("name", "").lower()
                odds_value = choice.get("fractionalValue")
                
                if odds_value:
                    if "over" in name:
                        parsed["over_odds"] = Decimal(str(odds_value))
                    elif "under" in name:
                        parsed["under_odds"] = Decimal(str(odds_value))
        
        # Both Teams To Score (BTTS)
        elif "both teams to score" in market_name or market_group == "both teams to score":
            for choice in choices:
                name = choice.get("name", "").lower()
                odds_value = choice.get("fractionalValue")
                
                if odds_value:
                    if name == "yes" or "yes" in name:
                        parsed["btts_yes_odds"] = Decimal(str(odds_value))
                    elif name == "no" or "no" in name:
                        parsed["btts_no_odds"] = Decimal(str(odds_value))
    
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


def sync_upcoming_fixtures_odds(days_ahead: int = 7) -> dict:
    """
    Fetch and store odds for all upcoming fixtures within specified days.
    
    Args:
        days_ahead: Number of days ahead to fetch odds for
        
    Returns:
        dict with success/failure counts
    """
    # Get upcoming fixtures
    now = timezone.now()
    cutoff = now + timedelta(days=days_ahead)
    
    fixtures = SofasportFixture.objects.filter(
        kickoff_time__gte=now,
        kickoff_time__lte=cutoff
    ).order_by('kickoff_time')
    
    total = fixtures.count()
    logger.info(f"Found {total} upcoming fixtures in next {days_ahead} days")
    
    if total == 0:
        logger.warning("No upcoming fixtures found. Run European fixtures sync first.")
        return {"success": 0, "failed": 0, "skipped": 0}
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for i, fixture in enumerate(fixtures, 1):
        logger.info(f"[{i}/{total}] Processing {fixture}")
        
        # Check if fixture is too far in the past (already started/finished)
        if fixture.match_status in ["finished", "inprogress"]:
            logger.info(f"  → Skipping (status: {fixture.match_status})")
            skipped_count += 1
            continue
        
        # Fetch odds from API
        odds_response = fetch_odds_from_api(fixture.sofasport_event_id)
        
        if not odds_response:
            logger.warning(f"  → Failed to fetch odds")
            failed_count += 1
            time.sleep(RATE_LIMIT_DELAY)
            continue
        
        # Parse odds
        parsed_odds = parse_odds_response(odds_response)
        
        # Check if we got valid 1X2 odds
        if not parsed_odds["home_odds"]:
            logger.warning(f"  → No valid odds found in response")
            failed_count += 1
            time.sleep(RATE_LIMIT_DELAY)
            continue
        
        # Update database
        if update_fixture_odds(fixture, parsed_odds):
            success_count += 1
            logger.info(f"  → Success: {parsed_odds['home_odds']} / {parsed_odds['draw_odds']} / {parsed_odds['away_odds']}")
        else:
            failed_count += 1
        
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Odds sync complete!")
    logger.info(f"  ✅ Success: {success_count}")
    logger.info(f"  ❌ Failed: {failed_count}")
    logger.info(f"  ⏭️  Skipped: {skipped_count}")
    logger.info(f"{'='*60}\n")
    
    return {
        "success": success_count,
        "failed": failed_count,
        "skipped": skipped_count
    }


def sync_single_fixture_odds(event_id: int) -> bool:
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
    
    odds_response = fetch_odds_from_api(event_id)
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
        default=7,
        help="Number of days ahead to fetch odds for (default: 7)"
    )
    parser.add_argument(
        "--event-id",
        type=int,
        help="Fetch odds for specific event ID only"
    )
    
    args = parser.parse_args()
    
    if args.event_id:
        success = sync_single_fixture_odds(args.event_id)
        sys.exit(0 if success else 1)
    else:
        result = sync_upcoming_fixtures_odds(days_ahead=args.days)
        sys.exit(0 if result["failed"] == 0 else 1)
