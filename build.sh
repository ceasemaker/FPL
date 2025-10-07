#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting build process..."

# Ensure we're using the right Python and pip
echo "🐍 Python version: $(python --version)"
echo "� Python location: $(which python)"
echo "📍 Pip location: $(which pip)"

echo "�📦 Installing Python dependencies..."
python -m pip install --upgrade pip

# Install from django_etl requirements
echo "📦 Installing from requirements.txt..."
python -m pip install -r django_etl/requirements.txt

# Ensure critical packages are installed explicitly
echo "📦 Installing critical packages explicitly..."
python -m pip install gunicorn supervisor celery[redis] redis whitenoise django-cors-headers psycopg2-binary

echo "📋 Verifying installed packages:"
python -m pip list | grep -E "(celery|redis|whitenoise|gunicorn|supervisor|django-cors|psycopg2)"

# Navigate to Django directory for management commands
cd django_etl

echo "🗄️  Running database migrations..."
python manage.py migrate --noinput

echo "📊 Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "✅ Build completed successfully!"
