"""
Celery Configuration for FPL Platform

Automated task scheduling for weekly SofaSport data updates.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fpl_platform.settings')

app = Celery('fpl_platform')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat Schedule (Weekly Updates)
app.conf.beat_schedule = {
    # Monday 2:00 AM - Update fixture mappings after gameweek ends
    'update-fixture-mappings': {
        'task': 'etl.tasks.update_fixture_mappings',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # Monday 2 AM
    },
    
    # Tuesday 3:00 AM - Update lineups and stats after all matches complete
    'update-lineups': {
        'task': 'etl.tasks.update_lineups',
        'schedule': crontab(hour=3, minute=0, day_of_week=2),  # Tuesday 3 AM
    },
    
    # OLD: Heatmaps collected separately on Tuesday
    # NEW: Heatmaps are now part of the Daily Pipeline
    # 'collect-heatmaps': {
    #    'task': 'etl.tasks.collect_heatmaps',
    #    'schedule': crontab(hour=4, minute=0, day_of_week=2),
    # },

    # Daily 3:30 AM - Run Daily FPL ETL Pipeline (Replaces Render Cron Job)
    # Runs after lineups (on Tue) and other weekly tasks
    'run-daily-pipeline': {
        'task': 'etl.tasks.run_daily_pipeline',
        'schedule': crontab(hour=3, minute=30),  # Daily 3:30 AM
    },
    
    # Wednesday 2:00 AM - Update season statistics
    'update-season-stats': {
        'task': 'etl.tasks.update_season_stats',
        'schedule': crontab(hour=2, minute=0, day_of_week=3),  # Wednesday 2 AM
    },
    
    # Wednesday 3:00 AM - Update radar attributes
    'update-radar-attributes': {
        'task': 'etl.tasks.update_radar_attributes',
        'schedule': crontab(hour=3, minute=0, day_of_week=3),  # Wednesday 3 AM
    },
    
    # Every 10 minutes - Sync fixture odds for upcoming matches
    'sync-fixture-odds': {
        'task': 'etl.tasks.sync_fixture_odds',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
        'kwargs': {'days_ahead': 7}  # Next 7 days of fixtures
    },

    # Every 30 minutes - Warm price predictor cache for frontend charts
    'warm-price-predictor-cache': {
        'task': 'etl.tasks.warm_price_predictor_cache',
        'schedule': crontab(minute='*/30'),
    },
}

# Celery Configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/London',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_max_tasks_per_child=50,
)

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')
