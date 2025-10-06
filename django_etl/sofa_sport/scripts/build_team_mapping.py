"""
Team Mapping Builder

Creates a JSON mapping between SofaSport team IDs and FPL team IDs.
Uses fuzzy matching to match team names.
"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
from fuzzywuzzy import fuzz
from dotenv import load_dotenv

# Load environment variables from sofa_sport/.env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Add parent directory to path to import api_client
sys.path.append(str(Path(__file__).parent))
from api_client import SofaSportClient

# Add Django project to path - need both parent and django_etl itself
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))  # For django_etl module
django_path = project_root / 'django_etl'
sys.path.insert(0, str(django_path))  # For fpl_platform.settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fpl_platform.settings')

import django
django.setup()

from etl.models import Team


def get_fpl_teams() -> Dict[int, str]:
    """Get all FPL teams as {id: name} dict."""
    teams = Team.objects.all()
    return {team.id: team.name for team in teams}


def get_sofasport_teams(client: SofaSportClient) -> List[Dict[str, any]]:
    """Get all SofaSport teams."""
    response = client.get_teams_statistics()
    
    if not response or 'data' not in response:
        print("❌ Failed to fetch SofaSport teams")
        return []
    
    teams = []
    # Extract teams from avgRating data
    if 'avgRating' in response['data']:
        for item in response['data']['avgRating']:
            if 'team' in item:
                teams.append({
                    'id': item['team']['id'],
                    'name': item['team']['name']
                })
    
    return teams


def fuzzy_match_team(sofa_name: str, fpl_teams: Dict[int, str], threshold: int = 80) -> Tuple[int, str, int]:
    """
    Fuzzy match SofaSport team name to FPL team.
    
    Returns:
        (fpl_id, fpl_name, match_score)
    """
    best_match = (None, None, 0)
    
    for fpl_id, fpl_name in fpl_teams.items():
        # Try different matching strategies
        scores = [
            fuzz.ratio(sofa_name.lower(), fpl_name.lower()),
            fuzz.partial_ratio(sofa_name.lower(), fpl_name.lower()),
            fuzz.token_sort_ratio(sofa_name.lower(), fpl_name.lower())
        ]
        score = max(scores)
        
        if score > best_match[2]:
            best_match = (fpl_id, fpl_name, score)
    
    return best_match


def build_team_mapping() -> Dict[str, Dict[str, any]]:
    """Build complete team mapping."""
    print("🏟️  Building Team Mapping...")
    print("=" * 60)
    
    client = SofaSportClient()
    
    # Get teams from both sources
    fpl_teams = get_fpl_teams()
    sofa_teams = get_sofasport_teams(client)
    
    print(f"✅ Found {len(fpl_teams)} FPL teams")
    print(f"✅ Found {len(sofa_teams)} SofaSport teams")
    print()
    
    # Build mapping
    mapping = {}
    unmatched = []
    
    for sofa_team in sofa_teams:
        sofa_id = str(sofa_team['id'])
        sofa_name = sofa_team['name']
        
        fpl_id, fpl_name, score = fuzzy_match_team(sofa_name, fpl_teams)
        
        if score >= 80:
            mapping[sofa_id] = {
                "sofasport_id": sofa_id,
                "sofasport_name": sofa_name,
                "fpl_id": fpl_id,
                "fpl_name": fpl_name,
                "match_score": score
            }
            status = "✅" if score >= 95 else "⚠️ "
            print(f"{status} {sofa_name:25} → {fpl_name:25} (score: {score})")
        else:
            unmatched.append((sofa_name, fpl_name, score))
            print(f"❌ {sofa_name:25} → {fpl_name:25} (score: {score}) - NEEDS MANUAL REVIEW")
    
    print()
    print("=" * 60)
    print(f"✅ Successfully mapped: {len(mapping)}/{len(sofa_teams)} teams")
    
    if unmatched:
        print(f"⚠️  Unmatched teams: {len(unmatched)}")
        print("\nPlease review these manually:")
        for sofa_name, best_fpl, score in unmatched:
            print(f"  - {sofa_name} (best match: {best_fpl}, score: {score})")
    
    return mapping


def save_mapping(mapping: Dict, filename: str = "team_mapping.json"):
    """Save mapping to JSON file."""
    output_path = Path(__file__).parent.parent / 'mappings' / filename
    
    with open(output_path, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"\n💾 Mapping saved to: {output_path}")


if __name__ == "__main__":
    try:
        mapping = build_team_mapping()
        save_mapping(mapping)
        print("\n✅ Team mapping complete!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
