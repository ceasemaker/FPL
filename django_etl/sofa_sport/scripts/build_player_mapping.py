"""
Player Mapping Builder

Creates a JSON mapping between SofaSport player IDs and FPL player IDs.
Uses fuzzy matching on player names and team context.
"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
import time

# Load environment variables from sofa_sport/.env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Add parent directory to path
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

from etl.models import Athlete, Team


def load_team_mapping() -> Dict[str, Dict]:
    """Load team mapping from JSON file."""
    mapping_path = Path(__file__).parent.parent / 'mappings' / 'team_mapping.json'
    
    if not mapping_path.exists():
        raise FileNotFoundError(
            "team_mapping.json not found. Please run build_team_mapping.py first."
        )
    
    with open(mapping_path, 'r') as f:
        return json.load(f)


def get_fpl_players_by_team(team_id: int) -> List[Dict]:
    """Get all FPL players for a specific team."""
    players = Athlete.objects.filter(team_id=team_id).select_related('team')
    return [
        {
            'id': player.id,
            'first_name': player.first_name,
            'second_name': player.second_name,
            'web_name': player.web_name,
            'full_name': f"{player.first_name} {player.second_name}".strip(),
            'team_id': team_id
        }
        for player in players
    ]


def get_sofasport_players(client: SofaSportClient, team_id: str) -> List[Dict]:
    """Get all SofaSport players for a specific team using squad endpoint."""
    response = client.get_team_squad(team_id)
    
    if not response or 'data' not in response:
        return []
    
    players = []
    
    # The squad endpoint returns players array
    players_data = response.get('data', {}).get('players', [])
    
    for player_data in players_data:
        player = player_data.get('player', {})
        player_id = str(player.get('id', ''))
        
        if player_id:
            players.append({
                'id': player_id,
                'name': player.get('name', ''),
                'short_name': player.get('shortName', ''),
                'team_id': team_id
            })
    
    return players


def fuzzy_match_player(
    sofa_player: Dict, 
    fpl_players: List[Dict], 
    threshold: int = 75
) -> Tuple[Optional[int], Optional[str], Optional[str], int]:
    """
    Fuzzy match SofaSport player to FPL player.
    
    Returns:
        (fpl_id, fpl_web_name, fpl_full_name, match_score)
    """
    sofa_name = sofa_player['name']
    sofa_short = sofa_player.get('short_name', '')
    
    best_match = (None, None, None, 0)
    
    for fpl_player in fpl_players:
        # Prioritize full name matching
        fpl_full = fpl_player['full_name']
        fpl_web = fpl_player['web_name']
        fpl_second = fpl_player['second_name']
        
        # Calculate scores for different name combinations
        # Full name gets highest priority
        full_name_scores = [
            fuzz.ratio(sofa_name.lower(), fpl_full.lower()),
            fuzz.partial_ratio(sofa_name.lower(), fpl_full.lower()),
            fuzz.token_sort_ratio(sofa_name.lower(), fpl_full.lower())
        ]
        max_full_score = max(full_name_scores)
        
        # Also check short name if available
        max_score = max_full_score
        if sofa_short:
            short_scores = [
                fuzz.ratio(sofa_short.lower(), fpl_second.lower()),
                fuzz.ratio(sofa_short.lower(), fpl_web.lower()),
            ]
            max_score = max(max_score, max(short_scores))
        
        # Prefer full name matches - give them a boost
        if max_full_score >= 85:
            max_score = max(max_score, max_full_score + 5)
        
        if max_score > best_match[3]:
            best_match = (fpl_player['id'], fpl_player['web_name'], fpl_full, max_score)
    
    return best_match


def build_player_mapping() -> Dict[str, Dict]:
    """Build complete player mapping."""
    print("⚽ Building Player Mapping...")
    print("=" * 80)
    
    client = SofaSportClient()
    team_mapping = load_team_mapping()
    
    all_player_mapping = {}
    total_mapped = 0
    total_unmatched = 0
    
    # Process each team
    for sofa_team_id, team_info in team_mapping.items():
        fpl_team_id = team_info['fpl_id']
        team_name = team_info['fpl_name']
        
        print(f"\n🏟️  Processing {team_name}...")
        print("-" * 80)
        
        # Get players from both sources
        fpl_players = get_fpl_players_by_team(fpl_team_id)
        sofa_players = get_sofasport_players(client, sofa_team_id)
        
        print(f"   FPL Players: {len(fpl_players)}, SofaSport Players: {len(sofa_players)}")
        
        # Match players
        for sofa_player in sofa_players:
            sofa_id = sofa_player['id']
            sofa_name = sofa_player['name']
            
            fpl_id, fpl_web_name, fpl_full_name, score = fuzzy_match_player(sofa_player, fpl_players)
            
            if fpl_id and score >= 75:
                all_player_mapping[sofa_id] = {
                    "sofasport_id": sofa_id,
                    "sofasport_name": sofa_name,
                    "fpl_id": fpl_id,
                    "fpl_web_name": fpl_web_name,
                    "fpl_full_name": fpl_full_name,
                    "fpl_team_id": fpl_team_id,
                    "sofasport_team_id": sofa_team_id,
                    "match_score": score
                }
                total_mapped += 1
                status = "✅" if score >= 90 else "⚠️ "
                print(f"   {status} {sofa_name:35} → {fpl_full_name:35} (score: {score})")
            else:
                total_unmatched += 1
                best_name = fpl_full_name if fpl_full_name else "N/A"
                print(f"   ❌ {sofa_name:35} → No match (best: {best_name}, score: {score})")
        
        time.sleep(0.5)  # Rate limiting
    
    print("\n" + "=" * 80)
    print(f"✅ Successfully mapped: {total_mapped} players")
    print(f"⚠️  Unmatched: {total_unmatched} players")
    print(f"📊 Success rate: {total_mapped / (total_mapped + total_unmatched) * 100:.1f}%")
    
    return all_player_mapping


def save_mapping(mapping: Dict, filename: str = "player_mapping.json"):
    """Save mapping to JSON file."""
    output_path = Path(__file__).parent.parent / 'mappings' / filename
    
    with open(output_path, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"\n💾 Player mapping saved to: {output_path}")
    print(f"   Total players mapped: {len(mapping)}")


if __name__ == "__main__":
    try:
        mapping = build_player_mapping()
        save_mapping(mapping)
        print("\n✅ Player mapping complete!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
