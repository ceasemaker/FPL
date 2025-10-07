#!/usr/bin/env python3
"""
Build season statistics for all mapped players.
Fetches aggregated season stats from SofaSport API and stores in sofasport_player_season_stats table.
"""

import os
import sys
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Optional

# Add Django app to path
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fpl_django.settings')

import django
django.setup()

from django.db import transaction
from django.conf import settings
from etl.models import Athlete, Team, SofasportPlayerSeasonStats
from api_client import SofaSportClient

# Get mappings directory relative to Django project root
MAPPINGS_DIR = Path(settings.BASE_DIR) / 'sofa_sport' / 'mappings'


def load_player_mapping() -> Dict[str, Dict]:
    """Load the player mapping from JSON file."""
    mapping_path = MAPPINGS_DIR / "player_mapping.json"
    with open(mapping_path, 'r') as f:
        return json.load(f)


def safe_decimal(value, max_digits: int = 10, decimal_places: int = 2) -> Optional[Decimal]:
    """
    Safely convert a value to Decimal with specified precision.
    Returns None if conversion fails.
    """
    if value is None:
        return None
    try:
        # Convert to string first to handle floats properly
        decimal_value = Decimal(str(value))
        # Round to specified decimal places
        return decimal_value.quantize(Decimal(10) ** -decimal_places)
    except (InvalidOperation, ValueError, TypeError):
        return None


