# FPL Pulse - Celery Automated Scheduling

Automated task scheduling for weekly SofaSport data updates using Celery Beat.

## 🚀 Overview

This setup automates the collection and processing of SofaSport data on a weekly schedule:

- **Monday 2:00 AM**: Update fixture mappings after gameweek ends
- **Tuesday 3:00 AM**: Collect lineups and stats after all matches complete
- **Tuesday 4:00 AM**: Collect player heatmaps (runs after lineups)
- **Wednesday 2:00 AM**: Update season statistics
- **Wednesday 3:00 AM**: Update radar chart attributes

## 📦 Components

### 1. Celery Configuration (`fpl_platform/celery.py`)
- Celery app configuration
- Beat schedule with cron jobs
- Task serialization settings
- Timezone: Europe/London (matches Premier League schedule)

### 2. Celery Tasks (`etl/tasks.py`)
- `update_fixture_mappings` - Syncs FPL/SofaSport fixtures
- `update_lineups` - Collects player lineups
- `collect_heatmaps` - Gathers movement heatmaps
- `update_season_stats` - Updates aggregated season stats
- `update_radar_attributes` - Updates player attributes for radar charts
- `run_manual_update` - Manually trigger any ETL script

### 3. Docker Services (docker-compose.yml)
- **celery-worker**: Processes async tasks
- **celery-beat**: Scheduler daemon (triggers tasks on schedule)
- **redis**: Message broker and result backend
- **postgres**: Data storage

## 🛠️ Setup

### Prerequisites
- Docker and Docker Compose installed
- Redis running (included in docker-compose.yml)
- PostgreSQL database configured

### Installation

1. **Install Celery dependencies:**
```bash
cd django_etl
pip install -r requirements.txt
```

2. **Update environment variables in `local.env`:**
```bash
# Redis Configuration (Celery broker)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=  # Optional
REDIS_DB=0

# Django settings
DJANGO_SETTINGS_MODULE=fpl_platform.settings
```

3. **Start services with Docker Compose:**
```bash
# Start all services (includes Celery worker and beat)
docker-compose up -d

# Check Celery worker status
docker logs fpl_celery_worker

# Check Celery beat status
docker logs fpl_celery_beat
```

4. **Verify Celery is running:**
```bash
# Check worker health
docker exec fpl_celery_worker celery -A fpl_platform inspect active

# Check scheduled tasks
docker exec fpl_celery_beat celery -A fpl_platform inspect scheduled
```

## 📅 Task Schedule

| Task | Time | Day | Description |
|------|------|-----|-------------|
| `update_fixture_mappings` | 2:00 AM | Monday | Sync FPL/SofaSport fixture IDs |
| `update_lineups` | 3:00 AM | Tuesday | Collect player lineups from recent matches |
| `collect_heatmaps` | 4:00 AM | Tuesday | Gather heatmap data (runs after lineups) |
| `update_season_stats` | 2:00 AM | Wednesday | Aggregate season statistics |
| `update_radar_attributes` | 3:00 AM | Wednesday | Update radar chart attributes |

**Timezone:** Europe/London (BST/GMT)

**Rationale:**
- Monday: Weekend matches complete, fixture data ready
- Tuesday: Match data fully processed, lineups/heatmaps available
- Wednesday: Weekly stats finalized, radar attributes calculated

## 🔧 Manual Task Execution

### From Django Shell
```bash
docker exec -it fpl_celery_worker python manage.py shell
```

```python
from etl.tasks import update_fixture_mappings, update_lineups, collect_heatmaps

# Run a specific task manually
result = update_fixture_mappings.delay()
print(result.get())  # Wait for result

# Run multiple tasks
tasks = [
    update_fixture_mappings.delay(),
    update_lineups.delay(),
    collect_heatmaps.delay(),
]
for task in tasks:
    print(task.get())
```

### From Command Line
```bash
# Trigger a task immediately
docker exec fpl_celery_worker celery -A fpl_platform call etl.tasks.update_fixture_mappings

# Run manual update with custom script
docker exec fpl_celery_worker celery -A fpl_platform call etl.tasks.run_manual_update --args='["build_fixture_mapping.py"]'
```

## 📊 Monitoring

