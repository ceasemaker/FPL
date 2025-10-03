from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from django.core.cache import cache
from django.db.models import Count, F, Max, OuterRef, Prefetch, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Athlete, AthleteStat, Fixture, RawEndpointSnapshot, Team

PLAYER_IMAGE_BASE = "https://resources.premierleague.com/premierleague25/photos/players/110x140/"

# Cache timeouts (in seconds)
CACHE_TIMEOUT_24H = 86400  # 24 hours - perfect for daily data refresh at 3 AM
CACHE_TIMEOUT_1H = 3600  # 1 hour for more dynamic data


@dataclass
class PlayerMover:
    id: int
    first_name: str
    second_name: str
    team: str | None
    value: float
    now_cost: int | None
    total_points: int | None
    change_label: str
    image_url: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _player_image(photo: str | None) -> str | None:
    if not photo:
        return None
    clean = photo.split(".")[0]
    return f"{PLAYER_IMAGE_BASE}{clean}.png"


def _serialize_queryset(queryset, *, label: str, value_key: str) -> list[dict[str, Any]]:
    movers: list[PlayerMover] = []
    for record in queryset:
        mover = PlayerMover(
            id=record["id"],
            first_name=record["first_name"],
            second_name=record["second_name"],
            team=record.get("team__short_name"),
            value=float(record[value_key]) if record[value_key] is not None else 0.0,
            now_cost=record.get("now_cost"),
            total_points=record.get("total_points"),
            change_label=label,
            image_url=_player_image(record.get("photo")),
        )
        movers.append(mover.to_dict())
    return movers


