#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting build process..."

# Navigate to Django directory
cd django_etl

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn supervisor

echo "🗄️  Running database migrations..."
python manage.py migrate --noinput

echo "📊 Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "✅ Build completed successfully!"
