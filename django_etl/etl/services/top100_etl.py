"""ETL service for syncing Top 100 manager data from FPL API."""

from __future__ import annotations

import logging
import time
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..models import (
    Athlete,
    Top100Manager,
    Top100Pick,
    Top100Summary,
    Top100Transfer,
)
from .fpl_client import FPLClient

logger = logging.getLogger(__name__)


@dataclass
class Top100Config:
    """Configuration for Top 100 ETL."""
    league_id: str = "314"  # Overall FPL league
    manager_count: int = 100  # Number of managers to track (flexible!)
    sleep_between_requests: float = 0.2  # Rate limiting


def _parse_datetime_value(value: str | None):
    """Parse datetime string from FPL API."""
    if not value:
        return None
    dt = parse_datetime(value)
    if dt and timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.utc)
    return dt


def fetch_top_managers(client: FPLClient, config: Top100Config) -> list[dict]:
    """
    Fetch top N managers from league standings.
    Returns list of manager data dicts.
    """
    managers = []
    pages_needed = (config.manager_count + 49) // 50  # 50 managers per page
    
    for page in range(1, pages_needed + 1):
        logger.info(f"Fetching league {config.league_id} standings page {page}")
        response = client.get_league_standings(config.league_id, page)
        
        standings = response.get("standings", {}).get("results", [])
        managers.extend(standings)
        
        if len(managers) >= config.manager_count:
            break
        
        time.sleep(config.sleep_between_requests)
    
    return managers[:config.manager_count]


def fetch_manager_picks(
    client: FPLClient, 
    entry_id: int, 
    game_week: int,
    config: Top100Config
) -> dict | None:
    """Fetch a manager's picks for a specific gameweek."""
    try:
        response = client.get_manager_picks(entry_id, game_week)
        time.sleep(config.sleep_between_requests)
        return response
    except Exception as e:
        logger.warning(f"Failed to fetch picks for manager {entry_id} GW{game_week}: {e}")
        return None


def fetch_manager_transfers(
    client: FPLClient, 
    entry_id: int,
    config: Top100Config
) -> list[dict]:
    """Fetch all transfers for a manager."""
    try:
        transfers = client.get_manager_transfers(entry_id)
        time.sleep(config.sleep_between_requests)
        return transfers if isinstance(transfers, list) else []
    except Exception as e:
        logger.warning(f"Failed to fetch transfers for manager {entry_id}: {e}")
        return []