@require_GET
def landing_snapshot(request):
    current_gw = (
        AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"]
        or 0
    )
    prev_gw = current_gw - 1 if current_gw else None

    price_risers_qs = (
        Athlete.objects.filter(cost_change_event__gt=0)
        .select_related("team")
        .order_by("-cost_change_event")
        .values(
            "id",
            "first_name",
            "second_name",
            "team__short_name",
            "cost_change_event",
            "now_cost",
            "total_points",
            "photo",
        )[:10]
    )
    price_fallers_qs = (
        Athlete.objects.filter(cost_change_event__lt=0)
        .select_related("team")
        .order_by("cost_change_event")
        .values(
            "id",
            "first_name",
            "second_name",
            "team__short_name",
            "cost_change_event",
            "now_cost",
            "total_points",
            "photo",
        )[:10]
    )

    if current_gw:
        points_current_subquery = Subquery(
            AthleteStat.objects.filter(
                athlete_id=OuterRef("pk"), game_week=current_gw
            )
            .values("total_points")[:1]
        )
    else:
        points_current_subquery = Value(0)
    if prev_gw:
        points_prev_subquery = Subquery(
            AthleteStat.objects.filter(
                athlete_id=OuterRef("pk"), game_week=prev_gw
            )
            .values("total_points")[:1]
        )
    else:
        points_prev_subquery = Value(0)

    points_delta_qs = (
        Athlete.objects.annotate(
            points_current=Coalesce(points_current_subquery, Value(0)),
            points_prev=Coalesce(points_prev_subquery, Value(0)),
            points_delta=F("points_current") - F("points_prev"),
        )
        .filter(points_current__gt=0)
        .select_related("team")
        .order_by("-points_delta")
        .values(
            "id",
            "first_name",
            "second_name",
            "team__short_name",
            "points_delta",
            "points_current",
            "now_cost",
            "total_points",
            "photo",
        )[:10]
    )

    price_movers = {
        "risers": _serialize_queryset(
            price_risers_qs, label="Price ↑", value_key="cost_change_event"
        ),
        "fallers": _serialize_queryset(
            price_fallers_qs, label="Price ↓", value_key="cost_change_event"
        ),
    }

    points_movers = _serialize_queryset(
        points_delta_qs, label="Points Δ", value_key="points_delta"
    )

    snapshot_counts = {
        row["endpoint"]: row["count"]
        for row in RawEndpointSnapshot.objects.values("endpoint")
        .annotate(count=Count("id"))
        .order_by("endpoint")
    }

    last_updated = (
        RawEndpointSnapshot.objects.order_by("-updated_at")
        .values_list("updated_at", flat=True)
        .first()
    )

    if not last_updated:
        last_updated = (
            Athlete.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )

    total_points_current = (
        AthleteStat.objects.filter(game_week=current_gw)
        .aggregate(total=Coalesce(Sum("total_points"), Value(0)))
        .get("total")
        if current_gw
        else 0
    )
    total_transfers = Athlete.objects.aggregate(
        transfers=Coalesce(Sum("transfers_in_event"), Value(0))
    ).get("transfers")

    pulse_index = (
        (total_points_current or 0) * 0.6
        + (total_transfers or 0) * 0.001
        + (snapshot_counts.get("event-live", 0) * 0.05)
    )

    max_event = current_gw + 4 if current_gw else 4

    fixtures_qs = (
        Fixture.objects.filter(event__isnull=False)
        .filter(event__gte=current_gw if current_gw else 1)
        .filter(event__lte=max_event)
        .values(
            "event",
            "team_h_id",
            "team_a_id",
            "team_h_difficulty",
            "team_a_difficulty",
        )
    )

    team_difficulty: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for fixture in fixtures_qs:
        event = fixture["event"]
        team_h_id = fixture["team_h_id"]
        team_a_id = fixture["team_a_id"]
        if team_h_id:
            team_difficulty[team_h_id][event] += fixture["team_h_difficulty"] or 0
        if team_a_id:
            team_difficulty[team_a_id][event] += fixture["team_a_difficulty"] or 0

    team_lookup = {
        team.id: team.short_name or team.name
        for team in Team.objects.all().only("id", "name", "short_name")
    }

    upcoming_pressure = []
    horizon = range(current_gw + 1, current_gw + 5) if current_gw else range(1, 5)
    horizon_length = len(list(horizon))
    
    for team_id, events in team_difficulty.items():
        window_sum = sum(events.get(ev, 0) for ev in horizon)
        # Calculate average difficulty over the fixture window
        avg_difficulty = round(window_sum / horizon_length, 2) if horizon_length > 0 else 0
        upcoming_pressure.append(
            {
                "team": team_lookup.get(team_id, str(team_id)),
                "score": avg_difficulty,
            }
        )

    easiest = sorted(upcoming_pressure, key=lambda item: item["score"])[:5]
    hardest = sorted(upcoming_pressure, key=lambda item: item["score"], reverse=True)[:5]

    # Most transferred in players
    transfers_in_qs = (
        Athlete.objects.filter(transfers_in_event__gt=0)
        .select_related("team")
        .order_by("-transfers_in_event")
        .values(
            "id",
            "first_name",
            "second_name",
            "team__short_name",
            "transfers_in_event",
            "now_cost",
            "total_points",
            "photo",
        )[:10]
    )

    # Most transferred out players
    transfers_out_qs = (
        Athlete.objects.filter(transfers_out_event__gt=0)
        .select_related("team")
        .order_by("-transfers_out_event")
        .values(
            "id",
            "first_name",
            "second_name",
            "team__short_name",
            "transfers_out_event",
            "now_cost",
            "total_points",
            "photo",
        )[:10]
    )

    transfers_in = _serialize_queryset(
        transfers_in_qs, label="Transfers In", value_key="transfers_in_event"
    )
    transfers_out = _serialize_queryset(
        transfers_out_qs, label="Transfers Out", value_key="transfers_out_event"
    )

    # Player news - get all players with news, ordered by most recent
    player_news_qs = (
        Athlete.objects.filter(news__isnull=False)
        .exclude(news="")
        .select_related("team")
        .order_by("-news_added")
        .values(
            "id",
            "first_name",
            "second_name",
            "web_name",
            "team__short_name",
            "team__code",
            "news",
            "news_added",
            "photo",
        )[:50]  # Limit to 50 most recent news items
    )

    player_news = [
        {
            "id": item["id"],
            "first_name": item["first_name"],
            "second_name": item["second_name"],
            "web_name": item["web_name"],
            "team": item["team__short_name"],
            "team_code": item["team__code"],
            "news": item["news"],
            "news_added": item["news_added"].isoformat() if item["news_added"] else None,
            "image_url": _player_image(item["photo"]),
        }
        for item in player_news_qs
    ]

    response: dict[str, Any] = {
        "current_gameweek": current_gw,
        "pulse": {
            "value": round(pulse_index, 2),
            "total_points_current": total_points_current,
            "total_transfers_in_event": total_transfers,
            "snapshot_counts": snapshot_counts,
            "last_updated": last_updated.isoformat() if last_updated else None,
        },
        "movers": {
            "price": price_movers,
            "points": points_movers,
        },
        "transfers": {
            "in": transfers_in,
            "out": transfers_out,
        },
        "fixture_pressure": {
            "easiest": easiest,
            "hardest": hardest,
        },
        "news": player_news,
    }

    return JsonResponse(response)


