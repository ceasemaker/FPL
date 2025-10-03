"""
Proxy views for FPL API to bypass CORS restrictions.
"""
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.cache import cache


@require_GET
def proxy_manager_summary(request, manager_id):
    """Proxy for FPL manager summary endpoint with Redis caching."""
    cache_key = f"manager_summary_{manager_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data, safe=False)
    
    url = f"https://fantasy.premierleague.com/api/entry/{manager_id}/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cache.set(cache_key, data, timeout=1800)  # 30 minutes
            return JsonResponse(data, safe=False)
        return JsonResponse({"error": "Manager not found"}, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def proxy_manager_history(request, manager_id):
    """Proxy for FPL manager history endpoint with Redis caching."""
    cache_key = f"manager_history_{manager_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data, safe=False)
    
    url = f"https://fantasy.premierleague.com/api/entry/{manager_id}/history/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cache.set(cache_key, data, timeout=1800)  # 30 minutes
            return JsonResponse(data, safe=False)
        return JsonResponse({"error": "History not found"}, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def proxy_manager_picks(request, manager_id, event_id):
    """Proxy for FPL manager picks for a specific gameweek with Redis caching."""
    cache_key = f"manager_picks_{manager_id}_gw{event_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data, safe=False)
    
    url = f"https://fantasy.premierleague.com/api/entry/{manager_id}/event/{event_id}/picks/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cache.set(cache_key, data, timeout=1800)  # 30 minutes
            return JsonResponse(data, safe=False)
        return JsonResponse({"error": "Picks not found"}, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def proxy_bootstrap_static(request):
    """Proxy for FPL bootstrap-static endpoint (all players and teams data)."""
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    try:
        response = requests.get(url, timeout=15)
        return JsonResponse(response.json(), safe=False, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def proxy_event_live(request, event_id):
    """Proxy for FPL live gameweek data endpoint."""
    url = f"https://fantasy.premierleague.com/api/event/{event_id}/live/"
    try:
        response = requests.get(url, timeout=15)
        return JsonResponse(response.json(), safe=False, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def proxy_fixtures(request):
    """Proxy for FPL fixtures endpoint with Redis caching."""
    cache_key = "fpl_fixtures"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data, safe=False)
    
    url = "https://fantasy.premierleague.com/api/fixtures/"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            cache.set(cache_key, data, timeout=900)  # 15 minutes
            return JsonResponse(data, safe=False)
        return JsonResponse({"error": "Fixtures not found"}, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def proxy_player_summary(request, player_id):
    """Proxy for FPL player summary endpoint (includes fixture/history data)."""
    cache_key = f"player_summary_{player_id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data, safe=False)
    
    url = f"https://fantasy.premierleague.com/api/element-summary/{player_id}/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cache.set(cache_key, data, timeout=1800)  # 30 minutes
            return JsonResponse(data, safe=False)
        return JsonResponse({"error": "Player summary not found"}, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)
