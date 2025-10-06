#!/usr/bin/env bash
# Production start script for Render

echo "🚀 Starting FPL Pulse production services..."

# Start supervisord with all services (Django, Celery Worker, Celery Beat)
# supervisord.conf is in root, but programs will run from django_etl directory
exec supervisord -n -c ./supervisord.conf