@require_GET
def fixtures_by_gameweek(request):
    """Return fixtures for a specific gameweek with difficulty ratings."""
    gw_param = request.GET.get("gameweek")
    
    if gw_param:
        try:
            target_gw = int(gw_param)
        except ValueError:
            return JsonResponse({"error": "Invalid gameweek parameter"}, status=400)
    else:
        target_gw = (
            AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"] or 1
        )
    
    fixtures_qs = (
        Fixture.objects.filter(event=target_gw)
        .select_related("team_h", "team_a")
        .order_by("kickoff_time", "id")
    )
    
    fixtures_data = []
    for fixture in fixtures_qs:
        fixtures_data.append({
            "id": fixture.id,
            "event": fixture.event,
            "kickoff_time": fixture.kickoff_time.isoformat() if fixture.kickoff_time else None,
            "team_h": fixture.team_h.name if fixture.team_h else None,
            "team_h_short": fixture.team_h.short_name if fixture.team_h else None,
            "team_h_id": fixture.team_h.id if fixture.team_h else None,
            "team_h_code": fixture.team_h.code if fixture.team_h else None,
            "team_a": fixture.team_a.name if fixture.team_a else None,
            "team_a_short": fixture.team_a.short_name if fixture.team_a else None,
            "team_a_id": fixture.team_a.id if fixture.team_a else None,
            "team_a_code": fixture.team_a.code if fixture.team_a else None,
            "team_h_difficulty": fixture.team_h_difficulty,
            "team_a_difficulty": fixture.team_a_difficulty,
            "team_h_score": fixture.team_h_score,
            "team_a_score": fixture.team_a_score,
            "finished": fixture.finished,
            "started": fixture.started,
        })
    
    available_gameweeks = list(
        Fixture.objects.filter(event__isnull=False)
        .values_list("event", flat=True)
        .distinct()
        .order_by("event")
    )
    
    return JsonResponse({
        "gameweek": target_gw,
        "fixtures": fixtures_data,
        "available_gameweeks": available_gameweeks,
    })


