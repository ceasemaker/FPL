"""
Check which FPL players are not mapped to SofaSport
"""
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Add Django to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
django_path = project_root / 'django_etl'
sys.path.insert(0, str(django_path))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fpl_platform.settings')

import django
django.setup()

from etl.models import Athlete

# Load player mapping
mapping_path = Path(__file__).parent.parent / 'mappings' / 'player_mapping.json'
with open(mapping_path, 'r') as f:
    player_mapping = json.load(f)

# Get mapped FPL player IDs
mapped_fpl_ids = {p['fpl_id'] for p in player_mapping.values()}

# Get all FPL players
all_players = Athlete.objects.all().select_related('team')
total_players = all_players.count()

print(f'📊 FPL Database Stats:')
print(f'   Total FPL players: {total_players}')
print(f'   Mapped to SofaSport: {len(mapped_fpl_ids)}')
print(f'   Unmapped: {total_players - len(mapped_fpl_ids)}')
print()

# Group unmapped by team
unmapped_by_team = {}
for player in all_players:
    if player.id not in mapped_fpl_ids:
        team_name = player.team.short_name if player.team else 'Unknown'
        if team_name not in unmapped_by_team:
            unmapped_by_team[team_name] = []
        full_name = f"{player.first_name} {player.second_name}".strip()
        unmapped_by_team[team_name].append({
            'web_name': player.web_name,
            'full_name': full_name,
            'total_points': player.total_points or 0
        })

print(f'⚠️  Unmapped players by team (sorted by total points):')
for team in sorted(unmapped_by_team.keys()):
    players = sorted(unmapped_by_team[team], key=lambda x: x['total_points'], reverse=True)
    print(f'\n   {team} ({len(players)} unmapped):')
    for p in players[:10]:  # Show top 10
        print(f"      {p['web_name']:20} ({p['full_name']:35}) - {p['total_points']} pts")
    if len(players) > 10:
        print(f"      ... and {len(players) - 10} more")

# Summary by points
unmapped_with_points = []
for team_players in unmapped_by_team.values():
    for p in team_players:
        if p['total_points'] > 0:
            unmapped_with_points.append(p)

print(f'\n⚠️  CRITICAL: {len(unmapped_with_points)} unmapped players have FPL points!')
if unmapped_with_points:
    top_unmapped = sorted(unmapped_with_points, key=lambda x: x['total_points'], reverse=True)[:20]
    print(f'\nTop 20 unmapped players by points:')
    for i, p in enumerate(top_unmapped, 1):
        print(f"   {i:2}. {p['web_name']:20} ({p['full_name']:35}) - {p['total_points']} pts")
