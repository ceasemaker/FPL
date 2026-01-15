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


@require_GET
def proxy_league_standings(request, league_id):
    """Proxy for FPL classic league standings with Redis caching."""
    page = request.GET.get("page", "1")
    cache_key = f"league_standings_{league_id}_page_{page}"
    cached_data = cache.get(cache_key)

    if cached_data:
        return JsonResponse(cached_data, safe=False)

    url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/?page_standings={page}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            cache.set(cache_key, data, timeout=900)  # 15 minutes
            return JsonResponse(data, safe=False)
        return JsonResponse({"error": "League not found"}, status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def league_live_rank(request, league_id):
    """Compute live GW points and live ranks for a classic league."""
    try:
        limit = max(10, min(int(request.GET.get("limit", 30)), 50))
    except (TypeError, ValueError):
        limit = 30

    cache_key = f"league_live_{league_id}_limit_{limit}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached, safe=False)

    try:
        bootstrap = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=15)
        bootstrap.raise_for_status()
        bootstrap_data = bootstrap.json()
        current_event = next((e for e in bootstrap_data.get("events", []) if e.get("is_current")), None)
        current_event_id = current_event.get("id") if current_event else None

        if not current_event_id:
            return JsonResponse({"error": "Unable to determine current gameweek."}, status=400)

        standings = requests.get(
            f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/?page_standings=1",
            timeout=15,
        )
        standings.raise_for_status()
        standings_data = standings.json()
        results = standings_data.get("standings", {}).get("results", [])[:limit]

        live = requests.get(
            f"https://fantasy.premierleague.com/api/event/{current_event_id}/live/",
            timeout=15,
        )
        live.raise_for_status()
        live_data = live.json()
        live_points = {
            element["id"]: element.get("stats", {}).get("total_points", 0)
            for element in live_data.get("elements", [])
        }

        entries = []
        for entry in results:
            entry_id = entry.get("entry")
            picks_resp = requests.get(
                f"https://fantasy.premierleague.com/api/entry/{entry_id}/event/{current_event_id}/picks/",
                timeout=10,
            )
            if picks_resp.status_code != 200:
                live_total = 0
            else:
                picks_data = picks_resp.json()
                live_total = 0
                for pick in picks_data.get("picks", []):
                    element_id = pick.get("element")
                    multiplier = pick.get("multiplier", 0) or 0
                    points = live_points.get(element_id, 0)
                    live_total += points * multiplier

            entries.append({
                "entry": entry_id,
                "entry_name": entry.get("entry_name"),
                "player_name": entry.get("player_name"),
                "rank": entry.get("rank"),
                "total_points": entry.get("total"),
                "live_points": live_total,
            })

        entries_sorted = sorted(entries, key=lambda e: e["live_points"], reverse=True)
        live_rank_map = {entry["entry"]: idx + 1 for idx, entry in enumerate(entries_sorted)}
        for entry in entries:
            entry["live_rank"] = live_rank_map.get(entry["entry"])

        payload = {
            "league_id": league_id,
            "league_name": standings_data.get("league", {}).get("name"),
            "current_gameweek": current_event_id,
            "entries": entries,
        }
        cache.set(cache_key, payload, timeout=300)  # 5 minutes
        return JsonResponse(payload, safe=False)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)