@transaction.atomic
def sync_top100_for_gameweek(
    game_week: int,
    config: Top100Config | None = None,
) -> Top100Summary:
    """
    Main ETL function: sync top 100 managers data for a specific gameweek.
    
    Args:
        game_week: The gameweek to sync
        config: Optional configuration (uses defaults if not provided)
    
    Returns:
        Top100Summary object with aggregated stats
    """
    if config is None:
        config = Top100Config()
    
    logger.info(f"Starting Top {config.manager_count} sync for GW{game_week}")
    
    with FPLClient() as client:
        # Step 1: Fetch top managers from standings
        managers_data = fetch_top_managers(client, config)
        logger.info(f"Fetched {len(managers_data)} managers from standings")
        
        # Step 2: Process each manager
        all_picks: list[dict] = []
        all_transfers: list[dict] = []
        chip_usage: Counter = Counter()
        captain_picks: Counter = Counter()
        points_list: list[int] = []
        
        for idx, manager_data in enumerate(managers_data):
            entry_id = manager_data["entry"]
            rank = manager_data.get("rank", idx + 1)
            
            logger.debug(f"Processing manager {entry_id} (rank {rank})")
            
            # Create/update manager record
            manager, _ = Top100Manager.objects.update_or_create(
                entry_id=entry_id,
                game_week=game_week,
                defaults={
                    "player_name": manager_data.get("player_name", ""),
                    "entry_name": manager_data.get("entry_name", ""),
                    "rank": rank,
                    "last_rank": manager_data.get("last_rank"),
                    "total_points": manager_data.get("total", 0),
                    "event_total": manager_data.get("event_total", 0),
                }
            )
            
            points_list.append(manager_data.get("event_total", 0))
            
            # Fetch picks for this gameweek
            picks_data = fetch_manager_picks(client, entry_id, game_week, config)
            
            if picks_data:
                active_chip = picks_data.get("active_chip")
                if active_chip:
                    manager.active_chip = active_chip
                    manager.save(update_fields=["active_chip"])
                    chip_usage[active_chip] += 1
                
                # Get entry history for bank/value
                entry_history = picks_data.get("entry_history", {})
                if entry_history:
                    manager.bank = entry_history.get("bank", 0)
                    manager.team_value = entry_history.get("value", 0)
                    manager.save(update_fields=["bank", "team_value"])
                
                # Process picks
                picks = picks_data.get("picks", [])
                for pick in picks:
                    athlete_id = pick.get("element")
                    
                    # Verify athlete exists
                    if not Athlete.objects.filter(id=athlete_id).exists():
                        logger.warning(f"Athlete {athlete_id} not found, skipping pick")
                        continue
                    
                    Top100Pick.objects.update_or_create(
                        manager=manager,
                        athlete_id=athlete_id,
                        defaults={
                            "game_week": game_week,
                            "position": pick.get("position", 0),
                            "is_captain": pick.get("is_captain", False),
                            "is_vice_captain": pick.get("is_vice_captain", False),
                            "multiplier": pick.get("multiplier", 1),
                        }
                    )
                    
                    all_picks.append({
                        "athlete_id": athlete_id,
                        "position": pick.get("position", 0),
                        "is_captain": pick.get("is_captain", False),
                    })
                    
                    if pick.get("is_captain"):
                        captain_picks[athlete_id] += 1
            
            # Fetch transfers
            transfers = fetch_manager_transfers(client, entry_id, config)
            gw_transfers = [t for t in transfers if t.get("event") == game_week]
            
            for transfer in gw_transfers:
                element_in_id = transfer.get("element_in")
                element_out_id = transfer.get("element_out")
                
                # Verify athletes exist
                if not Athlete.objects.filter(id=element_in_id).exists():
                    continue
                if not Athlete.objects.filter(id=element_out_id).exists():
                    continue
                
                Top100Transfer.objects.get_or_create(
                    manager=manager,
                    game_week=game_week,
                    element_in_id=element_in_id,
                    element_out_id=element_out_id,
                    defaults={
                        "element_in_cost": transfer.get("element_in_cost", 0),
                        "element_out_cost": transfer.get("element_out_cost", 0),
                        "transfer_time": _parse_datetime_value(transfer.get("time")),
                    }
                )
                
                all_transfers.append({
                    "element_in": element_in_id,
                    "element_out": element_out_id,
                })
            
            # Progress logging
            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{len(managers_data)} managers")
        
        # Step 3: Compute summary statistics
        summary = _compute_summary(
            game_week=game_week,
            config=config,
            all_picks=all_picks,
            all_transfers=all_transfers,
            captain_picks=captain_picks,
            chip_usage=chip_usage,
            points_list=points_list,
        )
        
        logger.info(f"Completed Top {config.manager_count} sync for GW{game_week}")
        return summary