@require_GET
def players_list(request):
    """Return all players with key stats for player grid view."""
    search = request.GET.get("search", "").strip()
    team_filter = request.GET.get("team", "").strip()
    page = int(request.GET.get("page", "1"))
    page_size = int(request.GET.get("page_size", "50"))  # Default 50 players per page
    
    # Validate pagination params
    page = max(1, page)
    page_size = min(max(10, page_size), 500)  # Between 10 and 500
    
    # Build cache key based on filters
    cache_key = f"players_list:search={search}:team={team_filter}:page={page}:size={page_size}"
    
    # Try to get from cache first
    cached_response = cache.get(cache_key)
    if cached_response:
        return JsonResponse(cached_response)
    
    # Default sorting by total_points descending
    players_qs = Athlete.objects.select_related("team").all().order_by("-total_points")
    
    if search:
        players_qs = players_qs.filter(
            Q(first_name__icontains=search)
            | Q(second_name__icontains=search)
            | Q(web_name__icontains=search)
        )
    
    if team_filter:
        players_qs = players_qs.filter(team__short_name__iexact=team_filter)
    
    # Calculate pagination
    total_count = players_qs.count()
    total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Get current gameweek for FDR calculation
    current_gw = (
        AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"] or 1
    )
    
    # Pre-fetch all upcoming fixtures for all teams in ONE query
    upcoming_fixtures = {}
    fixtures_qs = Fixture.objects.filter(
        event__gte=current_gw + 1,
        event__lte=current_gw + 3,
    ).select_related("team_h", "team_a").order_by("event")
    
    # Group fixtures by team_id for fast lookup
    for fixture in fixtures_qs:
        if fixture.team_h_id:
            if fixture.team_h_id not in upcoming_fixtures:
                upcoming_fixtures[fixture.team_h_id] = []
            upcoming_fixtures[fixture.team_h_id].append(("home", fixture))
        if fixture.team_a_id:
            if fixture.team_a_id not in upcoming_fixtures:
                upcoming_fixtures[fixture.team_a_id] = []
            upcoming_fixtures[fixture.team_a_id].append(("away", fixture))
    
    # Calculate average FDR for next 3 fixtures per player (paginated)
    players_data = []
    for player in players_qs[start_idx:end_idx]:
        team = player.team
        team_id = team.id if team else None
        avg_fdr = None
        
        if team_id and team_id in upcoming_fixtures:
            # Get FDR values from pre-fetched fixtures
            fdr_values = []
            for location, fixture in upcoming_fixtures[team_id][:3]:
                if location == "home" and fixture.team_h_difficulty:
                    fdr_values.append(fixture.team_h_difficulty)
                elif location == "away" and fixture.team_a_difficulty:
                    fdr_values.append(fixture.team_a_difficulty)
            
            if fdr_values:
                avg_fdr = round(sum(fdr_values) / len(fdr_values), 1)
        
        players_data.append({
            "id": player.id,
            "first_name": player.first_name,
            "second_name": player.second_name,
            "web_name": player.web_name,
            "team": team.short_name if team else None,
            "team_id": team_id,
            "team_code": team.code if team else None,
            "now_cost": player.now_cost,
            "total_points": player.total_points,
            "form": float(player.form) if player.form else None,
            "avg_fdr": avg_fdr,
            "element_type": player.element_type,
            "image_url": _player_image(player.photo),
            "news": player.news,
            "news_added": player.news_added.isoformat() if player.news_added else None,
            # Performance stats
            "minutes": player.minutes,
            "goals_scored": player.goals_scored,
            "assists": player.assists,
            "clean_sheets": player.clean_sheets,
            "goals_conceded": player.goals_conceded,
            "bonus": player.bonus,
            "bps": player.bps,
            "selected_by_percent": float(player.selected_by_percent) if player.selected_by_percent else None,
        })
    
    response_data = {
        "players": players_data,
        "count": len(players_data),
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }
    
    # Cache for 24 hours (data refreshes daily at 3 AM)
    cache.set(cache_key, response_data, CACHE_TIMEOUT_24H)
    
    return JsonResponse(response_data)


