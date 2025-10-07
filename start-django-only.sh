#!/usr/bin/env bash
# Alternative start script without supervisord
# Use this if you prefer not to run Celery in the same service

set -o errexit

echo "🚀 Starting Django with Gunicorn..."

cd django_etl

# Start gunicorn
exec gunicorn fpl_platform.wsgi:application \
  --bind 0.0.0.0:${PORT:-10000} \
  --workers 2 \
  --timeout 120 \
  --log-file - \
  --access-logfile - \
  --error-logfile - \
  --log-level info
