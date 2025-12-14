from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from django.core.cache import cache
from django.db.models import Count, F, Max, OuterRef, Prefetch, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Athlete, AthleteStat, Fixture, RawEndpointSnapshot, Team

logger = logging.getLogger(__name__)

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
        # Get current gameweek from max AthleteStat game_week
        current_gw = (
            AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"] or 1
        )
        
        # Check if all fixtures in current gameweek are finished
        # If so, show the next gameweek
        current_gw_fixtures = Fixture.objects.filter(event=current_gw)
        if current_gw_fixtures.exists():
            all_finished = all(f.finished for f in current_gw_fixtures)
            if all_finished:
                # Move to next gameweek
                target_gw = current_gw + 1
            else:
                target_gw = current_gw
        else:
            target_gw = current_gw
    
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


# ============================================================================
# SofaSport API Endpoints
# ============================================================================

@require_GET
def player_radar_attributes(request, player_id: int):
    """
    Get player attribute ratings for radar chart visualization.
    
    Returns:
        {
            "player_id": 123,
            "player_name": "Salah",
            "position": "F",
            "attributes": {
                "attacking": 71,
                "technical": 64,
                "tactical": 46,
                "defending": 33,
                "creativity": 69
            },
            "is_average": false,
            "year_shift": 0
        }
    """
    from .models import SofasportPlayerAttributes
    
    cache_key = f"radar_attributes_{player_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    try:
        # Try to get current season attributes first
        attrs = SofasportPlayerAttributes.objects.filter(
            athlete_id=player_id,
            year_shift=0,
            is_average=False
        ).select_related('athlete').first()
        
        # Fallback to career average
        if not attrs:
            attrs = SofasportPlayerAttributes.objects.filter(
                athlete_id=player_id,
                is_average=True
            ).select_related('athlete').first()
        
        if not attrs:
            return JsonResponse({"error": "No radar attributes found for this player"}, status=404)
        
        data = {
            "player_id": player_id,
            "player_name": attrs.athlete.web_name,
            "full_name": f"{attrs.athlete.first_name} {attrs.athlete.second_name}",
            "position": attrs.position,
            "attributes": {
                "attacking": attrs.attacking,
                "technical": attrs.technical,
                "tactical": attrs.tactical,
                "defending": attrs.defending,
                "creativity": attrs.creativity
            },
            "is_average": attrs.is_average,
            "year_shift": attrs.year_shift
        }
        
        # Cache for 24 hours
        cache.set(cache_key, data, CACHE_TIMEOUT_24H)
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def player_season_stats(request, player_id: int):
    """
    Get aggregated season statistics for a player.
    
    Returns comprehensive season stats including rating, goals, assists, etc.
    """
    from .models import SofasportPlayerSeasonStats
    
    cache_key = f"season_stats_{player_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    try:
        stats = SofasportPlayerSeasonStats.objects.filter(
            athlete_id=player_id,
            display_stats=True
        ).select_related('athlete', 'team').first()
        
        if not stats:
            return JsonResponse({"error": "No season stats found for this player"}, status=404)
        
        data = {
            "player_id": player_id,
            "player_name": stats.athlete.web_name,
            "team": stats.team.name if stats.team else None,
            "season_id": stats.season_id,
            "category": stats.category,
            
            # Core stats
            "rating": float(stats.rating) if stats.rating else None,
            "minutes_played": stats.minutes_played,
            "appearances": stats.appearances,
            
            # Attacking
            "goals": stats.goals,
            "assists": stats.assists,
            "expected_assists": float(stats.expected_assists) if stats.expected_assists else None,
            "shots": stats.shots,
            "big_chances": stats.big_chances,
            
            # Passing
            "accurate_passes": stats.accurate_passes,
            "total_passes": stats.total_passes,
            "pass_percentage": float(stats.pass_percentage) if stats.pass_percentage else None,
            "key_passes": stats.key_passes,
            "accurate_long_balls": stats.accurate_long_balls,
            "accurate_long_balls_percentage": float(stats.accurate_long_balls_percentage) if stats.accurate_long_balls_percentage else None,
            
            # Defensive
            "tackles": stats.tackles,
            "interceptions": stats.interceptions,
            "clearances": stats.clearances,
            
            # Duels
            "total_duels_won": stats.total_duels_won,
            "total_duels_won_percentage": float(stats.total_duels_won_percentage) if stats.total_duels_won_percentage else None,
            "aerial_duels_won": stats.aerial_duels_won,
            "ground_duels_won": stats.ground_duels_won,
            
            # Discipline
            "yellow_cards": stats.yellow_cards,
            "red_cards": stats.red_cards,
            "fouls": stats.fouls,
            "was_fouled": stats.was_fouled,
            
            # Goalkeeper
            "saves": stats.saves,
            "saves_percentage": float(stats.saves_percentage) if stats.saves_percentage else None,
            "clean_sheets": stats.clean_sheets,
            "goals_conceded": stats.goals_conceded,
            
            # Full statistics object
            "all_stats": stats.statistics
        }
        
        # Cache for 24 hours
        cache.set(cache_key, data, CACHE_TIMEOUT_24H)
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def player_heatmap(request, player_id: int, gameweek: int):
    """
    Get player heatmap coordinates for a specific gameweek.
    
    Returns:
        {
            "player_id": 123,
            "player_name": "Salah",
            "gameweek": 3,
            "coordinates": [{x: 45, y: 50}, {x: 46, y: 50}, ...],
            "point_count": 52
        }
    """
    from .models import SofasportHeatmap
    
    cache_key = f"heatmap_{player_id}_gw{gameweek}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    try:
        heatmap = SofasportHeatmap.objects.filter(
            athlete_id=player_id,
            fixture__fixture__event=gameweek
        ).select_related('athlete', 'fixture__fixture').first()
        
        if not heatmap:
            return JsonResponse({"error": "No heatmap data found for this player/gameweek"}, status=404)
        
        data = {
            "player_id": player_id,
            "player_name": heatmap.athlete.web_name,
            "gameweek": gameweek,
            "coordinates": heatmap.coordinates,
            "point_count": heatmap.point_count
        }
        
        # Cache for 24 hours
        cache.set(cache_key, data, CACHE_TIMEOUT_24H)
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def player_match_stats(request, player_id: int, gameweek: int):
    """
    Get detailed per-match statistics for a player in a specific gameweek.
    
    Returns lineup data with embedded statistics JSONField.
    """
    from .models import SofasportLineup
    
    cache_key = f"match_stats_{player_id}_gw{gameweek}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    try:
        lineup = SofasportLineup.objects.filter(
            athlete_id=player_id,
            fixture__fixture__event=gameweek
        ).select_related('athlete', 'team', 'fixture__fixture').first()
        
        if not lineup:
            return JsonResponse({"error": "No match stats found for this player/gameweek"}, status=404)
        
        data = {
            "player_id": player_id,
            "player_name": lineup.player_name,
            "gameweek": gameweek,
            "position": lineup.position,
            "shirt_number": lineup.shirt_number,
            "substitute": lineup.substitute,
            "minutes_played": lineup.minutes_played,
            "team": lineup.team.name if lineup.team else None,
            
            # All match statistics (20-60 fields depending on position)
            "statistics": lineup.statistics
        }
        
        # Cache for 24 hours
        cache.set(cache_key, data, CACHE_TIMEOUT_24H)
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def compare_players_radar(request):
    """
    Compare multiple players' radar attributes.
    
    Query params: player_ids=123,456,789
    
    Returns:
        {
            "players": [
                {
                    "player_id": 123,
                    "player_name": "Salah",
                    "position": "F",
                    "attributes": {...},
                    "is_average": false
                },
                ...
            ]
        }
    """
    from .models import SofasportPlayerAttributes
    
    player_ids_str = request.GET.get('player_ids', '')
    if not player_ids_str:
        return JsonResponse({"error": "player_ids query parameter required"}, status=400)
    
    try:
        player_ids = [int(pid.strip()) for pid in player_ids_str.split(',')]
    except ValueError:
        return JsonResponse({"error": "Invalid player_ids format"}, status=400)
    
    cache_key = f"compare_radar_{'_'.join(map(str, sorted(player_ids)))}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    try:
        players_data = []
        
        for player_id in player_ids:
            # Try current season first, fallback to career average
            attrs = SofasportPlayerAttributes.objects.filter(
                athlete_id=player_id,
                year_shift=0,
                is_average=False
            ).select_related('athlete').first()
            
            if not attrs:
                attrs = SofasportPlayerAttributes.objects.filter(
                    athlete_id=player_id,
                    is_average=True
                ).select_related('athlete').first()
            
            if attrs:
                players_data.append({
                    "player_id": player_id,
                    "player_name": attrs.athlete.web_name,
                    "full_name": f"{attrs.athlete.first_name} {attrs.athlete.second_name}",
                    "position": attrs.position,
                    "attributes": {
                        "attacking": attrs.attacking,
                        "technical": attrs.technical,
                        "tactical": attrs.tactical,
                        "defending": attrs.defending,
                        "creativity": attrs.creativity
                    },
                    "is_average": attrs.is_average,
                    "year_shift": attrs.year_shift
                })
        
        response_data = {"players": players_data}
        
        # Cache for 24 hours
        cache.set(cache_key, response_data, CACHE_TIMEOUT_24H)
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ============================================================================
# Top 100 Manager API Views
# ============================================================================