@require_GET
def player_detail(request, player_id):
    """Return detailed stats for a specific player."""
    try:
        player = Athlete.objects.select_related("team").get(id=player_id)
    except Athlete.DoesNotExist:
        return JsonResponse({"error": "Player not found"}, status=404)
    
    team = player.team
    
    # Get current gameweek for FDR calculation
    current_gw = (
        AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"] or 1
    )
    
    # Calculate average FDR for next 3 fixtures
    avg_fdr = None
    if team:
        upcoming_fixtures = Fixture.objects.filter(
            Q(team_h_id=team.id) | Q(team_a_id=team.id),
            event__gte=current_gw + 1,
            event__lte=current_gw + 3,
        ).order_by("event")[:3]
        
        fdr_values = []
        for fixture in upcoming_fixtures:
            if fixture.team_h and fixture.team_h.id == team.id and fixture.team_h_difficulty:
                fdr_values.append(fixture.team_h_difficulty)
            elif fixture.team_a and fixture.team_a.id == team.id and fixture.team_a_difficulty:
                fdr_values.append(fixture.team_a_difficulty)
        
        if fdr_values:
            avg_fdr = round(sum(fdr_values) / len(fdr_values), 1)
    
    # Build comprehensive player data
    player_data = {
        # Basic Info
        "id": player.id,
        "first_name": player.first_name,
        "second_name": player.second_name,
        "web_name": player.web_name,
        "team": team.short_name if team else None,
        "team_id": team.id if team else None,
        "team_code": team.code if team else None,
        "element_type": player.element_type,
        "image_url": _player_image(player.photo),
        "status": player.status,
        "news": player.news,
        "news_added": player.news_added.isoformat() if player.news_added else None,
        
        # Cost & Ownership
        "now_cost": player.now_cost,
        "cost_change_event": player.cost_change_event,
        "cost_change_start": player.cost_change_start,
        "selected_by_percent": float(player.selected_by_percent) if player.selected_by_percent else None,
        
        # Points & Form
        "total_points": player.total_points,
        "event_points": player.event_points,
        "points_per_game": float(player.points_per_game) if player.points_per_game else None,
        "form": float(player.form) if player.form else None,
        "value_form": float(player.value_form) if player.value_form else None,
        "value_season": float(player.value_season) if player.value_season else None,
        
        # Transfers
        "transfers_in": player.transfers_in,
        "transfers_in_event": player.transfers_in_event,
        "transfers_out": player.transfers_out,
        "transfers_out_event": player.transfers_out_event,
        
        # Performance Stats
        "minutes": player.minutes,
        "goals_scored": player.goals_scored,
        "assists": player.assists,
        "clean_sheets": player.clean_sheets,
        "goals_conceded": player.goals_conceded,
        "own_goals": player.own_goals,
        "penalties_saved": player.penalties_saved,
        "penalties_missed": player.penalties_missed,
        "yellow_cards": player.yellow_cards,
        "red_cards": player.red_cards,
        "saves": player.saves,
        "bonus": player.bonus,
        "bps": player.bps,
        "starts": player.starts,
        
        # Advanced Stats (ICT)
        "influence": float(player.influence) if player.influence else None,
        "creativity": float(player.creativity) if player.creativity else None,
        "threat": float(player.threat) if player.threat else None,
        "ict_index": float(player.ict_index) if player.ict_index else None,
        
        # Expected Stats
        "expected_goals": float(player.expected_goals) if player.expected_goals else None,
        "expected_assists": float(player.expected_assists) if player.expected_assists else None,
        "expected_goal_involvements": float(player.expected_goal_involvements) if player.expected_goal_involvements else None,
        "expected_goals_conceded": float(player.expected_goals_conceded) if player.expected_goals_conceded else None,
        
        # Per 90 Stats
        "expected_goals_per_90": float(player.expected_goals_per_90) if player.expected_goals_per_90 else None,
        "expected_assists_per_90": float(player.expected_assists_per_90) if player.expected_assists_per_90 else None,
        "expected_goal_involvements_per_90": float(player.expected_goal_involvements_per_90) if player.expected_goal_involvements_per_90 else None,
        "expected_goals_conceded_per_90": float(player.expected_goals_conceded_per_90) if player.expected_goals_conceded_per_90 else None,
        "goals_conceded_per_90": float(player.goals_conceded_per_90) if player.goals_conceded_per_90 else None,
        "saves_per_90": float(player.saves_per_90) if player.saves_per_90 else None,
        "starts_per_90": float(player.starts_per_90) if player.starts_per_90 else None,
        "clean_sheets_per_90": float(player.clean_sheets_per_90) if player.clean_sheets_per_90 else None,
        
        # Rankings
        "influence_rank": player.influence_rank,
        "influence_rank_type": player.influence_rank_type,
        "creativity_rank": player.creativity_rank,
        "creativity_rank_type": player.creativity_rank_type,
        "threat_rank": player.threat_rank,
        "threat_rank_type": player.threat_rank_type,
        "ict_index_rank": player.ict_index_rank,
        "ict_index_rank_type": player.ict_index_rank_type,
        "now_cost_rank": player.now_cost_rank,
        "now_cost_rank_type": player.now_cost_rank_type,
        "form_rank": player.form_rank,
        "form_rank_type": player.form_rank_type,
        "points_per_game_rank": player.points_per_game_rank,
        "points_per_game_rank_type": player.points_per_game_rank_type,
        "selected_rank": player.selected_rank,
        "selected_rank_type": player.selected_rank_type,
        
        # Set Pieces
        "corners_and_indirect_freekicks_order": player.corners_and_indirect_freekicks_order,
        "corners_and_indirect_freekicks_text": player.corners_and_indirect_freekicks_text,
        "direct_freekicks_order": player.direct_freekicks_order,
        "direct_freekicks_text": player.direct_freekicks_text,
        "penalties_order": player.penalties_order,
        "penalties_text": player.penalties_text,
        
        # Fixtures
        "avg_fdr": avg_fdr,
        
        # Chance of Playing
        "chance_of_playing_this_round": player.chance_of_playing_this_round,
        "chance_of_playing_next_round": player.chance_of_playing_next_round,
    }
    
    return JsonResponse(player_data)