def safe_int(value) -> Optional[int]:
    """Safely convert a value to int. Returns None if conversion fails."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def process_player_season_stats(
    player_mapping_entry: Dict,
    client: SofaSportClient
) -> Optional[SofasportPlayerSeasonStats]:
    """
    Process season statistics for a single player.
    
    Args:
        player_mapping_entry: Player mapping dict containing fpl_id, sofasport_id, etc.
        client: SofaSportClient instance
    
    Returns:
        SofasportPlayerSeasonStats instance or None if error
    """
    fpl_id = player_mapping_entry.get('fpl_id')
    sofasport_player_id = player_mapping_entry.get('sofasport_id')
    fpl_team_id = player_mapping_entry.get('fpl_team_id')
    sofasport_team_id = player_mapping_entry.get('sofasport_team_id')
    
    if not all([fpl_id, sofasport_player_id]):
        return None
    
    try:
        athlete = Athlete.objects.get(id=fpl_id)
    except Athlete.DoesNotExist:
        return None
    
    try:
        team = Team.objects.get(id=fpl_team_id) if fpl_team_id else None
    except Team.DoesNotExist:
        team = None
    
    # Fetch season statistics from API
    try:
        stats_data = client.get_player_season_statistics(str(sofasport_player_id))
    except Exception as e:
        print(f"         ❌ API error: {e}")
        return None
    
    if not stats_data or 'data' not in stats_data:
        return None
    
    data = stats_data['data']
    statistics = data.get('statistics', {})
    team_data = data.get('team', {})
    
    # Extract and convert key statistics
    # Use safe conversions to handle None values and type mismatches
    
    # Create or update season stats record
    season_stats, created = SofasportPlayerSeasonStats.objects.update_or_create(
        athlete=athlete,
        season_id='76986',  # 2025/26 season
        defaults={
            'sofasport_player_id': sofasport_player_id,
            'team': team,
            'sofasport_team_id': sofasport_team_id or team_data.get('id'),
            
            # Key stats
            'rating': safe_decimal(statistics.get('rating')),
            'total_rating': safe_decimal(statistics.get('totalRating'), 8, 2),
            'count_rating': safe_int(statistics.get('countRating')),
            'minutes_played': safe_int(statistics.get('minutesPlayed')),
            'appearances': safe_int(statistics.get('appearances')),
            
            # Attacking stats
            'goals': safe_int(statistics.get('goals')),
            'assists': safe_int(statistics.get('assists')),
            'expected_assists': safe_decimal(statistics.get('expectedAssists')),
            'big_chances_created': safe_int(statistics.get('bigChancesCreated')),
            'big_chances_missed': safe_int(statistics.get('bigChancesMissed')),
            'total_shots': safe_int(statistics.get('totalShots')),
            'shots_on_target': safe_int(statistics.get('shotsOnTarget')),
            
            # Passing stats
            'accurate_passes': safe_int(statistics.get('accuratePasses')),
            'total_passes': safe_int(statistics.get('totalPasses')),
            'accurate_passes_percentage': safe_decimal(statistics.get('accuratePassesPercentage'), 5, 2),
            'key_passes': safe_int(statistics.get('keyPasses')),
            'accurate_long_balls': safe_int(statistics.get('accurateLongBalls')),
            'accurate_long_balls_percentage': safe_decimal(statistics.get('accurateLongBallsPercentage'), 5, 2),
            
            # Defensive stats
            'tackles': safe_int(statistics.get('tackles')),
            'interceptions': safe_int(statistics.get('interceptions')),
            'clearances': safe_int(statistics.get('clearances')),
            
            # Duel stats
            'total_duels_won': safe_int(statistics.get('totalDuelsWon')),
            'total_duels_won_percentage': safe_decimal(statistics.get('totalDuelsWonPercentage'), 5, 2),
            'aerial_duels_won': safe_int(statistics.get('aerialDuelsWon')),
            'ground_duels_won': safe_int(statistics.get('groundDuelsWon')),
            
            # Discipline
            'yellow_cards': safe_int(statistics.get('yellowCards')),
            'red_cards': safe_int(statistics.get('redCards')),
            'fouls': safe_int(statistics.get('fouls')),
            'was_fouled': safe_int(statistics.get('wasFouled')),
            
            # Goalkeeper stats
            'saves': safe_int(statistics.get('saves')),
            'saves_percentage': safe_decimal(statistics.get('savedShotsFromInsideTheBoxPercentage'), 5, 2),
            'clean_sheets': safe_int(statistics.get('cleanSheet')),
            'goals_conceded': safe_int(statistics.get('goalsConceded')),
            
            # Store full statistics JSON
            'statistics': statistics
        }
    )
    
    return season_stats, created


def main():
    """Main execution function."""
    print("="*80)
    print("BUILDING SOFASPORT SEASON STATISTICS")
    print("="*80)
    print()
    
    # Initialize client and load mappings
    print("📡 Initializing SofaSport API client...")
    client = SofaSportClient()
    
    print("📂 Loading player mapping...")
    player_mapping = load_player_mapping()
    print(f"   Loaded {len(player_mapping)} player mappings")
    print()
    
    # Process each mapped player
    print("📊 Fetching season statistics for all mapped players...")
    print("   (This will take a while due to API rate limiting...)")
    print()
    
    total_processed = 0
    total_created = 0
    total_updated = 0
    total_errors = 0
    total_no_data = 0
    
    for sofasport_id, player_data in player_mapping.items():
        player_name = player_data.get('sofasport_name', 'Unknown')
        fpl_name = player_data.get('fpl_web_name', 'Unknown')
        team_name = player_data.get('fpl_team_id', '?')
        
        print(f"   Processing: {player_name} ({fpl_name})...")
        
        try:
            result = process_player_season_stats(player_data, client)
            
            if result:
                season_stats, created = result
                total_processed += 1
                if created:
                    total_created += 1
                    rating = season_stats.rating or 'N/A'
                    goals = season_stats.goals or 0
                    assists = season_stats.assists or 0
                    mins = season_stats.minutes_played or 0
                    print(f"      ✅ Created: Rating {rating}, G:{goals} A:{assists}, Mins:{mins}")
                else:
                    total_updated += 1
                    print(f"      🔄 Updated")
            else:
                total_no_data += 1
                print(f"      ⚠️  No data available")
        
        except Exception as e:
            total_errors += 1
            print(f"      ❌ Error: {e}")
            continue
    
    print()
    print("="*80)
    print("SEASON STATS ETL SUMMARY")
    print("="*80)
    print(f"Total players in mapping: {len(player_mapping)}")
    print(f"Successfully processed: {total_processed}")
    print(f"  - Created new: {total_created}")
    print(f"  - Updated existing: {total_updated}")
    print(f"No data available: {total_no_data}")
    print(f"Errors: {total_errors}")
    print()
    
    # Show top players by rating
    print("🌟 TOP 10 PLAYERS BY RATING:")
    top_players = SofasportPlayerSeasonStats.objects.filter(
        rating__isnull=False
    ).select_related('athlete', 'team').order_by('-rating')[:10]
    
    for i, stats in enumerate(top_players, 1):
        print(f"   {i}. {stats.athlete.web_name} ({stats.team.name if stats.team else 'Unknown'})")
        print(f"      Rating: {stats.rating}, Goals: {stats.goals or 0}, Assists: {stats.assists or 0}, Mins: {stats.minutes_played or 0}")
    
    print()
    print("✅ Season statistics ETL complete!")


if __name__ == "__main__":
    main()
