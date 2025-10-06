"""
Show best match candidates for unmapped FPL players with points
"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from fuzzywuzzy import fuzz
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))
from api_client import SofaSportClient

# Add Django to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
django_path = project_root / 'django_etl'
sys.path.insert(0, str(django_path))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fpl_platform.settings')

import django
django.setup()

from etl.models import Athlete

def fuzzy_match_player_detailed(
    fpl_player: Dict,
    sofa_players: List[Dict],
    threshold: int = 50
) -> List[Tuple[Dict, int]]:
    """
    Find all matches above threshold with scores.
    
    Returns:
        List of (sofa_player, score) tuples sorted by score descending
    """
    fpl_full = fpl_player['full_name']
    fpl_web = fpl_player['web_name']
    fpl_first = fpl_player.get('first_name', '')
    fpl_second = fpl_player.get('second_name', '')
    
    matches = []
    
    for sofa_player in sofa_players:
        sofa_name = sofa_player['name']
        sofa_short = sofa_player.get('short_name', '')
        
        # Calculate various match scores
        scores = [
            fuzz.ratio(sofa_name.lower(), fpl_full.lower()),
            fuzz.partial_ratio(sofa_name.lower(), fpl_full.lower()),
            fuzz.token_sort_ratio(sofa_name.lower(), fpl_full.lower()),
        ]
        
        if sofa_short:
            scores.extend([
                fuzz.ratio(sofa_short.lower(), fpl_second.lower()),
                fuzz.ratio(sofa_short.lower(), fpl_web.lower()),
                fuzz.partial_ratio(sofa_short.lower(), fpl_full.lower()),
            ])
        
        max_score = max(scores)
        
        if max_score >= threshold:
            matches.append((sofa_player, max_score))
    
    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def main():
    # Load mappings
    mapping_path = Path(__file__).parent.parent / 'mappings'
    
    with open(mapping_path / 'player_mapping.json', 'r') as f:
        player_mapping = json.load(f)
    
    with open(mapping_path / 'team_mapping.json', 'r') as f:
        team_mapping = json.load(f)
    
    # Create reverse team mapping (fpl_id -> sofasport_id)
    fpl_to_sofa_teams = {}
    for sofa_id, info in team_mapping.items():
        fpl_to_sofa_teams[info['fpl_id']] = sofa_id
    
    # Get mapped FPL player IDs
    mapped_fpl_ids = {p['fpl_id'] for p in player_mapping.values()}
    
    # Get unmapped players with points
    unmapped_with_points = []
    all_players = Athlete.objects.all().select_related('team')
    
    for player in all_players:
        if player.id not in mapped_fpl_ids and (player.total_points or 0) > 0:
            unmapped_with_points.append({
                'id': player.id,
                'first_name': player.first_name,
                'second_name': player.second_name,
                'web_name': player.web_name,
                'full_name': f'{player.first_name} {player.second_name}'.strip(),
                'team': player.team.short_name if player.team else 'Unknown',
                'team_id': player.team.id if player.team else None,
                'points': player.total_points or 0
            })
    
    # Sort by points descending
    unmapped_with_points.sort(key=lambda x: x['points'], reverse=True)
    
    # Get SofaSport client
    client = SofaSportClient()
    
    print(f'\n🔍 Analyzing {len(unmapped_with_points)} Unmapped Players with Best Match Candidates')
    print('=' * 120)
    
    for i, fpl_player in enumerate(unmapped_with_points, 1):
        team_id = fpl_player['team_id']
        if team_id not in fpl_to_sofa_teams:
            print(f"\n{i:2}. [{fpl_player['team']:3}] {fpl_player['web_name']:20} ({fpl_player['full_name']:40}) - {fpl_player['points']} pts")
            print(f"    ❌ Team not in mapping")
            continue
        
        sofa_team_id = fpl_to_sofa_teams[team_id]
        
        # Get SofaSport squad for this team
        response = client.get_team_squad(sofa_team_id)
        sofa_players = []
        
        if response and 'data' in response:
            for player_data in response.get('data', {}).get('players', []):
                player = player_data.get('player', {})
                if player.get('id'):
                    sofa_players.append({
                        'id': str(player.get('id')),
                        'name': player.get('name', ''),
                        'short_name': player.get('shortName', '')
                    })
        
        # Find matches
        matches = fuzzy_match_player_detailed(fpl_player, sofa_players, threshold=50)
        
        print(f"\n{i:2}. [{fpl_player['team']:3}] {fpl_player['web_name']:20} ({fpl_player['full_name']:40}) - {fpl_player['points']} pts")
        print(f"    FPL ID: {fpl_player['id']}, SofaSport Team ID: {sofa_team_id}")
        
        if matches:
            print(f"    Best matches (threshold >= 50):")
            for j, (sofa_player, score) in enumerate(matches[:5], 1):
                status = "✅" if score >= 90 else "⚠️ " if score >= 75 else "❓"
                print(f"      {status} {score:3} | {sofa_player['name']:45} (ID: {sofa_player['id']:10}) | Short: {sofa_player['short_name']}")
        else:
            print(f"    ❌ No matches found (all scores < 50)")


if __name__ == "__main__":
    main()