@require_GET
def dream_team(request):
    """
    Calculate and return the dream team (11 starters + 4 bench).
    
    Selection criteria:
    - Score = (total_points * 0.3) + (inverted_fdr * 0.4) + (form * 0.3)
    - FDR is inverted: lower is better, so we use (6 - fdr) to make higher scores better
    - Formation: 1 GKP, 4 DEF, 3 MID, 3 FWD (best 11)
    - Bench: 1 GKP, 1 DEF, 1 MID, 1 FWD
    - In case of tie, choose cheaper player
    """
    # Check cache first - Dream Team calculation is expensive
    cache_key = "dream_team:v1"
    cached_response = cache.get(cache_key)
    if cached_response:
        return JsonResponse(cached_response)
    
    # Get current gameweek for FDR calculation
    current_gw = (
        AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"] or 1
    )
    
    # Pre-fetch all upcoming fixtures for all teams in ONE query
    upcoming_fixtures = {}
    fixtures_qs = Fixture.objects.filter(
        event__gte=current_gw + 1,
        event__lte=current_gw + 3,
    ).select_related("team_h", "team_a").order_by("event")
    
    # Group fixtures by team_id for fast lookup
    for fixture in fixtures_qs:
        if fixture.team_h_id:
            if fixture.team_h_id not in upcoming_fixtures:
                upcoming_fixtures[fixture.team_h_id] = []
            upcoming_fixtures[fixture.team_h_id].append(("home", fixture))
        if fixture.team_a_id:
            if fixture.team_a_id not in upcoming_fixtures:
                upcoming_fixtures[fixture.team_a_id] = []
            upcoming_fixtures[fixture.team_a_id].append(("away", fixture))
    
    # Get all players with team info - only those with points
    players_qs = Athlete.objects.select_related("team").filter(
        total_points__gt=0  # Only active players
    )
    
    # Calculate scores for all players
    players_with_scores = []
    for player in players_qs:
        team = player.team
        team_id = team.id if team else None
        
        # Calculate average FDR for next 3 fixtures using pre-fetched data
        avg_fdr = 3.0  # Default neutral FDR
        if team_id and team_id in upcoming_fixtures:
            fdr_values = []
            for location, fixture in upcoming_fixtures[team_id][:3]:
                if location == "home" and fixture.team_h_difficulty:
                    fdr_values.append(fixture.team_h_difficulty)
                elif location == "away" and fixture.team_a_difficulty:
                    fdr_values.append(fixture.team_a_difficulty)
            
            if fdr_values:
                avg_fdr = sum(fdr_values) / len(fdr_values)
        
        # Normalize and calculate weighted score
        # Points: use as-is (already a good scale)
        # FDR: invert so lower difficulty = higher score (6 - fdr, where fdr is 1-5)
        # Form: use as-is (already 0-10 scale)
        points_score = float(player.total_points or 0)
        fdr_score = 6.0 - avg_fdr  # Invert: easier fixtures = higher score
        form_score = float(player.form or 0)
        
        # Weighted score: points (30%), fdr (40%), form (30%)
        weighted_score = (points_score * 0.3) + (fdr_score * 0.4) + (form_score * 0.3)
        
        players_with_scores.append({
            "id": player.id,
            "first_name": player.first_name,
            "second_name": player.second_name,
            "web_name": player.web_name,
            "team": team.short_name if team else None,
            "team_id": team_id,
            "team_code": team.code if team else None,
            "element_type": player.element_type,
            "now_cost": player.now_cost,
            "total_points": player.total_points,
            "form": form_score,
            "avg_fdr": round(avg_fdr, 1),
            "image_url": _player_image(player.photo),
            "weighted_score": round(weighted_score, 2),
        })
    
    # Sort by weighted_score (desc), then by now_cost (asc) for ties
    players_with_scores.sort(key=lambda x: (-x["weighted_score"], x["now_cost"]))
    
    # Separate by position
    goalkeepers = [p for p in players_with_scores if p["element_type"] == 1]
    defenders = [p for p in players_with_scores if p["element_type"] == 2]
    midfielders = [p for p in players_with_scores if p["element_type"] == 3]
    forwards = [p for p in players_with_scores if p["element_type"] == 4]
    
    # Select dream team: 1-4-3-3 formation + bench
    starting_11 = {
        "goalkeeper": goalkeepers[0] if goalkeepers else None,
        "defenders": defenders[:4],
        "midfielders": midfielders[:3],
        "forwards": forwards[:3],
    }
    
    # Bench: 1 GKP, 1 DEF, 1 MID, 1 FWD (next best in each position)
    bench = {
        "goalkeeper": goalkeepers[1] if len(goalkeepers) > 1 else None,
        "defender": defenders[4] if len(defenders) > 4 else None,
        "midfielder": midfielders[3] if len(midfielders) > 3 else None,
        "forward": forwards[3] if len(forwards) > 3 else None,
    }
    
    # Calculate team stats
    all_selected = (
        [starting_11["goalkeeper"]] + 
        starting_11["defenders"] + 
        starting_11["midfielders"] + 
        starting_11["forwards"]
    )
    all_selected = [p for p in all_selected if p is not None]
    
    bench_players = [p for p in bench.values() if p is not None]
    
    total_cost = sum(p["now_cost"] for p in all_selected + bench_players)
    total_points = sum(p["total_points"] for p in all_selected)
    avg_form = sum(p["form"] for p in all_selected) / len(all_selected) if all_selected else 0
    
    response_data = {
        "starting_11": starting_11,
        "bench": bench,
        "team_stats": {
            "total_cost": total_cost / 10,  # Convert to millions
            "total_points": total_points,
            "avg_form": round(avg_form, 1),
            "formation": "1-4-3-3",
        }
    }
    
    # Cache for 24 hours (data refreshes daily at 3 AM)
    cache.set(cache_key, response_data, CACHE_TIMEOUT_24H)
    
    return JsonResponse(response_data)
