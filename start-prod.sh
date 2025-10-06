#!/usr/bin/env bash
# Production start script for Render

echo "🚀 Starting FPL Pulse production services..."

# Navigate to Django directory
cd django_etl

# Start supervisord with all services (Django, Celery Worker, Celery Beat)
exec supervisord -n -c ../supervisord.conf
