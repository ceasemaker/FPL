#!/usr/bin/env python3
"""
Build fixture mapping between SofaSport events and FPL fixtures.
Fetches all past fixtures from SofaSport API and matches them to existing FPL fixtures.
Stores results in the sofasport_fixtures database table.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add Django app to path
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fpl_platform.settings')

import django
django.setup()

from django.db import transaction
from django.conf import settings
from etl.models import Fixture, Team, SofasportFixture
from api_client import SofaSportClient

# Get mappings directory relative to Django project root
# settings.BASE_DIR is /opt/render/project/src/django_etl on Render
MAPPINGS_DIR = Path(settings.BASE_DIR) / 'sofa_sport' / 'mappings'


def load_team_mapping() -> Dict[int, Dict]:
    """Load the team mapping from JSON file."""
    mapping_path = MAPPINGS_DIR / "team_mapping.json"
    with open(mapping_path, 'r') as f:
        return json.load(f)


def get_fpl_team_id(sofasport_team_id: int, team_mapping: Dict) -> Optional[int]:
    """Get FPL team ID from SofaSport team ID."""
    sofasport_id_str = str(sofasport_team_id)
    if sofasport_id_str in team_mapping:
        return team_mapping[sofasport_id_str]['fpl_id']
    return None


def match_fixture_to_fpl(event: Dict, team_mapping: Dict) -> Optional[Fixture]:
    """
    Match a SofaSport event to an FPL fixture.
    
    Matching criteria:
    1. Home and away teams must match
    2. Kickoff time should be close (within same gameweek)
    
    Args:
        event: SofaSport event dict
        team_mapping: Mapping from SofaSport team IDs to FPL team IDs
    
    Returns:
        Matching FPL Fixture or None
    """
    home_team_id = event.get('homeTeam', {}).get('id')
    away_team_id = event.get('awayTeam', {}).get('id')
    start_timestamp = event.get('startTimestamp')
    
    if not all([home_team_id, away_team_id, start_timestamp]):
        return None
    
    # Get FPL team IDs
    fpl_home_id = get_fpl_team_id(home_team_id, team_mapping)
    fpl_away_id = get_fpl_team_id(away_team_id, team_mapping)
    
    if not fpl_home_id or not fpl_away_id:
        return None
    
    # Convert Unix timestamp to datetime
    kickoff_dt = datetime.fromtimestamp(start_timestamp)
    
    # Try to find matching FPL fixture
    # First try exact match on teams
    fixtures = Fixture.objects.filter(
        team_h_id=fpl_home_id,
        team_a_id=fpl_away_id
    ).order_by('kickoff_time')
    
    if not fixtures.exists():
        return None
    
    # If multiple matches, find closest by kickoff time
    if fixtures.count() > 1:
        closest = None
        min_diff = float('inf')
        for fixture in fixtures:
            if fixture.kickoff_time:
                diff = abs((fixture.kickoff_time - kickoff_dt).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest = fixture
        return closest
    
    return fixtures.first()


def create_sofasport_fixture(event: Dict, fpl_fixture: Fixture, team_mapping: Dict) -> SofasportFixture:
    """
    Create or update a SofasportFixture record.
    
    Args:
        event: SofaSport event dict
        fpl_fixture: Matched FPL fixture
        team_mapping: Team mapping dict
    
    Returns:
        SofasportFixture instance
    """
    event_id = event['id']
    home_team_id = event['homeTeam']['id']
    away_team_id = event['awayTeam']['id']
    
    # Get FPL team objects
    fpl_home_id = get_fpl_team_id(home_team_id, team_mapping)
    fpl_away_id = get_fpl_team_id(away_team_id, team_mapping)
    
    home_team = Team.objects.get(id=fpl_home_id) if fpl_home_id else None
    away_team = Team.objects.get(id=fpl_away_id) if fpl_away_id else None
    
    # Extract scores
    home_score = event.get('homeScore', {})
    away_score = event.get('awayScore', {})
    
    # Extract status
    status = event.get('status', {})
    match_status = status.get('type')
    
    # Convert timestamp to datetime
    start_timestamp = event.get('startTimestamp')
    kickoff_time = datetime.fromtimestamp(start_timestamp) if start_timestamp else None
    
    # Create or update the record
    sofasport_fixture, created = SofasportFixture.objects.update_or_create(
        sofasport_event_id=event_id,
        defaults={
            'fixture': fpl_fixture,
            'home_team': home_team,
            'away_team': away_team,
            'sofasport_home_team_id': home_team_id,
            'sofasport_away_team_id': away_team_id,
            'start_timestamp': start_timestamp,
            'kickoff_time': kickoff_time,
            'match_status': match_status,
            'home_score_current': home_score.get('current'),
            'away_score_current': away_score.get('current'),
            'home_score_period1': home_score.get('period1'),
            'away_score_period1': away_score.get('period1'),
            'home_score_period2': home_score.get('period2'),
            'away_score_period2': away_score.get('period2'),
            'has_xg': event.get('hasXg', False),
            'has_player_statistics': event.get('hasEventPlayerStatistics', False),
            'has_heatmap': event.get('hasEventPlayerHeatMap', False),
            'raw_data': event
        }
    )
    
    return sofasport_fixture, created


def main():
    """Main execution function."""
    print("="*80)
    print("BUILDING SOFASPORT FIXTURE MAPPING")
    print("="*80)
    print()
    
    # Initialize client and load mappings
    print("📡 Initializing SofaSport API client...")
    client = SofaSportClient()
    
    print("📂 Loading team mapping...")
    team_mapping = load_team_mapping()
    print(f"   Loaded {len(team_mapping)} team mappings")
    print()
    
    # Fetch all past fixtures
    print("🔍 Fetching all past fixtures from SofaSport API...")
    all_events = client.get_all_fixtures(course='last')
    print(f"   Found {len(all_events)} past events")
    print()
    
    # Match and store fixtures
    print("🔗 Matching SofaSport events to FPL fixtures...")
    matched_count = 0
    unmatched_count = 0
    created_count = 0
    updated_count = 0
    unmatched_events = []
    
    with transaction.atomic():
        for event in all_events:
            event_id = event.get('id')
            home_name = event.get('homeTeam', {}).get('name')
            away_name = event.get('awayTeam', {}).get('name')
            
            # Try to match to FPL fixture
            fpl_fixture = match_fixture_to_fpl(event, team_mapping)
            
            if fpl_fixture:
                sofasport_fixture, created = create_sofasport_fixture(event, fpl_fixture, team_mapping)
                matched_count += 1
                if created:
                    created_count += 1
                    print(f"   ✅ Created: {home_name} vs {away_name} (Event {event_id} → FPL GW{fpl_fixture.event})")
                else:
                    updated_count += 1
                    print(f"   🔄 Updated: {home_name} vs {away_name} (Event {event_id})")
            else:
                unmatched_count += 1
                unmatched_events.append({
                    'event_id': event_id,
                    'home_team': home_name,
                    'away_team': away_name,
                    'home_team_id': event.get('homeTeam', {}).get('id'),
                    'away_team_id': event.get('awayTeam', {}).get('id'),
                    'timestamp': event.get('startTimestamp')
                })
                print(f"   ⚠️  Unmatched: {home_name} vs {away_name} (Event {event_id})")
    
    print()
    print("="*80)
    print("FIXTURE MAPPING SUMMARY")
    print("="*80)
    print(f"Total SofaSport events: {len(all_events)}")
    print(f"Successfully matched: {matched_count}")
    print(f"  - Created new: {created_count}")
    print(f"  - Updated existing: {updated_count}")
    print(f"Unmatched: {unmatched_count}")
    print()
    
    if unmatched_events:
        print("⚠️  UNMATCHED EVENTS:")
        for event in unmatched_events[:10]:  # Show first 10
            dt = datetime.fromtimestamp(event['timestamp']) if event['timestamp'] else 'Unknown'
            print(f"   - {event['home_team']} vs {event['away_team']}")
            print(f"     Event ID: {event['event_id']}, Date: {dt}")
            print(f"     Team IDs: {event['home_team_id']} vs {event['away_team_id']}")
        if len(unmatched_events) > 10:
            print(f"   ... and {len(unmatched_events) - 10} more")
        print()
    
    # Save unmatched events to file for review
    if unmatched_events:
        output_path = MAPPINGS_DIR / "unmatched_fixtures.json"
        with open(output_path, 'w') as f:
            json.dump(unmatched_events, f, indent=2)
        print(f"📝 Unmatched fixtures saved to: {output_path}")
    
    print()
    print("✅ Fixture mapping complete!")


if __name__ == "__main__":
    main()
