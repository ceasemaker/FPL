"""
ETL Script: Fetch Player Attribute Overviews for Radar Charts

This script fetches player attribute ratings (attacking, technical, tactical, 
defending, creativity) from the SofaSport API for all mapped players.

These attributes are used to create radar chart visualizations showing player
strengths across multiple dimensions.

Process:
1. Load player_mapping.json to get all mapped SofaSport player IDs
2. For each player, call get_player_attribute_overviews(player_id)
3. Extract attributes:
   - First try attributeOverviews with yearShift=0 (current season)
   - If not found, use averageAttributeOverviews[0] (career average)
4. Store in SofasportPlayerAttributes table
5. Track success/failure statistics

API Response Structure:
{
  "data": {
    "playerAttributeOverviews": [
      {
        "attacking": 71,
        "technical": 64,
        "tactical": 46,
        "defending": 33,
        "creativity": 69,
        "position": "F",
        "yearShift": 0,
        "id": 62847
      },
      {
        "attacking": 67,
        "technical": 53,
        "tactical": 40,
        "defending": 27,
        "creativity": 61,
        "position": "F",
        "yearShift": 1,
        "id": 81296
      }
    ],
    "averageAttributeOverviews": [
      {
        "attacking": 52,
        "technical": 55,
        "tactical": 40,
        "defending": 42,
        "creativity": 51,
        "position": "M",
        "yearShift": 0,
        "id": 19811
      }
    ]
  }
}

Note: We use the FIRST element in playerAttributeOverviews (most recent season).
If not available, we fall back to averageAttributeOverviews (career average).
"""
import os
import sys
import json
import django
from pathlib import Path
from typing import Dict, Optional

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fpl_django.settings')
django.setup()

from api_client import SofaSportClient
from django.conf import settings
from etl.models import Athlete, SofasportPlayerAttributes

# Get mappings directory relative to Django project root
MAPPINGS_DIR = Path(settings.BASE_DIR) / 'sofa_sport' / 'mappings'


def load_player_mapping() -> Dict:
    """Load player mapping file."""
    mapping_path = MAPPINGS_DIR / 'player_mapping.json'
    with open(mapping_path, 'r') as f:
        return json.load(f)


def extract_attributes(api_response: Dict) -> Optional[Dict]:
    """
    Extract attribute data from API response.
    
    Priority:
    1. playerAttributeOverviews[0] (first element = most recent season, yearShift=0)
    2. averageAttributeOverviews[0] (career average as fallback)
    
    Returns:
        dict with attributes or None if no data
    """
    data = api_response.get('data', {})
    
    # Try playerAttributeOverviews first - get the FIRST element (most recent)
    player_attribute_overviews = data.get('playerAttributeOverviews', [])
    if player_attribute_overviews:
        # The first element is always the most recent (yearShift=0)
        overview = player_attribute_overviews[0]
        return {
            'attacking': overview.get('attacking'),
            'technical': overview.get('technical'),
            'tactical': overview.get('tactical'),
            'defending': overview.get('defending'),
            'creativity': overview.get('creativity'),
            'position': overview.get('position'),
            'year_shift': overview.get('yearShift', 0),
            'is_average': False,
            'raw_data': api_response
        }
    
    # Fallback to averageAttributeOverviews (career average)
    avg_overviews = data.get('averageAttributeOverviews', [])
    if avg_overviews:
        overview = avg_overviews[0]
        return {
            'attacking': overview.get('attacking'),
            'technical': overview.get('technical'),
            'tactical': overview.get('tactical'),
            'defending': overview.get('defending'),
            'creativity': overview.get('creativity'),
            'position': overview.get('position'),
            'year_shift': overview.get('yearShift', 0),
            'is_average': True,
            'raw_data': api_response
        }
    
    return None


