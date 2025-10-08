"""
Management command to manually trigger SofaSport data loading.

Usage:
    python manage.py load_sofasport_data
    python manage.py load_sofasport_data --task=heatmaps
    python manage.py load_sofasport_data --task=all
"""
from django.core.management.base import BaseCommand, CommandError
from etl.tasks import (
    update_fixture_mappings,
    update_lineups,
    collect_heatmaps,
    update_season_stats,
    update_radar_attributes,
)


class Command(BaseCommand):
    help = 'Manually trigger SofaSport data loading tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            default='all',
            choices=['all', 'fixtures', 'lineups', 'heatmaps', 'season_stats', 'radar'],
            help='Which task to run (default: all)',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run tasks asynchronously via Celery (requires Celery worker)',
        )

    def handle(self, *args, **options):
        task_name = options['task']
        use_async = options['async']
        
        tasks_to_run = []
        
        if task_name == 'all':
            tasks_to_run = [
                ('Fixture Mappings', update_fixture_mappings),
                ('Lineups & Stats', update_lineups),
                ('Heatmaps', collect_heatmaps),
                ('Season Statistics', update_season_stats),
                ('Radar Attributes', update_radar_attributes),
            ]
        elif task_name == 'fixtures':
            tasks_to_run = [('Fixture Mappings', update_fixture_mappings)]
        elif task_name == 'lineups':
            tasks_to_run = [('Lineups & Stats', update_lineups)]
        elif task_name == 'heatmaps':
            tasks_to_run = [('Heatmaps', collect_heatmaps)]
        elif task_name == 'season_stats':
            tasks_to_run = [('Season Statistics', update_season_stats)]
        elif task_name == 'radar':
            tasks_to_run = [('Radar Attributes', update_radar_attributes)]
        
        self.stdout.write(self.style.SUCCESS(
            f'\n🚀 Starting SofaSport data load: {task_name}\n'
        ))
        
        for task_label, task_func in tasks_to_run:
            self.stdout.write(f'\n📊 Running: {task_label}...')
            
            try:
                if use_async:
                    # Queue task in Celery
                    result = task_func.delay()
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ Queued (Task ID: {result.id})'
                    ))
                else:
                    # Run synchronously (blocks until complete)
                    result = task_func()
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ Completed: {result}'
                    ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'   ❌ Failed: {str(e)}'
                ))
                if task_name != 'all':
                    raise CommandError(f'Task failed: {str(e)}')
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✨ SofaSport data load complete!\n'
        ))
