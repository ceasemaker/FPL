"""
Proxy views for FPL API to bypass CORS restrictions.
"""
import zlib

import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.core.cache import cache


def _passthrough(url, cache_key, ttl):
    """Forward FPL's JSON as the bytes it arrived in, held briefly in the cache.

    bootstrap-static is ~2 MB: parsing it and writing it out again cost the web
    process 7-9 MB and up to a few seconds on every call. The body is passed on
    untouched instead, and kept compressed (about a seventh of the size) so
    visitors in the same minute share one request to FPL.
    """
    packed = cache.get(cache_key)
    if packed is not None:
        return HttpResponse(zlib.decompress(packed), content_type="application/json")
    try:
        response = requests.get(url, timeout=15)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)
    if response.status_code != 200:
        return JsonResponse({"error": f"FPL returned {response.status_code}"}, status=response.status_code)
    body = response.content
    cache.set(cache_key, zlib.compress(body, 6), ttl)
    return HttpResponse(body, content_type="application/json")


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
    return _passthrough("https://fantasy.premierleague.com/api/bootstrap-static/", "fpl-proxy:bootstrap:v1", 60)


@require_GET
def proxy_event_live(request, event_id):
    """Proxy for FPL live gameweek data endpoint."""
    return _passthrough(f"https://fantasy.premierleague.com/api/event/{event_id}/live/", f"fpl-proxy:live:{event_id}:v1", 30)


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