def _compute_summary(
    game_week: int,
    config: Top100Config,
    all_picks: list[dict],
    all_transfers: list[dict],
    captain_picks: Counter,
    chip_usage: Counter,
    points_list: list[int],
) -> Top100Summary:
    """Compute and store summary statistics."""
    
    # Count player ownership (all 15 squad players)
    squad_ownership: Counter = Counter()
    starting_ownership: Counter = Counter()  # Only positions 1-11
    
    for pick in all_picks:
        athlete_id = pick["athlete_id"]
        squad_ownership[athlete_id] += 1
        if pick["position"] <= 11:
            starting_ownership[athlete_id] += 1
    
    # Template team: most common starting 11
    template_team = []
    for athlete_id, count in starting_ownership.most_common(11):
        percentage = (count / config.manager_count) * 100
        template_team.append({
            "athlete_id": athlete_id,
            "count": count,
            "percentage": round(percentage, 1),
        })
    
    # Template squad: most common 22 players (15 typical + extras for bench)
    template_squad = []
    for athlete_id, count in squad_ownership.most_common(22):
        percentage = (count / config.manager_count) * 100
        template_squad.append({
            "athlete_id": athlete_id,
            "count": count,
            "percentage": round(percentage, 1),
        })
    
    # Most captained
    most_captained = []
    for athlete_id, count in captain_picks.most_common(5):
        percentage = (count / config.manager_count) * 100
        most_captained.append({
            "athlete_id": athlete_id,
            "count": count,
            "percentage": round(percentage, 1),
        })
    
    # Transfer trends
    transfers_in: Counter = Counter()
    transfers_out: Counter = Counter()
    for t in all_transfers:
        transfers_in[t["element_in"]] += 1
        transfers_out[t["element_out"]] += 1
    
    most_transferred_in = [
        {"athlete_id": aid, "count": c}
        for aid, c in transfers_in.most_common(10)
    ]
    most_transferred_out = [
        {"athlete_id": aid, "count": c}
        for aid, c in transfers_out.most_common(10)
    ]
    
    # Chip usage dict
    chip_dict = dict(chip_usage)
    
    # Points stats
    avg_points = sum(points_list) / len(points_list) if points_list else 0
    
    # Create/update summary
    summary, _ = Top100Summary.objects.update_or_create(
        game_week=game_week,
        defaults={
            "manager_count": config.manager_count,
            "league_id": config.league_id,
            "average_points": Decimal(str(round(avg_points, 2))),
            "highest_points": max(points_list) if points_list else None,
            "lowest_points": min(points_list) if points_list else None,
            "template_team": template_team,
            "template_squad": template_squad,
            "most_captained": most_captained,
            "chip_usage": chip_dict,
            "most_transferred_in": most_transferred_in,
            "most_transferred_out": most_transferred_out,
        }
    )
    
    return summary


def get_template_team_points_history(
    start_gw: int = 1,
    end_gw: int | None = None,
) -> list[dict]:
    """
    Get points history for the template team (most common starting 11).
    Used for the chart comparing template vs overall performance.
    
    Returns list of {game_week, template_points, average_selected_points}
    """
    from django.db.models import Avg
    
    summaries = Top100Summary.objects.all()
    if end_gw:
        summaries = summaries.filter(game_week__lte=end_gw)
    summaries = summaries.filter(game_week__gte=start_gw).order_by("game_week")
    
    history = []
    for summary in summaries:
        # Calculate template team points for this GW
        template_points = 0
        template_team = summary.template_team or []
        
        for player in template_team[:11]:
            athlete_id = player.get("athlete_id")
            # Get athlete's points for this gameweek
            from ..models import AthleteStat
            stat = AthleteStat.objects.filter(
                athlete_id=athlete_id,
                game_week=summary.game_week
            ).first()
            if stat:
                template_points += stat.total_points
        
        history.append({
            "game_week": summary.game_week,
            "template_points": template_points,
            "average_points": float(summary.average_points) if summary.average_points else 0,
            "highest_points": summary.highest_points,
            "lowest_points": summary.lowest_points,
        })
    
    return history


def get_user_team_points_history(
    entry_id: int,
    start_gw: int = 1,
    end_gw: int | None = None,
) -> list[dict]:
    """
    Fetch a user's team points history for chart overlay.
    
    Args:
        entry_id: FPL manager entry ID
        start_gw: Starting gameweek
        end_gw: Ending gameweek (optional)
    
    Returns:
        List of {game_week, points, overall_rank}
    """
    with FPLClient() as client:
        try:
            history = client.get_manager_history(entry_id)
            current = history.get("current", [])
            
            result = []
            for gw in current:
                gw_num = gw.get("event", 0)
                if gw_num < start_gw:
                    continue
                if end_gw and gw_num > end_gw:
                    continue
                
                result.append({
                    "game_week": gw_num,
                    "points": gw.get("points", 0),
                    "total_points": gw.get("total_points", 0),
                    "overall_rank": gw.get("overall_rank"),
                    "percentile_rank": gw.get("percentile_rank"),
                    "bank": gw.get("bank", 0),
                    "value": gw.get("value", 0),
                })
            
            return result
        except Exception as e:
            logger.error(f"Failed to fetch history for manager {entry_id}: {e}")
            return []
