"""
ETL Script: Fetch Player Heatmap Data

This script collects player movement heatmap coordinates from the SofaSport API
for qualifying players based on selective criteria.

Instead of collecting all 2,733 lineup records (~23 minutes), we use smart filtering
to collect ~1,000 heatmaps (~8 minutes) for the most valuable/interesting players.

Filtering Criteria (ANY met = collect heatmap):
1. Played ≥60 minutes
2. Rating ≥7.0
3. Goals + Assists ≥1
4. Player's total FPL points ≥30
5. Started the match (not substitute)

Process:
1. Query all SofasportLineup records
2. Apply filtering criteria to identify qualifying players
3. For each qualifying player:
   - Check if heatmap already exists (skip if so)
   - Call get_player_heatmap(player_id, event_id)
   - Store coordinates in SofasportHeatmap table
4. Track statistics and display summary

API Response Structure:
{
  "data": [
    {"x": 45, "y": 50},
    {"x": 46, "y": 50},
    {"x": 45, "y": 51},
    ...
  ]
}

Coordinates are on 0-100 grid representing the pitch.
"""
import os
import sys
import django
from typing import Dict, List

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fpl_platform.settings')
django.setup()

from api_client import SofaSportClient
from etl.models import SofasportLineup, SofasportHeatmap


def should_collect_heatmap(lineup: SofasportLineup) -> tuple[bool, List[str]]:
    """
    Determine if heatmap should be collected for this player.
    
    Returns:
        (should_collect, reasons_met) - Bool and list of criteria that were met
    """
    reasons = []
    stats = lineup.statistics or {}
    
    # Criteria 1: High minutes (≥60)
    minutes = stats.get('minutesPlayed', 0) or 0
    if minutes >= 60:
        reasons.append(f"mins≥60({minutes})")
    
    # Criteria 2: High rating (≥7.0)
    rating = float(stats.get('rating', 0) or 0)
    if rating >= 7.0:
        reasons.append(f"rating≥7.0({rating:.2f})")
    
    # Criteria 3: Goal contributor (goals + assists ≥1)
    goals = stats.get('goals', 0) or 0
    assists = stats.get('goalAssist', 0) or 0
    if (goals + assists) >= 1:
        reasons.append(f"G+A≥1({goals}+{assists})")
    
    # Criteria 4: High FPL value (total_points ≥30)
    if lineup.athlete and lineup.athlete.total_points >= 30:
        reasons.append(f"FPL≥30pts({lineup.athlete.total_points})")
    
    # Criteria 5: Started (not substitute)
    if not lineup.substitute:
        reasons.append("started")
    
    return len(reasons) > 0, reasons


def process_heatmaps(client: SofaSportClient) -> Dict:
    """
    Process lineups to collect heatmaps for qualifying players.
    
    Returns:
        dict with statistics: total, qualifying, collected, skipped, errors
    """
    stats = {
        'total_lineups': 0,
        'qualifying': 0,
        'collected': 0,
        'skipped_exists': 0,
        'skipped_no_data': 0,
        'skipped_not_qualifying': 0,
        'errors': 0
    }
    
    # Get all lineups
    lineups = SofasportLineup.objects.select_related(
        'athlete', 'fixture', 'team'
    ).order_by('fixture__fixture__event', 'team__name')
    
    total_lineups = lineups.count()
    stats['total_lineups'] = total_lineups
    
    print(f"\n{'='*70}")
    print(f"Analyzing {total_lineups} lineup records for heatmap collection...")
    print(f"{'='*70}\n")
    
    # First pass: Count qualifying players
    print("🔍 Identifying qualifying players...")
    qualifying_lineups = []
    for lineup in lineups:
        should_collect, reasons = should_collect_heatmap(lineup)
        if should_collect:
            qualifying_lineups.append((lineup, reasons))
    
    stats['qualifying'] = len(qualifying_lineups)
    stats['skipped_not_qualifying'] = total_lineups - len(qualifying_lineups)
    
    print(f"✅ Found {stats['qualifying']} qualifying players")
    print(f"⏭️  Skipping {stats['skipped_not_qualifying']} non-qualifying players")
    print(f"\n{'='*70}")
    print(f"Starting heatmap collection for {stats['qualifying']} players...")
    print(f"{'='*70}\n")
    
    # Second pass: Collect heatmaps
    for i, (lineup, reasons) in enumerate(qualifying_lineups, 1):
        player_name = lineup.player_name or 'Unknown'
        gw = lineup.fixture.fixture.event if lineup.fixture.fixture else '?'
        
        print(f"[{i}/{stats['qualifying']}] {player_name} - GW{gw}")
        print(f"  Criteria met: {', '.join(reasons)}")
        
        # Check if already exists
        existing = SofasportHeatmap.objects.filter(
            athlete=lineup.athlete,
            fixture=lineup.fixture
        ).exists()
        
        if existing:
            print(f"  ⏭️  Already exists - skipping")
            stats['skipped_exists'] += 1
            continue
        
        # Fetch from API
        try:
            response = client.get_player_heatmap(
                str(lineup.sofasport_player_id),
                str(lineup.fixture.sofasport_event_id)
            )
            
            if not response or 'data' not in response:
                print(f"  ⚠️  No data returned from API")
                stats['skipped_no_data'] += 1
                continue
            
            coordinates = response['data']
            
            if not isinstance(coordinates, list):
                print(f"  ⚠️  Invalid coordinate format")
                stats['skipped_no_data'] += 1
                continue
            
            point_count = len(coordinates)
            
            # Create heatmap record
            SofasportHeatmap.objects.create(
                sofasport_player_id=lineup.sofasport_player_id,
                athlete=lineup.athlete,
                fixture=lineup.fixture,
                lineup=lineup,
                coordinates=coordinates,
                point_count=point_count
            )
            
            print(f"  ✅ Collected {point_count} coordinate points")
            stats['collected'] += 1
        
        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg:
                print(f"  ⚠️  404 - No heatmap data available")
                stats['skipped_no_data'] += 1
            else:
                print(f"  ❌ Error: {error_msg}")
                stats['errors'] += 1
            continue
    
    return stats


