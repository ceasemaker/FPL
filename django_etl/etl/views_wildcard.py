"""
Views for Wildcard Simulator feature.

Hybrid storage approach:
1. Create minimal DB entry for tracking on first interaction
2. User edits in localStorage (free, instant)
3. Full save to DB only when user clicks "Save & Share"
"""

import json
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import WildcardSimulation, Athlete


@require_http_methods(["GET"])
def wildcard_home(request):
    """Main wildcard simulator page."""
    return render(request, 'wildcard/index.html')


@require_http_methods(["POST"])
@csrf_exempt
def track_wildcard_start(request):
    """
    Create minimal tracking entry when user starts building a team.
    Returns a code that identifies this team.
    """
    code = WildcardSimulation.generate_code()
    
    # Create minimal entry for tracking
    simulation = WildcardSimulation.objects.create(
        code=code,
        squad_data={'players': [], 'formation': None, 'captain': None},
        is_saved=False,
        gameweek=get_current_gameweek()
    )
    
    return JsonResponse({
        'success': True,
        'code': code,
        'message': 'Team tracking started'
    })


@require_http_methods(["GET"])
def get_wildcard_team(request, code):
    """
    Retrieve a wildcard team by code.
    Increments view count.
    """
    simulation = get_object_or_404(WildcardSimulation, code=code)
    
    # Increment view count
    simulation.view_count += 1
    simulation.save(update_fields=['view_count'])
    
    return JsonResponse({
        'success': True,
        'code': simulation.code,
        'squad_data': simulation.squad_data,
        'total_cost': float(simulation.total_cost),
        'predicted_points': simulation.predicted_points,
        'gameweek': simulation.gameweek,
        'team_name': simulation.team_name,
        'is_saved': simulation.is_saved,
        'created_at': simulation.created_at.isoformat(),
        'updated_at': simulation.updated_at.isoformat(),
    })


@require_http_methods(["PATCH", "PUT"])
@csrf_exempt
def save_wildcard_team(request, code):
    """
    Full save when user clicks "Save & Share".
    Updates squad data and marks as saved.
    """
    simulation = get_object_or_404(WildcardSimulation, code=code)
    
    try:
        data = json.loads(request.body)
        
        # Update squad data
        simulation.squad_data = data.get('squad_data', simulation.squad_data)
        simulation.team_name = data.get('team_name', simulation.team_name)
        simulation.is_saved = True
        
        # Calculate cost and points
        if 'players' in simulation.squad_data:
            simulation.total_cost = calculate_total_cost(simulation.squad_data['players'])
            simulation.predicted_points = calculate_predicted_points(simulation.squad_data['players'])
        
        simulation.save()
        
        return JsonResponse({
            'success': True,
            'code': simulation.code,
            'message': 'Team saved successfully',
            'total_cost': float(simulation.total_cost),
            'predicted_points': simulation.predicted_points,
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def wildcard_view(request, code):
    """
    Render the wildcard team page with the given code.
    """
    simulation = get_object_or_404(WildcardSimulation, code=code)
    
    # Increment view count
    simulation.view_count += 1
    simulation.save(update_fields=['view_count'])
    
    return render(request, 'wildcard/view.html', {
        'simulation': simulation,
        'code': code,
    })


# Helper functions

def get_current_gameweek():
    """Get the current gameweek number."""
    # TODO: Implement based on your Fixture model
    # For now, return a default value
    from django.db.models import Max
    from .models import Fixture
    
    current_gw = Fixture.objects.aggregate(
        max_gw=Max('event')
    )['max_gw']
    
    return current_gw if current_gw else 1


def calculate_total_cost(players):
    """Calculate total cost of squad."""
    if not players:
        return Decimal('0.0')
    
    total = Decimal('0.0')
    player_ids = [p.get('id') for p in players if p.get('id')]
    
    athletes = Athlete.objects.filter(id__in=player_ids)
    for athlete in athletes:
        total += Decimal(str(athlete.now_cost)) / Decimal('10')
    
    return total


def calculate_predicted_points(players):
    """Calculate predicted points for next gameweek."""
    if not players:
        return 0
    
    total_points = 0
    player_ids = [p.get('id') for p in players if p.get('id')]
    
    athletes = Athlete.objects.filter(id__in=player_ids)
    for athlete in athletes:
        # Simple prediction based on form
        if athlete.form:
            try:
                total_points += int(float(athlete.form))
            except (ValueError, TypeError):
                pass
    
    return total_points


@require_http_methods(["GET"])
def wildcard_stats(request):
    """
    Simple stats endpoint (not a full dashboard).
    Returns basic counts.
    """
    stats = {
        'total_teams': WildcardSimulation.objects.count(),
        'saved_teams': WildcardSimulation.objects.filter(is_saved=True).count(),
        'drafts': WildcardSimulation.objects.filter(is_saved=False).count(),
    }
    
    return JsonResponse(stats)
