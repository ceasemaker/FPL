#!/usr/bin/env python3
"""
Build lineups and player statistics for all SofaSport fixtures.
Fetches lineup data (including embedded player statistics) from SofaSport API
and stores in the sofasport_lineups table.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add Django app to path
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fpl_django.settings')

import django
django.setup()

from django.db import transaction
from etl.models import Athlete, Team, SofasportFixture, SofasportLineup
from api_client import SofaSportClient

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
MAPPINGS_DIR = SCRIPT_DIR.parent / 'mappings'


def load_player_mapping() -> Dict[str, Dict]:
    """Load the player mapping from JSON file."""
    mapping_path = MAPPINGS_DIR / "player_mapping.json"
    with open(mapping_path, 'r') as f:
        return json.load(f)


def get_fpl_athlete_id(sofasport_player_id: int, player_mapping: Dict) -> Optional[int]:
    """Get FPL athlete ID from SofaSport player ID."""
    player_id_str = str(sofasport_player_id)
    if player_id_str in player_mapping:
        return player_mapping[player_id_str]['fpl_id']
    return None


def process_lineup_player(
    player_data: Dict, 
    sofasport_fixture: SofasportFixture,
    team: Team,
    sofasport_team_id: int,
    player_mapping: Dict
) -> Optional[SofasportLineup]:
    """
    Process a single player from lineup data and create/update SofasportLineup record.
    
    Args:
        player_data: Player dict from lineup API (contains 'player', 'statistics', etc.)
        sofasport_fixture: SofasportFixture instance
        team: FPL Team instance
        sofasport_team_id: SofaSport team ID
        player_mapping: Player mapping dict
    
    Returns:
        SofasportLineup instance or None if player not mapped
    """
    player_info = player_data.get('player', {})
    sofasport_player_id = player_info.get('id')
    
    if not sofasport_player_id:
        return None
    
    # Get FPL athlete ID
    fpl_athlete_id = get_fpl_athlete_id(sofasport_player_id, player_mapping)
    if not fpl_athlete_id:
        return None
    
    try:
        athlete = Athlete.objects.get(id=fpl_athlete_id)
    except Athlete.DoesNotExist:
        return None
    
    # Extract player data
    position = player_data.get('position')
    shirt_number = player_data.get('shirtNumber')
    substitute = player_data.get('substitute', False)
    statistics = player_data.get('statistics', {})
    minutes_played = statistics.get('minutesPlayed', 0) if statistics else 0
    player_name = player_info.get('name', '')
    player_slug = player_info.get('slug', '')
    
    # Create or update lineup record
    lineup, created = SofasportLineup.objects.update_or_create(
        athlete=athlete,
        fixture=sofasport_fixture,
        defaults={
            'sofasport_player_id': sofasport_player_id,
            'team': team,
            'sofasport_team_id': sofasport_team_id,
            'position': position,
            'shirt_number': shirt_number,
            'substitute': substitute,
            'minutes_played': minutes_played,
            'statistics': statistics,
            'player_name': player_name,
            'player_slug': player_slug
        }
    )
    
    return lineup, created


def process_fixture_lineups(sofasport_fixture: SofasportFixture, client: SofaSportClient, player_mapping: Dict) -> Dict:
    """
    Process lineups for a single fixture.
    
    Args:
        sofasport_fixture: SofasportFixture instance
        client: SofaSportClient instance
        player_mapping: Player mapping dict
    
    Returns:
        Dict with stats about processing
    """
    event_id = sofasport_fixture.sofasport_event_id
    
    # Fetch lineup data
    lineup_data = client.get_event_lineups(event_id)
    
    if not lineup_data or 'data' not in lineup_data:
        return {'error': 'No lineup data', 'created': 0, 'updated': 0, 'skipped': 0}
    
    data = lineup_data['data']
    confirmed = data.get('confirmed', False)
    
    # Update fixture with lineup confirmation status
    if confirmed:
        sofasport_fixture.lineups_confirmed = True
        sofasport_fixture.save(update_fields=['lineups_confirmed'])
    
    stats = {
        'created': 0,
        'updated': 0,
        'skipped_unmapped': 0,
        'home_players': 0,
        'away_players': 0
    }
    
    # Process home team players
    if 'home' in data:
        home = data['home']
        home_formation = home.get('formation')
        if home_formation:
            sofasport_fixture.home_formation = home_formation
            sofasport_fixture.save(update_fields=['home_formation'])
        
        for player_data in home.get('players', []):
            result = process_lineup_player(
                player_data,
                sofasport_fixture,
                sofasport_fixture.home_team,
                sofasport_fixture.sofasport_home_team_id,
                player_mapping
            )
            if result:
                lineup, created = result
                if created:
                    stats['created'] += 1
                else:
                    stats['updated'] += 1
                stats['home_players'] += 1
            else:
                stats['skipped_unmapped'] += 1
    
    # Process away team players
    if 'away' in data:
        away = data['away']
        away_formation = away.get('formation')
        if away_formation:
            sofasport_fixture.away_formation = away_formation
            sofasport_fixture.save(update_fields=['away_formation'])
        
        for player_data in away.get('players', []):
            result = process_lineup_player(
                player_data,
                sofasport_fixture,
                sofasport_fixture.away_team,
                sofasport_fixture.sofasport_away_team_id,
                player_mapping
            )
            if result:
                lineup, created = result
                if created:
                    stats['created'] += 1
                else:
                    stats['updated'] += 1
                stats['away_players'] += 1
            else:
                stats['skipped_unmapped'] += 1
    
    return stats


def main():
    """Main execution function."""
    print("="*80)
    print("BUILDING SOFASPORT LINEUPS AND PLAYER STATS")
    print("="*80)
    print()
    
    # Initialize client and load mappings
    print("📡 Initializing SofaSport API client...")
    client = SofaSportClient()
    
    print("📂 Loading player mapping...")
    player_mapping = load_player_mapping()
    print(f"   Loaded {len(player_mapping)} player mappings")
    print()
    
    # Get all SofaSport fixtures
    print("🔍 Fetching all SofaSport fixtures from database...")
    fixtures = SofasportFixture.objects.select_related('fixture', 'home_team', 'away_team').order_by('kickoff_time')
    print(f"   Found {fixtures.count()} fixtures to process")
    print()
    
    # Process each fixture
    print("⚽ Processing fixture lineups...")
    total_created = 0
    total_updated = 0
    total_skipped = 0
    fixtures_processed = 0
    fixtures_with_errors = 0
    
    for fixture in fixtures:
        try:
            home = fixture.home_team.name if fixture.home_team else 'Unknown'
            away = fixture.away_team.name if fixture.away_team else 'Unknown'
            gw = fixture.fixture.event if fixture.fixture else '?'
            
            print(f"   Processing GW{gw}: {home} vs {away} (Event {fixture.sofasport_event_id})...")
            
            stats = process_fixture_lineups(fixture, client, player_mapping)
            
            if 'error' in stats:
                print(f"      ⚠️  Error: {stats['error']}")
                fixtures_with_errors += 1
            else:
                total_created += stats['created']
                total_updated += stats['updated']
                total_skipped += stats['skipped_unmapped']
                fixtures_processed += 1
                
                print(f"      ✅ Home: {stats['home_players']} players, Away: {stats['away_players']} players")
                print(f"         Created: {stats['created']}, Updated: {stats['updated']}, Skipped: {stats['skipped_unmapped']}")
        
        except Exception as e:
            print(f"      ❌ Error processing fixture: {e}")
            fixtures_with_errors += 1
            continue
    
    print()
    print("="*80)
    print("LINEUP ETL SUMMARY")
    print("="*80)
    print(f"Total fixtures: {fixtures.count()}")
    print(f"Successfully processed: {fixtures_processed}")
    print(f"Fixtures with errors: {fixtures_with_errors}")
    print()
    print(f"Total lineup records created: {total_created}")
    print(f"Total lineup records updated: {total_updated}")
    print(f"Players skipped (unmapped): {total_skipped}")
    print()
    
    # Show unmapped player summary
    if total_skipped > 0:
        print(f"⚠️  {total_skipped} players were skipped due to missing player mapping")
        print("   These players exist in SofaSport lineups but not in our player_mapping.json")
        print("   Review mappings/players_to_review.md for potential additions")
        print()
    
    print("✅ Lineup and player stats ETL complete!")


if __name__ == "__main__":
    main()
