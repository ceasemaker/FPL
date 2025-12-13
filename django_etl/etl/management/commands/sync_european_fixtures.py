"""
Management command to sync European/Cup fixtures for Premier League teams.

Syncs matches from:
- UEFA Champions League (UCL)
- UEFA Europa League (UEL)
- UEFA Conference League (UECL)
- FA Cup (FAC)
- EFL Cup (EFL)

Usage:
    python manage.py sync_european_fixtures
    python manage.py sync_european_fixtures --competitions UCL UEL
    python manage.py sync_european_fixtures --no-lineups
"""
import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Sync European and Cup fixtures for Premier League teams from SofaSport'

    def add_arguments(self, parser):
        parser.add_argument(
            '--competitions', '-c',
            nargs='+',
            choices=['UCL', 'UEL', 'UECL', 'FAC', 'EFL'],
            help='Specific competitions to sync (default: all)',
        )
        parser.add_argument(
            '--no-lineups',
            action='store_true',
            help='Skip fetching player lineups',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting European/Cup fixtures sync...'))
        
        # Add sofa_sport scripts to path
        scripts_dir = Path(settings.BASE_DIR) / 'sofa_sport' / 'scripts'
        sys.path.insert(0, str(scripts_dir))
        
        try:
            # Import the ETL module
            from build_european_fixtures_etl import main as sync_european
            
            # Run the sync
            sync_european(
                competitions=options['competitions'],
                fetch_lineups=not options['no_lineups']
            )
            
            self.stdout.write(self.style.SUCCESS('✅ European/Cup fixtures sync completed!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            raise