@require_GET
def top100_template(request):
    """
    Get the Top 100 template team - most common 22 players among top managers.
    
    Query params:
        - gameweek: Specific gameweek (optional, defaults to latest)
    
    Response:
        {
            "game_week": 15,
            "manager_count": 100,
            "template_squad": [
                {
                    "athlete_id": 123,
                    "web_name": "Salah",
                    "first_name": "Mohamed",
                    "second_name": "Salah",
                    "team_name": "Liverpool",
                    "team_short_name": "LIV",
                    "position": "Midfielder",
                    "element_type": 3,
                    "now_cost": 130,
                    "total_points": 120,
                    "ownership_count": 95,
                    "ownership_percentage": 95.0,
                    "image_url": "https://...",
                    "is_starting": true
                },
                ...
            ],
            "most_captained": [...],
            "chip_usage": {"wildcard": 2, "freehit": 1, ...}
        }
    """
    from .models import Top100Summary
    
    gameweek = request.GET.get("gameweek")
    
    cache_key = f"top100_template_{gameweek or 'latest'}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)
    
    try:
        if gameweek:
            summary = Top100Summary.objects.filter(game_week=int(gameweek)).first()
        else:
            summary = Top100Summary.objects.order_by("-game_week").first()
        
        if not summary:
            return JsonResponse({"error": "No Top 100 data available"}, status=404)
        
        # Enrich template squad with athlete details
        template_squad = []
        position_names = {1: "Goalkeeper", 2: "Defender", 3: "Midfielder", 4: "Forward"}
        
        for idx, item in enumerate(summary.template_squad or []):
            athlete_id = item.get("athlete_id")
            athlete = Athlete.objects.select_related("team").filter(id=athlete_id).first()
            
            if athlete:
                template_squad.append({
                    "athlete_id": athlete.id,
                    "web_name": athlete.web_name,
                    "first_name": athlete.first_name,
                    "second_name": athlete.second_name,
                    "team_name": athlete.team.name if athlete.team else None,
                    "team_short_name": athlete.team.short_name if athlete.team else None,
                    "position": position_names.get(athlete.element_type, "Unknown"),
                    "element_type": athlete.element_type,
                    "now_cost": athlete.now_cost,
                    "total_points": athlete.total_points,
                    "form": float(athlete.form) if athlete.form else 0,
                    "ownership_count": item.get("count", 0),
                    "ownership_percentage": item.get("percentage", 0),
                    "image_url": _player_image(athlete.photo),
                    "is_starting": idx < 11,  # First 11 are starters
                })
        
        # Enrich most captained
        most_captained = []
        for item in summary.most_captained or []:
            athlete_id = item.get("athlete_id")
            athlete = Athlete.objects.select_related("team").filter(id=athlete_id).first()
            if athlete:
                most_captained.append({
                    "athlete_id": athlete.id,
                    "web_name": athlete.web_name,
                    "team_short_name": athlete.team.short_name if athlete.team else None,
                    "count": item.get("count", 0),
                    "percentage": item.get("percentage", 0),
                    "image_url": _player_image(athlete.photo),
                })
        
        response_data = {
            "game_week": summary.game_week,
            "manager_count": summary.manager_count,
            "average_points": float(summary.average_points) if summary.average_points else 0,
            "highest_points": summary.highest_points,
            "lowest_points": summary.lowest_points,
            "template_squad": template_squad,
            "most_captained": most_captained,
            "chip_usage": summary.chip_usage or {},
        }
        
        cache.set(cache_key, response_data, CACHE_TIMEOUT_1H)
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def best_value_players(request):
    """
    Get best value players: Points per 90 (last 3 GWs) / Cost.
    Excludes injured players.
    
    Response:
        {
            "current_gameweek": 15,
            "goalkeepers": [...],  # 3 players
            "defenders": [...],    # 5 players
            "midfielders": [...],  # 5 players
            "forwards": [...]      # 5 players
        }
    
    Each player object:
        {
            "athlete_id": 123,
            "web_name": "Salah",
            "team_short_name": "LIV",
            "now_cost": 130,
            "now_cost_display": "13.0",
            "value_score": 2.5,
            "points_last_3": 35,
            "minutes_last_3": 270,
            "form": 8.5,
            "image_url": "...",
            "status": "a"
        }
    """
    from django.db.models import Sum
    
    cache_key = "best_value_players"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)
    
    try:
        # Get current gameweek
        current_gw = (
            AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"] or 0
        )
        
        # Calculate last 3 gameweeks
        gw_range = list(range(max(1, current_gw - 2), current_gw + 1))
        
        # Position limits
        position_limits = {
            1: ("goalkeepers", 3),
            2: ("defenders", 5),
            3: ("midfielders", 5),
            4: ("forwards", 5),
        }
        
        result = {"current_gameweek": current_gw}
        
        for element_type, (key, limit) in position_limits.items():
            # Get athletes of this position who are not injured
            # Status: 'a' = available, 'i' = injured, 'd' = doubtful, 's' = suspended, 'u' = unavailable
            athletes = (
                Athlete.objects.filter(
                    element_type=element_type,
                    status__in=["a", "d"],  # Available or doubtful (not fully injured)
                    now_cost__gt=0,
                )
                .select_related("team")
                .annotate(
                    points_last_3=Coalesce(
                        Sum(
                            "stats__total_points",
                            filter=Q(stats__game_week__in=gw_range)
                        ),
                        Value(0)
                    ),
                    minutes_last_3=Coalesce(
                        Sum(
                            "stats__minutes",
                            filter=Q(stats__game_week__in=gw_range)
                        ),
                        Value(0)
                    ),
                )
                .filter(minutes_last_3__gte=90)  # At least 90 mins in last 3 GWs
            )
            
            # Calculate value score and sort
            player_values = []
            for athlete in athletes:
                minutes = athlete.minutes_last_3 or 0
                points = athlete.points_last_3 or 0
                cost = athlete.now_cost or 1  # Avoid division by zero
                
                # Points per 90 / cost (normalized to per million)
                if minutes > 0:
                    points_per_90 = (points / minutes) * 90
                    value_score = points_per_90 / (cost / 10)  # cost is in tenths
                else:
                    value_score = 0
                
                player_values.append({
                    "athlete_id": athlete.id,
                    "web_name": athlete.web_name,
                    "first_name": athlete.first_name,
                    "second_name": athlete.second_name,
                    "team_short_name": athlete.team.short_name if athlete.team else None,
                    "now_cost": athlete.now_cost,
                    "now_cost_display": f"{athlete.now_cost / 10:.1f}",
                    "value_score": round(value_score, 2),
                    "points_last_3": points,
                    "minutes_last_3": minutes,
                    "form": float(athlete.form) if athlete.form else 0,
                    "total_points": athlete.total_points,
                    "image_url": _player_image(athlete.photo),
                    "status": athlete.status,
                })
            
            # Sort by value score and take top N
            player_values.sort(key=lambda x: x["value_score"], reverse=True)
            result[key] = player_values[:limit]
        
        cache.set(cache_key, result, CACHE_TIMEOUT_1H)
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def top100_points_chart(request):
    """
    Get points history for chart comparing:
    - Template team (most common starting 11 among top 100)
    - Average points of top 100 managers
    - Optionally: User's team points
    
    Query params:
        - start_gw: Starting gameweek (default: 1)
        - end_gw: Ending gameweek (optional)
        - entry_id: User's FPL entry ID for overlay (optional)
    
    Response:
        {
            "chart_data": [
                {
                    "game_week": 1,
                    "template_points": 65,
                    "average_points": 58.5,
                    "highest_points": 95,
                    "lowest_points": 32,
                    "user_points": null  // or actual points if entry_id provided
                },
                ...
            ],
            "user_info": null  // or {entry_name, player_name, total_points} if entry_id provided
        }
    """
    from .services.top100_etl import get_template_team_points_history, get_user_team_points_history
    
    start_gw = int(request.GET.get("start_gw", 1))
    end_gw = request.GET.get("end_gw")
    entry_id = request.GET.get("entry_id")
    
    if end_gw:
        end_gw = int(end_gw)
    
    cache_key = f"top100_chart_{start_gw}_{end_gw}_{entry_id or 'none'}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)
    
    try:
        # Get template team history
        chart_data = get_template_team_points_history(start_gw, end_gw)
        
        user_info = None
        
        # Add user data if entry_id provided
        if entry_id:
            entry_id = int(entry_id)
            user_history = get_user_team_points_history(entry_id, start_gw, end_gw)
            
            # Merge user data into chart_data
            user_points_map = {h["game_week"]: h for h in user_history}
            
            for item in chart_data:
                gw = item["game_week"]
                user_gw = user_points_map.get(gw)
                item["user_points"] = user_gw["points"] if user_gw else None
            
            # Get user info
            from .services.fpl_client import FPLClient
            with FPLClient() as client:
                try:
                    info = client.get_manager_info(entry_id)
                    user_info = {
                        "entry_id": entry_id,
                        "entry_name": info.get("name"),
                        "player_name": f"{info.get('player_first_name', '')} {info.get('player_last_name', '')}".strip(),
                        "total_points": info.get("summary_overall_points"),
                        "overall_rank": info.get("summary_overall_rank"),
                    }
                except Exception:
                    pass
        else:
            # Add null user_points to all entries
            for item in chart_data:
                item["user_points"] = None
        
        response_data = {
            "chart_data": chart_data,
            "user_info": user_info,
        }
        
        cache.set(cache_key, response_data, CACHE_TIMEOUT_1H)
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def top100_transfers(request):
    """
    Get transfer trends among top 100 managers.
    
    Query params:
        - gameweek: Specific gameweek (optional, defaults to latest)
    
    Response:
        {
            "game_week": 15,
            "transfers_in": [
                {
                    "athlete_id": 123,
                    "web_name": "Salah",
                    "team_short_name": "LIV",
                    "count": 45,
                    "now_cost": 130,
                    "image_url": "..."
                },
                ...
            ],
            "transfers_out": [...]
        }
    """
    from .models import Top100Summary
    
    gameweek = request.GET.get("gameweek")
    
    cache_key = f"top100_transfers_{gameweek or 'latest'}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)
    
    try:
        if gameweek:
            summary = Top100Summary.objects.filter(game_week=int(gameweek)).first()
        else:
            summary = Top100Summary.objects.order_by("-game_week").first()
        
        if not summary:
            return JsonResponse({"error": "No Top 100 data available"}, status=404)
        
        def enrich_transfers(items):
            result = []
            for item in items or []:
                athlete_id = item.get("athlete_id")
                athlete = Athlete.objects.select_related("team").filter(id=athlete_id).first()
                if athlete:
                    result.append({
                        "athlete_id": athlete.id,
                        "web_name": athlete.web_name,
                        "team_short_name": athlete.team.short_name if athlete.team else None,
                        "count": item.get("count", 0),
                        "now_cost": athlete.now_cost,
                        "now_cost_display": f"{athlete.now_cost / 10:.1f}",
                        "total_points": athlete.total_points,
                        "image_url": _player_image(athlete.photo),
                    })
            return result
        
        response_data = {
            "game_week": summary.game_week,
            "transfers_in": enrich_transfers(summary.most_transferred_in),
            "transfers_out": enrich_transfers(summary.most_transferred_out),
        }
        
        cache.set(cache_key, response_data, CACHE_TIMEOUT_1H)
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def top100_differentials(request):
    """
    Get differential picks - players owned by <15% of top 100 but with good points.
    These are the "hidden gems" that elite managers are using.
    
    Query params:
        - gameweek: Specific gameweek (optional, defaults to latest)
        - max_ownership: Maximum ownership percentage (default: 15)
    
    Response:
        {
            "game_week": 15,
            "differentials": [
                {
                    "athlete_id": 123,
                    "web_name": "Palmer",
                    "team_short_name": "CHE",
                    "ownership_percentage": 8.5,
                    "total_points": 85,
                    "form": 7.2,
                    "image_url": "..."
                },
                ...
            ]
        }
    """
    from .models import Top100Summary
    
    gameweek = request.GET.get("gameweek")
    max_ownership = float(request.GET.get("max_ownership", 15))
    
    cache_key = f"top100_differentials_{gameweek or 'latest'}_{max_ownership}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)
    
    try:
        if gameweek:
            summary = Top100Summary.objects.filter(game_week=int(gameweek)).first()
        else:
            summary = Top100Summary.objects.order_by("-game_week").first()
        
        if not summary:
            return JsonResponse({"error": "No Top 100 data available"}, status=404)
        
        # Find players with low ownership but still selected
        differentials = []
        for item in summary.template_squad or []:
            ownership = item.get("percentage", 0)
            if ownership <= max_ownership and ownership > 0:
                athlete_id = item.get("athlete_id")
                athlete = Athlete.objects.select_related("team").filter(id=athlete_id).first()
                if athlete:
                    differentials.append({
                        "athlete_id": athlete.id,
                        "web_name": athlete.web_name,
                        "first_name": athlete.first_name,
                        "second_name": athlete.second_name,
                        "team_short_name": athlete.team.short_name if athlete.team else None,
                        "position": {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}.get(athlete.element_type, "?"),
                        "ownership_percentage": ownership,
                        "ownership_count": item.get("count", 0),
                        "total_points": athlete.total_points,
                        "now_cost": athlete.now_cost,
                        "now_cost_display": f"{athlete.now_cost / 10:.1f}",
                        "form": float(athlete.form) if athlete.form else 0,
                        "image_url": _player_image(athlete.photo),
                    })
        
        # Sort by total points descending
        differentials.sort(key=lambda x: x["total_points"], reverse=True)
        
        response_data = {
            "game_week": summary.game_week,
            "max_ownership": max_ownership,
            "differentials": differentials[:15],  # Top 15 differentials
        }
        
        cache.set(cache_key, response_data, CACHE_TIMEOUT_1H)
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def player_recent_matches(request, player_id: int):
    """
    Get recent matches for a player including European competitions.
    
    Queries stored SofasportLineup and SofasportFixture data for the player's
    recent fixtures across all competitions (Premier League, UCL, Europa, cups, etc.)
    
    Query params:
        - limit: Number of matches to return (default: 10)
        - exclude_pl: If 'true', exclude Premier League matches (default: false)
    
    Returns:
        {
            "player_id": 123,
            "player_name": "Salah",
            "matches": [
                {
                    "event_id": "12345678",
                    "date": "2025-12-10T20:00:00Z",
                    "competition": "UEFA Champions League",
                    "competition_short": "UCL",
                    "home_team": "Liverpool",
                    "away_team": "Real Madrid",
                    "home_score": 2,
                    "away_score": 1,
                    "was_home": true,
                    "minutes_played": 90,
                    "goals": 1,
                    "assists": 0,
                    "yellow_cards": 0,
                    "red_cards": 0,
                    "rating": 7.8
                },
                ...
            ]
        }
    """
    from .models import Athlete, SofasportLineup, SofasportFixture
    
    cache_key = f"player_recent_matches_{player_id}"
    exclude_pl = request.GET.get("exclude_pl", "false").lower() == "true"
    if exclude_pl:
        cache_key += "_no_pl"
    
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    limit = int(request.GET.get("limit", 10))
    
    try:
        # Get the athlete
        try:
            athlete = Athlete.objects.get(id=player_id)
            player_name = athlete.web_name
        except Athlete.DoesNotExist:
            return JsonResponse({
                "player_id": player_id,
                "player_name": None,
                "matches": [],
                "error": "Player not found"
            }, status=404)
        
        # Query lineups for this player joined with fixtures
        lineups_query = SofasportLineup.objects.filter(
            athlete=athlete
        ).select_related('fixture').order_by('-fixture__kickoff_time')
        
        # Optionally exclude Premier League matches
        if exclude_pl:
            lineups_query = lineups_query.exclude(fixture__competition='PL')
        
        lineups = lineups_query[:limit]
        
        # Competition display names
        competition_names = {
            'PL': 'Premier League',
            'UCL': 'UEFA Champions League',
            'UEL': 'UEFA Europa League',
            'UECL': 'Conference League',
            'FAC': 'FA Cup',
            'EFL': 'EFL Cup',
            'OTHER': 'Other',
        }
        
        matches = []
        for lineup in lineups:
            fixture = lineup.fixture
            if not fixture:
                continue
            
            # Extract stats from lineup statistics JSON
            stats = lineup.statistics or {}
            
            # Determine team names
            home_team = fixture.home_team_name or (fixture.home_team.name if fixture.home_team else "Unknown")
            away_team = fixture.away_team_name or (fixture.away_team.name if fixture.away_team else "Unknown")
            
            # Determine if player was on home or away team
            was_home = False
            if athlete.team:
                was_home = (fixture.home_team == athlete.team)
            
            matches.append({
                "event_id": str(fixture.sofasport_event_id),
                "date": fixture.kickoff_time.isoformat() if fixture.kickoff_time else None,
                "competition": competition_names.get(fixture.competition, fixture.competition_name or fixture.competition),
                "competition_short": fixture.competition,
                "home_team": home_team,
                "home_team_id": fixture.sofasport_home_team_id,
                "away_team": away_team,
                "away_team_id": fixture.sofasport_away_team_id,
                "home_score": fixture.home_score_current,
                "away_score": fixture.away_score_current,
                "was_home": was_home,
                "minutes_played": lineup.minutes_played if lineup.minutes_played is not None else stats.get("minutesPlayed", 0),
                "goals": stats.get("goals", 0),
                "assists": stats.get("goalAssist", 0) or stats.get("assists", 0),
                "yellow_cards": stats.get("yellowCards", 0),
                "red_cards": stats.get("redCards", 0),
                "rating": round(stats.get("rating", 0), 1) if stats.get("rating") else None,
            })
        
        # Get sofasport_id from mapping for reference
        sofasport_id = None
        try:
            import json
            from pathlib import Path
            mapping_path = Path(__file__).parent.parent / "sofa_sport" / "mappings" / "player_mapping.json"
            if mapping_path.exists():
                with open(mapping_path) as f:
                    player_mapping = json.load(f)
                for sofa_id, mapping in player_mapping.items():
                    if mapping.get("fpl_id") == player_id:
                        sofasport_id = sofa_id
                        break
        except Exception:
            pass
        
        response_data = {
            "player_id": player_id,
            "sofasport_id": sofasport_id,
            "player_name": player_name,
            "matches": matches,
            "total_count": len(matches),
        }
        
        # Cache for 1 hour
        cache.set(cache_key, response_data, CACHE_TIMEOUT_1H)
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching recent matches for player {player_id}: {e}")
        return JsonResponse({"error": str(e)}, status=500)