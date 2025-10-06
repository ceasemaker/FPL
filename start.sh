#!/bin/bash

# FPL Pulse - Quick Start Script
# This script helps you start the application and test the new features

set -e

echo "🚀 FPL Pulse - Quick Start"
echo "=============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

print_success "Docker is running"
echo ""

# Step 1: Build and start services
print_info "Step 1: Building and starting services..."
docker-compose down
docker-compose build
docker-compose up -d

echo ""
print_info "Waiting for services to start..."
sleep 10

# Step 2: Check service health
print_info "Step 2: Checking service health..."
echo ""

# Check Postgres
if docker exec fpl_postgres pg_isready -U postgres > /dev/null 2>&1; then
    print_success "PostgreSQL is ready"
else
    print_warning "PostgreSQL might not be ready yet"
fi

# Check Redis
if docker exec fpl_redis redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is ready"
else
    print_warning "Redis might not be ready yet"
fi

# Check Django
if curl -s http://localhost:8000/api/landing/ > /dev/null 2>&1; then
    print_success "Django web server is ready"
else
    print_warning "Django web server might not be ready yet (might take a few more seconds)"
fi

# Check Frontend
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    print_success "Frontend is ready"
else
    print_warning "Frontend might not be ready yet (might take a few more seconds)"
fi

# Check Celery Worker
if docker ps | grep -q fpl_celery_worker; then
    print_success "Celery worker is running"
else
    print_warning "Celery worker might not be running"
fi

# Check Celery Beat
if docker ps | grep -q fpl_celery_beat; then
    print_success "Celery beat scheduler is running"
else
    print_warning "Celery beat scheduler might not be running"
fi

echo ""
echo "=============================="
echo "🎉 FPL Pulse is starting!"
echo "=============================="
echo ""

# Step 3: Show service URLs
print_info "Service URLs:"
echo "  🌐 Frontend:    http://localhost:5173"
echo "  🔧 Django API:  http://localhost:8000"
echo "  📊 API Docs:    http://localhost:8000/api/landing/"
echo ""

# Step 4: Test API endpoints
print_info "Step 3: Testing new API endpoints..."
echo ""

# Test landing page
if curl -s http://localhost:8000/api/landing/ > /dev/null 2>&1; then
    print_success "Landing endpoint working"
else
    print_warning "Landing endpoint not responding (server might still be starting)"
fi

# Give it a bit more time for Django to fully start
sleep 5

# Test radar endpoint (try player ID 306 - Salah)
print_info "Testing radar endpoint (player 306)..."
RADAR_RESPONSE=$(curl -s http://localhost:8000/api/sofasport/player/306/radar/)
if echo "$RADAR_RESPONSE" | grep -q "player_id"; then
    print_success "Radar endpoint working!"
    echo "$RADAR_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20 || echo "$RADAR_RESPONSE" | head -20
else
    print_warning "Radar endpoint returned no data (player might not have SofaSport data yet)"
fi

echo ""

# Step 5: Show Celery status
print_info "Step 4: Checking Celery status..."
echo ""

# Check Celery worker
print_info "Celery worker status:"
docker exec fpl_celery_worker celery -A fpl_platform inspect active 2>/dev/null | head -10 || print_warning "Could not check Celery worker status"

echo ""

# Check scheduled tasks
print_info "Scheduled tasks:"
docker exec fpl_celery_beat celery -A fpl_platform inspect registered 2>/dev/null | grep -A 5 "registered" || print_warning "Could not check scheduled tasks"

echo ""
echo "=============================="
echo "📝 Next Steps"
echo "=============================="
echo ""
echo "1. Open browser: http://localhost:5173"
echo "2. Navigate to Players page"
echo "3. Click on any player to see the radar chart"
echo ""
echo "📚 Documentation:"
echo "  - SOFASPORT_SUMMARY.md     - Complete feature summary"
echo "  - RADAR_CHART_TESTING.md   - Testing instructions"
echo "  - CELERY_SETUP.md          - Celery setup guide"
echo ""
echo "🛠️  Useful Commands:"
echo ""
echo "  # View all running containers"
echo "  docker ps"
echo ""
echo "  # View Django logs"
echo "  docker logs -f fpl_django_web"
echo ""
echo "  # View Celery worker logs"
echo "  docker logs -f fpl_celery_worker"
echo ""
echo "  # View Celery beat logs"
echo "  docker logs -f fpl_celery_beat"
echo ""
echo "  # View frontend logs"
echo "  docker logs -f fpl_frontend"
echo ""
echo "  # Test API endpoints"
echo "  curl http://localhost:8000/api/sofasport/player/306/radar/"
echo "  curl 'http://localhost:8000/api/sofasport/compare/radar/?player_ids=306,301'"
echo ""
echo "  # Manually trigger a Celery task"
echo "  docker exec -it fpl_celery_worker python manage.py shell"
echo "  >>> from etl.tasks import update_fixture_mappings"
echo "  >>> result = update_fixture_mappings.delay()"
echo "  >>> print(result.get())"
echo ""
echo "  # Stop all services"
echo "  docker-compose down"
echo ""
echo "=============================="
print_success "Setup complete! 🎉"
echo "=============================="