def display_summary(stats: Dict):
    """Display summary statistics."""
    print(f"\n{'='*70}")
    print("HEATMAP COLLECTION ETL - SUMMARY")
    print(f"{'='*70}")
    print(f"📊 Total Lineups:         {stats['total_lineups']}")
    print(f"✅ Qualifying Players:    {stats['qualifying']} ({stats['qualifying']/stats['total_lineups']*100:.1f}%)")
    print(f"⏭️  Non-Qualifying:        {stats['skipped_not_qualifying']}")
    print(f"")
    print(f"🎯 Collection Results:")
    print(f"   ✅ Collected:          {stats['collected']}")
    print(f"   ⏭️  Already Exists:     {stats['skipped_exists']}")
    print(f"   ⚠️  No Data Available:  {stats['skipped_no_data']}")
    print(f"   ❌ Errors:             {stats['errors']}")
    print(f"")
    total_processed = stats['collected'] + stats['skipped_exists']
    print(f"📈 Total Heatmaps (DB):   {total_processed}")
    print(f"{'='*70}")
    
    # Show some examples
    print("\n📍 Sample Heatmap Data (Top 10 by Point Count):")
    print(f"{'='*70}")
    
    top_heatmaps = SofasportHeatmap.objects.select_related(
        'athlete', 'fixture__fixture'
    ).order_by('-point_count')[:10]
    
    for i, heatmap in enumerate(top_heatmaps, 1):
        gw = heatmap.fixture.fixture.event if heatmap.fixture.fixture else '?'
        print(f"{i}. {heatmap.athlete.web_name} - GW{gw}: {heatmap.point_count} points")
    
    # Show coverage by gameweek
    print(f"\n📅 Coverage by Gameweek:")
    print(f"{'='*70}")
    
    from django.db.models import Count
    from etl.models import SofasportFixture
    
    coverage = SofasportHeatmap.objects.values(
        'fixture__fixture__event'
    ).annotate(
        count=Count('id')
    ).order_by('fixture__fixture__event')
    
    for gw_data in coverage:
        gw = gw_data['fixture__fixture__event']
        count = gw_data['count']
        print(f"   GW{gw}: {count} heatmaps")


def display_criteria_breakdown():
    """Show which criteria were most effective."""
    print(f"\n📊 Criteria Effectiveness Analysis:")
    print(f"{'='*70}")
    
    lineups = SofasportLineup.objects.select_related('athlete')
    
    criteria_counts = {
        'minutes_60': 0,
        'rating_7': 0,
        'goal_contributor': 0,
        'fpl_30pts': 0,
        'started': 0
    }
    
    for lineup in lineups:
        stats = lineup.statistics or {}
        
        if (stats.get('minutesPlayed', 0) or 0) >= 60:
            criteria_counts['minutes_60'] += 1
        
        if float(stats.get('rating', 0) or 0) >= 7.0:
            criteria_counts['rating_7'] += 1
        
        goals = stats.get('goals', 0) or 0
        assists = stats.get('goalAssist', 0) or 0
        if (goals + assists) >= 1:
            criteria_counts['goal_contributor'] += 1
        
        if lineup.athlete and lineup.athlete.total_points >= 30:
            criteria_counts['fpl_30pts'] += 1
        
        if not lineup.substitute:
            criteria_counts['started'] += 1
    
    print(f"1. Minutes ≥60:       {criteria_counts['minutes_60']} lineups")
    print(f"2. Rating ≥7.0:       {criteria_counts['rating_7']} lineups")
    print(f"3. Goals+Assists ≥1:  {criteria_counts['goal_contributor']} lineups")
    print(f"4. FPL Points ≥30:    {criteria_counts['fpl_30pts']} lineups")
    print(f"5. Started Match:     {criteria_counts['started']} lineups")
    print(f"{'='*70}")


if __name__ == "__main__":
    print("🗺️  Starting Player Heatmap Collection ETL...")
    
    # Show criteria breakdown first
    display_criteria_breakdown()
    
    # Initialize client
    client = SofaSportClient()
    
    # Process heatmaps
    stats = process_heatmaps(client)
    
    # Display summary
    display_summary(stats)
    
    print("\n✅ Heatmap Collection ETL completed!")
