#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting build process..."

echo "📦 Installing Python dependencies..."
pip install --upgrade pip

# Install from django_etl requirements
pip install -r django_etl/requirements.txt

# Ensure critical packages are installed explicitly
pip install gunicorn supervisor celery redis whitenoise django-cors-headers

echo "📋 Installed packages:"
pip list | grep -E "(celery|redis|whitenoise|gunicorn|supervisor|django-cors)"

# Navigate to Django directory for management commands
cd django_etl

echo "🗄️  Running database migrations..."
python manage.py migrate --noinput

echo "📊 Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "✅ Build completed successfully!"