### Check Task Status
```bash
# View active tasks
docker exec fpl_celery_worker celery -A fpl_platform inspect active

# View registered tasks
docker exec fpl_celery_worker celery -A fpl_platform inspect registered

# View scheduled tasks
docker exec fpl_celery_beat celery -A fpl_platform inspect scheduled

# Check task statistics
docker exec fpl_celery_worker celery -A fpl_platform inspect stats
```

### View Logs
```bash
# Celery worker logs
docker logs -f fpl_celery_worker

# Celery beat (scheduler) logs
docker logs -f fpl_celery_beat

# Filter for specific task
docker logs fpl_celery_worker 2>&1 | grep "update_fixture_mappings"
```

### Django Admin Monitoring
Use Django Admin to view task results if you install `django-celery-results`:
```bash
pip install django-celery-results
python manage.py migrate django_celery_results
```

## 🐛 Troubleshooting

### Tasks Not Running
1. Check Celery worker is running:
```bash
docker ps | grep celery
```

2. Check Redis connection:
```bash
docker exec fpl_celery_worker celery -A fpl_platform inspect ping
```

3. Verify task registration:
```bash
docker exec fpl_celery_worker celery -A fpl_platform inspect registered
```

### Task Failures
1. Check worker logs:
```bash
docker logs fpl_celery_worker --tail 100
```

2. Run task manually to see detailed error:
```bash
docker exec -it fpl_celery_worker python manage.py shell
>>> from etl.tasks import update_fixture_mappings
>>> result = update_fixture_mappings()
>>> print(result)
```

### Redis Connection Issues
1. Check Redis is running:
```bash
docker exec fpl_redis redis-cli ping
```

2. Test connection from Django:
```bash
docker exec fpl_celery_worker python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value', 60)
>>> cache.get('test')
```

## 🔄 Updating the Schedule

Edit `fpl_platform/celery.py` to modify the schedule:

```python
app.conf.beat_schedule = {
    'update-fixture-mappings': {
        'task': 'etl.tasks.update_fixture_mappings',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # Monday 2 AM
    },
    # Add or modify tasks here
}
```

**Crontab Format:**
- `hour`: 0-23
- `minute`: 0-59
- `day_of_week`: 0-6 (0=Sunday, 1=Monday, etc.)
- `day_of_month`: 1-31
- `month_of_year`: 1-12

**Restart Celery Beat after changes:**
```bash
docker-compose restart celery-beat
```

## 📁 File Structure

```
django_etl/
├── fpl_platform/
│   ├── __init__.py        # Loads Celery on Django startup
│   ├── celery.py          # Celery configuration & schedule
│   └── settings.py        # Django settings (includes CELERY_* config)
├── etl/
│   ├── tasks.py           # Celery task definitions
│   └── api_views.py       # API endpoints (includes SofaSport data)
└── sofasport_etl/         # ETL scripts
    ├── build_fixture_mapping.py
    ├── build_lineups_etl.py
    ├── build_heatmap_etl.py
    ├── build_season_stats_etl.py
    └── build_radar_attributes_etl.py
```

## 🎯 Task Timeouts

Each task has specific timeout limits:

- `update_fixture_mappings`: 10 minutes
- `update_lineups`: 15 minutes
- `collect_heatmaps`: 30 minutes (largest dataset)
- `update_season_stats`: 20 minutes
- `update_radar_attributes`: 15 minutes
- `run_manual_update`: 1 hour

If a task exceeds its timeout, it will be terminated and logged as an error.

## 🔐 Security Notes

- Celery runs with `C_FORCE_ROOT=true` in Docker (not recommended for production with untrusted code)
- Redis has no authentication in local dev setup
- For production:
  - Enable Redis password authentication
  - Use TLS for Redis connections
  - Implement task result expiration
  - Add task rate limiting

## 📚 Additional Resources

- [Celery Documentation](https://docs.celeryq.dev/)
- [Celery Beat Scheduler](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html)
- [Django + Celery Integration](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
- [Redis Documentation](https://redis.io/docs/)

## 🆘 Support

If tasks are failing:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review worker logs: `docker logs fpl_celery_worker`
3. Run tasks manually to debug
4. Verify ETL scripts run correctly outside Celery
5. Check Redis/PostgreSQL connectivity

---

**Last Updated:** January 2025  
**Celery Version:** 5.3+  
**Django Version:** 4.2+  
**Redis Version:** 7.x
