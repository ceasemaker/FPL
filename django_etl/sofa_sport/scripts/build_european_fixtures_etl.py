#!/usr/bin/env python3
"""
Build European/Cup fixture mapping for Premier League teams.
Fetches UCL, Europa League, Conference League, FA Cup, and EFL Cup fixtures.
Only stores fixtures involving Premier League teams.

Competition IDs:
- UCL (UEFA Champions League): 7
- UEL (UEFA Europa League): 679
- UECL (UEFA Conference League): 17015
- FAC (FA Cup): 19
- EFL (EFL Cup): 21
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add Django app to path
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fpl_platform.settings')

import django
django.setup()

from django.db import transaction
from django.conf import settings
from etl.models import Team, SofasportFixture, SofasportLineup, Athlete
from api_client import SofaSportClient

# Get mappings directory
MAPPINGS_DIR = Path(settings.BASE_DIR) / 'sofa_sport' / 'mappings'

# Competition configuration
# Format: (code, name, tournament_id, season_id for 2024/25)
COMPETITIONS = {
    'UCL': {
        'name': 'UEFA Champions League',
        'tournament_id': '7',
        'season_id': '61644',  # 2024/25 UCL season
    },
    'UEL': {
        'name': 'UEFA Europa League',
        'tournament_id': '679',
        'season_id': '61645',  # 2024/25 Europa season
    },
    'UECL': {
        'name': 'UEFA Conference League',
        'tournament_id': '17015',
        'season_id': '61648',  # 2024/25 Conference season
    },
    'FAC': {
        'name': 'FA Cup',
        'tournament_id': '19',
        'season_id': '67958',  # 2024/25 FA Cup season
    },
    'EFL': {
        'name': 'EFL Cup',
        'tournament_id': '21',
        'season_id': '62483',  # 2024/25 EFL Cup season
    },
}


def load_team_mapping() -> Dict[int, Dict]:
    """Load the team mapping from JSON file."""
    mapping_path = MAPPINGS_DIR / "team_mapping.json"
    with open(mapping_path, 'r') as f:
        return json.load(f)


def load_player_mapping() -> Dict[int, Dict]:
    """Load the player mapping from JSON file."""
    mapping_path = MAPPINGS_DIR / "player_mapping.json"
    with open(mapping_path, 'r') as f:
        return json.load(f)


def get_pl_team_sofasport_ids(team_mapping: Dict) -> Set[int]:
    """Get set of SofaSport team IDs for all Premier League teams."""
    return {int(sofasport_id) for sofasport_id in team_mapping.keys()}


def get_fpl_team_id(sofasport_team_id: int, team_mapping: Dict) -> Optional[int]:
    """Get FPL team ID from SofaSport team ID."""
    sofasport_id_str = str(sofasport_team_id)
    if sofasport_id_str in team_mapping:
        return team_mapping[sofasport_id_str]['fpl_id']
    return None


def involves_pl_team(event: Dict, pl_team_ids: Set[int]) -> Tuple[bool, int, int]:
    """
    Check if an event involves at least one Premier League team.
    
    Returns:
        Tuple of (involves_pl_team, home_team_id, away_team_id)
    """
    home_team_id = event.get('homeTeam', {}).get('id')
    away_team_id = event.get('awayTeam', {}).get('id')
    
    if not home_team_id or not away_team_id:
        return False, 0, 0
    
    involves_pl = home_team_id in pl_team_ids or away_team_id in pl_team_ids
    return involves_pl, home_team_id, away_team_id


def create_european_fixture(event: Dict, competition_code: str, competition_info: Dict,
                            team_mapping: Dict) -> Tuple[SofasportFixture, bool]:
    """
    Create or update a SofasportFixture record for a European/Cup match.
    
    Args:
        event: SofaSport event dict
        competition_code: Competition code (UCL, UEL, etc.)
        competition_info: Competition info dict
        team_mapping: Team mapping dict
    
    Returns:
        Tuple of (SofasportFixture instance, created bool)
    """
    event_id = event['id']
    home_team_data = event.get('homeTeam', {})
    away_team_data = event.get('awayTeam', {})
    home_team_id = home_team_data.get('id')
    away_team_id = away_team_data.get('id')
    
    # Get FPL team objects if they exist (for PL teams)
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
    
    # Convert timestamp to datetime (UTC)
    start_timestamp = event.get('startTimestamp')
    kickoff_time = datetime.fromtimestamp(start_timestamp, tz=timezone.utc) if start_timestamp else None
    
    # Create or update the record
    sofasport_fixture, created = SofasportFixture.objects.update_or_create(
        sofasport_event_id=event_id,
        defaults={
            'fixture': None,  # No FPL fixture for European/Cup matches
            'competition': competition_code,
            'competition_name': competition_info['name'],
            'sofasport_tournament_id': int(competition_info['tournament_id']),
            'sofasport_season_id': int(competition_info['season_id']),
            'home_team_name': home_team_data.get('name'),
            'away_team_name': away_team_data.get('name'),
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


def fetch_and_store_lineups(client: SofaSportClient, fixture: SofasportFixture, 
                            player_mapping: Dict) -> int:
    """
    Fetch and store player lineups for a European fixture.
    
    Returns:
        Number of lineups created
    """
    event_id = str(fixture.sofasport_event_id)
    response = client.get_event_lineups(event_id)
    
    if not response or 'data' not in response:
        return 0
    
    lineups_created = 0
    data = response['data']
    
    # Process both home and away lineups
    for team_key in ['home', 'away']:
        team_data = data.get(team_key, {})
        
        # Get the SofaSport team ID for this side
        if team_key == 'home':
            sofasport_team_id = fixture.sofasport_home_team_id
            fpl_team = fixture.home_team
        else:
            sofasport_team_id = fixture.sofasport_away_team_id
            fpl_team = fixture.away_team
        
        # Skip if no FPL team mapping (non-PL team)
        if not fpl_team:
            continue
        
        # Process both starting players and substitutes
        for player_list_key in ['players', 'substitutes']:
            players = team_data.get(player_list_key, [])
            is_sub = player_list_key == 'substitutes'
            
            for player_entry in players:
                player_data = player_entry.get('player', {})
                sofasport_player_id = player_data.get('id')
                
                if not sofasport_player_id:
                    continue
                
                # Try to find FPL athlete mapping
                sofasport_id_str = str(sofasport_player_id)
                athlete = None
                fpl_id = None
                
                if sofasport_id_str in player_mapping:
                    fpl_id = player_mapping[sofasport_id_str].get('fpl_id')
                    if fpl_id:
                        try:
                            athlete = Athlete.objects.get(id=fpl_id)
                        except Athlete.DoesNotExist:
                            pass
                
                # Skip non-FPL players since the model requires athlete FK
                if not athlete:
                    continue
                
                # Extract statistics from player entry
                statistics = player_entry.get('statistics', {})
                minutes_played = statistics.get('minutesPlayed', 0)
                
                # Skip unused substitutes (no minutes)
                if minutes_played == 0 and is_sub:
                    continue
                
                # Create lineup record
                lineup, created = SofasportLineup.objects.update_or_create(
                    athlete=athlete,
                    fixture=fixture,
                    defaults={
                        'sofasport_player_id': sofasport_player_id,
                        'team': fpl_team,
                        'sofasport_team_id': sofasport_team_id,
                        'player_name': player_data.get('name', ''),
                        'player_slug': player_data.get('slug'),
                        'shirt_number': player_entry.get('shirtNumber') or player_entry.get('jerseyNumber'),
                        'position': player_entry.get('position'),
                        'substitute': is_sub or player_entry.get('substitute', False),
                        'minutes_played': minutes_played,
                        'statistics': statistics,
                    }
                )
                
                if created:
                    lineups_created += 1
    
    return lineups_created


def sync_competition(client: SofaSportClient, competition_code: str, 
                     competition_info: Dict, team_mapping: Dict, 
                     player_mapping: Dict, pl_team_ids: Set[int],
                     fetch_lineups: bool = True) -> Dict:
    """
    Sync fixtures for a single competition.
    
    Returns:
        Dict with stats (total_events, pl_events, created, updated, lineups)
    """
    stats = {
        'total_events': 0,
        'pl_events': 0,
        'created': 0,
        'updated': 0,
        'lineups_created': 0
    }
    
    print(f"\n{'='*60}")
    print(f"📋 Syncing {competition_info['name']} ({competition_code})")
    print(f"   Tournament ID: {competition_info['tournament_id']}")
    print(f"   Season ID: {competition_info['season_id']}")
    print(f"{'='*60}")
    
    # Fetch all past fixtures for this competition
    print("   🔍 Fetching past fixtures...")
    events = client.get_all_competition_fixtures(
        tournament_id=competition_info['tournament_id'],
        season_id=competition_info['season_id'],
        course='last'
    )
    
    stats['total_events'] = len(events)
    print(f"   Found {len(events)} total events")
    
    # Filter to only events involving PL teams
    pl_events = []
    for event in events:
        involves_pl, home_id, away_id = involves_pl_team(event, pl_team_ids)
        if involves_pl:
            pl_events.append(event)
    
    stats['pl_events'] = len(pl_events)
    print(f"   Found {len(pl_events)} events involving PL teams")
    
    # Store fixtures
    with transaction.atomic():
        for event in pl_events:
            fixture, created = create_european_fixture(
                event, competition_code, competition_info, team_mapping
            )
            
            if created:
                stats['created'] += 1
            else:
                stats['updated'] += 1
            
            # Fetch lineups for finished matches with player statistics
            if fetch_lineups and fixture.match_status == 'finished' and fixture.has_player_statistics:
                lineups = fetch_and_store_lineups(client, fixture, player_mapping)
                stats['lineups_created'] += lineups
    
    print(f"   ✅ Created: {stats['created']}, Updated: {stats['updated']}")
    if fetch_lineups:
        print(f"   👥 Lineups created: {stats['lineups_created']}")
    
    return stats


def main(competitions: Optional[List[str]] = None, fetch_lineups: bool = True):
    """
    Main execution function.
    
    Args:
        competitions: List of competition codes to sync (default: all)
        fetch_lineups: Whether to fetch player lineups (default: True)
    """
    print("="*80)
    print("SYNCING EUROPEAN & CUP FIXTURES FOR PREMIER LEAGUE TEAMS")
    print("="*80)
    
    # Initialize client and load mappings
    print("\n📡 Initializing SofaSport API client...")
    client = SofaSportClient()
    
    print("📂 Loading mappings...")
    team_mapping = load_team_mapping()
    player_mapping = load_player_mapping()
    pl_team_ids = get_pl_team_sofasport_ids(team_mapping)
    
    print(f"   Loaded {len(team_mapping)} team mappings")
    print(f"   Loaded {len(player_mapping)} player mappings")
    print(f"   Tracking {len(pl_team_ids)} Premier League teams")
    
    # Determine which competitions to sync
    comps_to_sync = competitions or list(COMPETITIONS.keys())
    
    # Sync each competition
    all_stats = {}
    for comp_code in comps_to_sync:
        if comp_code not in COMPETITIONS:
            print(f"\n⚠️  Unknown competition: {comp_code}")
            continue
        
        comp_info = COMPETITIONS[comp_code]
        stats = sync_competition(
            client, comp_code, comp_info, 
            team_mapping, player_mapping, pl_team_ids,
            fetch_lineups=fetch_lineups
        )
        all_stats[comp_code] = stats
    
    # Print summary
    print("\n" + "="*80)
    print("📊 SYNC SUMMARY")
    print("="*80)
    
    total_created = 0
    total_updated = 0
    total_lineups = 0
    
    for comp_code, stats in all_stats.items():
        comp_name = COMPETITIONS[comp_code]['name']
        print(f"\n{comp_name}:")
        print(f"   Total events: {stats['total_events']}")
        print(f"   PL team events: {stats['pl_events']}")
        print(f"   Created: {stats['created']}")
        print(f"   Updated: {stats['updated']}")
        if fetch_lineups:
            print(f"   Lineups: {stats['lineups_created']}")
        
        total_created += stats['created']
        total_updated += stats['updated']
        total_lineups += stats['lineups_created']
    
    print(f"\n{'='*40}")
    print(f"TOTAL: {total_created} created, {total_updated} updated")
    if fetch_lineups:
        print(f"TOTAL LINEUPS: {total_lineups}")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync European/Cup fixtures for PL teams')
    parser.add_argument(
        '--competitions', '-c',
        nargs='+',
        choices=['UCL', 'UEL', 'UECL', 'FAC', 'EFL'],
        help='Specific competitions to sync (default: all)'
    )
    parser.add_argument(
        '--no-lineups',
        action='store_true',
        help='Skip fetching player lineups'
    )
    
    args = parser.parse_args()
    main(competitions=args.competitions, fetch_lineups=not args.no_lineups)