def process_player_attributes(client: SofaSportClient) -> Dict:
    """
    Process all mapped players to fetch and store attribute data.
    
    Returns:
        dict with statistics: created, updated, skipped, errors
    """
    player_mapping = load_player_mapping()
    
    stats = {
        'created': 0,
        'updated': 0,
        'skipped_no_data': 0,
        'skipped_unmapped': 0,
        'errors': 0
    }
    
    total_players = len(player_mapping)
    print(f"\n{'='*70}")
    print(f"Processing {total_players} mapped players for attribute data...")
    print(f"{'='*70}\n")
    
    for i, (sofasport_id, player_data) in enumerate(player_mapping.items(), 1):
        player_name = player_data.get('sofasport_name', 'Unknown')
        fpl_id = player_data.get('fpl_id')
        
        print(f"[{i}/{total_players}] {player_name} (SofaSport ID: {sofasport_id})")
        
        # Skip if no FPL mapping
        if not fpl_id:
            print(f"  ⚠️  No FPL mapping - skipping")
            stats['skipped_unmapped'] += 1
            continue
        
        # Get athlete
        try:
            athlete = Athlete.objects.get(id=fpl_id)
        except Athlete.DoesNotExist:
            print(f"  ❌ FPL athlete {fpl_id} not found in database")
            stats['errors'] += 1
            continue
        
        # Fetch from API
        try:
            response = client.get_player_attribute_overviews(sofasport_id)
            
            if not response or 'data' not in response:
                print(f"  ⚠️  No data returned from API")
                stats['skipped_no_data'] += 1
                continue
            
            # Extract attributes
            attributes_data = extract_attributes(response)
            
            if not attributes_data:
                print(f"  ⚠️  No valid attributes found in response")
                stats['skipped_no_data'] += 1
                continue
            
            # Check if already exists
            year_shift = attributes_data['year_shift']
            is_average = attributes_data['is_average']
            
            existing = SofasportPlayerAttributes.objects.filter(
                athlete=athlete,
                year_shift=year_shift,
                is_average=is_average
            ).first()
            
            if existing:
                # Update existing record
                for key, value in attributes_data.items():
                    setattr(existing, key, value)
                existing.sofasport_player_id = int(sofasport_id)
                existing.save()
                
                print(f"  ✅ Updated - Pos: {attributes_data['position']}, "
                      f"ATT: {attributes_data['attacking']}, "
                      f"TEC: {attributes_data['technical']}, "
                      f"TAC: {attributes_data['tactical']}, "
                      f"DEF: {attributes_data['defending']}, "
                      f"CRE: {attributes_data['creativity']}")
                if is_average:
                    print(f"     (Career Average)")
                
                stats['updated'] += 1
            else:
                # Create new record
                SofasportPlayerAttributes.objects.create(
                    sofasport_player_id=int(sofasport_id),
                    athlete=athlete,
                    **attributes_data
                )
                
                print(f"  ✅ Created - Pos: {attributes_data['position']}, "
                      f"ATT: {attributes_data['attacking']}, "
                      f"TEC: {attributes_data['technical']}, "
                      f"TAC: {attributes_data['tactical']}, "
                      f"DEF: {attributes_data['defending']}, "
                      f"CRE: {attributes_data['creativity']}")
                if is_average:
                    print(f"     (Career Average)")
                
                stats['created'] += 1
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            stats['errors'] += 1
            continue
    
    return stats


def display_summary(stats: Dict):
    """Display summary statistics."""
    total_processed = stats['created'] + stats['updated']
    total_skipped = stats['skipped_no_data'] + stats['skipped_unmapped']
    
    print(f"\n{'='*70}")
    print("RADAR CHART ATTRIBUTES ETL - SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Created:           {stats['created']}")
    print(f"🔄 Updated:           {stats['updated']}")
    print(f"📊 Total Processed:   {total_processed}")
    print(f"⚠️  Skipped (No Data): {stats['skipped_no_data']}")
    print(f"⚠️  Skipped (Unmapped):{stats['skipped_unmapped']}")
    print(f"❌ Errors:            {stats['errors']}")
    print(f"{'='*70}")
    
    # Show some examples
    print("\n📈 Sample Attribute Data (Top 10 by Attacking):")
    print(f"{'='*70}")
    
    top_attackers = SofasportPlayerAttributes.objects.filter(
        is_average=False
    ).order_by('-attacking')[:10]
    
    for i, attr in enumerate(top_attackers, 1):
        print(f"{i}. {attr.athlete.web_name} ({attr.position})")
        print(f"   ATT: {attr.attacking}, TEC: {attr.technical}, "
              f"TAC: {attr.tactical}, DEF: {attr.defending}, CRE: {attr.creativity}")


if __name__ == "__main__":
    print("Starting Radar Chart Attributes ETL...")
    
    # Initialize client
    client = SofaSportClient()
    
    # Process all players
    stats = process_player_attributes(client)
    
    # Display summary
    display_summary(stats)
    
    print("\n✅ Radar Chart Attributes ETL completed!")
