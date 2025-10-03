"""Orchestrates full data refresh from the FPL API into the database."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Sequence

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from ..models import (
    Athlete,
    AthleteStat,
    ElementSummary,
    EventStatus,
    Fixture,
    RawEndpointSnapshot,
    SetPieceNote,
    Team,
)
from .fpl_client import FPLClient

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    loop: bool = False
    sleep_seconds: int = 300
    snapshot_payloads: bool = True
    player_limit: int | None = None


def _to_decimal(value: object | None) -> Decimal | None:
    if value in (None, "", "null"):
        return None
    try:
        return Decimal(str(value))
    except Exception:  # pragma: no cover - defensive
        logger.debug("Unable to coerce %s to Decimal", value)
        return None


def _parse_datetime(value: object | None) -> datetime | None:
    if not value:
        return None
    dt = parse_datetime(str(value))
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.utc)
    return dt


def _parse_date(value: object | None) -> date | None:
    if not value:
        return None
    parsed = parse_date(str(value))
    return parsed


def _store_snapshot(endpoint: str, payload: object, identifier: str | None = None) -> None:
    RawEndpointSnapshot.objects.create(endpoint=endpoint, identifier=identifier, payload=payload)


def _sync_teams(teams_payload: Sequence[dict]) -> None:
    for team_data in teams_payload:
        defaults = {
            "code": team_data.get("code"),
            "name": team_data.get("name"),
            "short_name": team_data.get("short_name"),
            "strength": team_data.get("strength"),
            "played": team_data.get("played", 0),
            "win": team_data.get("win", 0),
            "draw": team_data.get("draw", 0),
            "loss": team_data.get("loss", 0),
            "points": team_data.get("points", 0),
            "position": team_data.get("position"),
            "form": team_data.get("form"),
            "unavailable": team_data.get("unavailable", False),
            "strength_overall_home": team_data.get("strength_overall_home"),
            "strength_overall_away": team_data.get("strength_overall_away"),
            "strength_attack_home": team_data.get("strength_attack_home"),
            "strength_attack_away": team_data.get("strength_attack_away"),
            "strength_defence_home": team_data.get("strength_defence_home"),
            "strength_defence_away": team_data.get("strength_defence_away"),
            "team_division": team_data.get("team_division"),
            "pulse_id": team_data.get("pulse_id"),
        }
        Team.objects.update_or_create(id=team_data["id"], defaults=defaults)


def _sync_athletes(athletes_payload: Sequence[dict]) -> None:
    decimal_fields = {
        "ep_next",
        "ep_this",
        "form",
        "points_per_game",
        "selected_by_percent",
        "value_form",
        "value_season",
        "influence",
        "creativity",
        "threat",
        "ict_index",
        "expected_goals",
        "expected_assists",
        "expected_goal_involvements",
        "expected_goals_conceded",
        "expected_goals_per_90",
        "saves_per_90",
        "expected_assists_per_90",
        "expected_goal_involvements_per_90",
        "expected_goals_conceded_per_90",
        "goals_conceded_per_90",
        "starts_per_90",
        "clean_sheets_per_90",
    }

    for athlete_data in athletes_payload:
        defaults: dict[str, object | None] = {
            "can_transact": athlete_data.get("can_transact"),
            "can_select": athlete_data.get("can_select"),
            "chance_of_playing_next_round": athlete_data.get("chance_of_playing_next_round"),
            "chance_of_playing_this_round": athlete_data.get("chance_of_playing_this_round"),
            "code": athlete_data.get("code"),
            "cost_change_event": athlete_data.get("cost_change_event", 0),
            "cost_change_event_fall": athlete_data.get("cost_change_event_fall", 0),
            "cost_change_start": athlete_data.get("cost_change_start", 0),
            "cost_change_start_fall": athlete_data.get("cost_change_start_fall", 0),
            "dreamteam_count": athlete_data.get("dreamteam_count", 0),
            "element_type": athlete_data.get("element_type"),
            "event_points": athlete_data.get("event_points", 0),
            "first_name": athlete_data.get("first_name"),
            "in_dreamteam": athlete_data.get("in_dreamteam", False),
            "news": athlete_data.get("news"),
            "news_added": _parse_datetime(athlete_data.get("news_added")),
            "now_cost": athlete_data.get("now_cost", 0),
            "photo": athlete_data.get("photo"),
            "removed": athlete_data.get("removed", False),
            "second_name": athlete_data.get("second_name"),
            "special": athlete_data.get("special", False),
            "squad_number": athlete_data.get("squad_number"),
            "status": athlete_data.get("status"),
            "team_id": athlete_data.get("team"),
            "team_code": athlete_data.get("team_code"),
            "total_points": athlete_data.get("total_points", 0),
            "transfers_in": athlete_data.get("transfers_in", 0),
            "transfers_in_event": athlete_data.get("transfers_in_event", 0),
            "transfers_out": athlete_data.get("transfers_out", 0),
            "transfers_out_event": athlete_data.get("transfers_out_event", 0),
            "web_name": athlete_data.get("web_name"),
            "region": athlete_data.get("region"),
            "team_join_date": _parse_date(athlete_data.get("team_join_date")),
            "birth_date": _parse_date(athlete_data.get("birth_date")),
            "has_temporary_code": athlete_data.get("has_temporary_code", False),
            "opta_code": athlete_data.get("opta_code"),
            "minutes": athlete_data.get("minutes", 0),
            "goals_scored": athlete_data.get("goals_scored", 0),
            "assists": athlete_data.get("assists", 0),
            "clean_sheets": athlete_data.get("clean_sheets", 0),
            "goals_conceded": athlete_data.get("goals_conceded", 0),
            "own_goals": athlete_data.get("own_goals", 0),
            "penalties_saved": athlete_data.get("penalties_saved", 0),
            "penalties_missed": athlete_data.get("penalties_missed", 0),
            "yellow_cards": athlete_data.get("yellow_cards", 0),
            "red_cards": athlete_data.get("red_cards", 0),
            "saves": athlete_data.get("saves", 0),
            "bonus": athlete_data.get("bonus", 0),
            "bps": athlete_data.get("bps", 0),
            "starts": athlete_data.get("starts", 0),
            "mng_win": athlete_data.get("mng_win", 0),
            "mng_draw": athlete_data.get("mng_draw", 0),
            "mng_loss": athlete_data.get("mng_loss", 0),
            "mng_underdog_win": athlete_data.get("mng_underdog_win", 0),
            "mng_underdog_draw": athlete_data.get("mng_underdog_draw", 0),
            "mng_clean_sheets": athlete_data.get("mng_clean_sheets", 0),
            "mng_goals_scored": athlete_data.get("mng_goals_scored", 0),
            "influence_rank": athlete_data.get("influence_rank"),
            "influence_rank_type": athlete_data.get("influence_rank_type"),
            "creativity_rank": athlete_data.get("creativity_rank"),
            "creativity_rank_type": athlete_data.get("creativity_rank_type"),
            "threat_rank": athlete_data.get("threat_rank"),
            "threat_rank_type": athlete_data.get("threat_rank_type"),
            "ict_index_rank": athlete_data.get("ict_index_rank"),
            "ict_index_rank_type": athlete_data.get("ict_index_rank_type"),
            "corners_and_indirect_freekicks_order": athlete_data.get(
                "corners_and_indirect_freekicks_order"
            ),
            "corners_and_indirect_freekicks_text": athlete_data.get(
                "corners_and_indirect_freekicks_text"
            ),
            "direct_freekicks_order": athlete_data.get("direct_freekicks_order"),
            "direct_freekicks_text": athlete_data.get("direct_freekicks_text"),
            "penalties_order": athlete_data.get("penalties_order"),
            "penalties_text": athlete_data.get("penalties_text"),
            "now_cost_rank": athlete_data.get("now_cost_rank"),
            "now_cost_rank_type": athlete_data.get("now_cost_rank_type"),
            "form_rank": athlete_data.get("form_rank"),
            "form_rank_type": athlete_data.get("form_rank_type"),
            "points_per_game_rank": athlete_data.get("points_per_game_rank"),
            "points_per_game_rank_type": athlete_data.get("points_per_game_rank_type"),
            "selected_rank": athlete_data.get("selected_rank"),
            "selected_rank_type": athlete_data.get("selected_rank_type"),
        }

        for field in decimal_fields:
            defaults[field] = _to_decimal(athlete_data.get(field))

        Athlete.objects.update_or_create(id=athlete_data["id"], defaults=defaults)


def _sync_fixtures(fixtures_payload: Sequence[dict]) -> None:
    for fixture_data in fixtures_payload:
        defaults = {
            "code": fixture_data.get("code"),
            "event": fixture_data.get("event"),
            "finished": fixture_data.get("finished", False),
            "finished_provisional": fixture_data.get("finished_provisional", False),
            "kickoff_time": _parse_datetime(fixture_data.get("kickoff_time")),
            "minutes": fixture_data.get("minutes", 0),
            "provisional_start_time": fixture_data.get("provisional_start_time", False),
            "started": fixture_data.get("started", False),
            "team_a_id": fixture_data.get("team_a"),
            "team_h_id": fixture_data.get("team_h"),
            "team_a_score": fixture_data.get("team_a_score"),
            "team_h_score": fixture_data.get("team_h_score"),
            "stats": fixture_data.get("stats", []),
            "team_a_difficulty": fixture_data.get("team_a_difficulty"),
            "team_h_difficulty": fixture_data.get("team_h_difficulty"),
            "pulse_id": fixture_data.get("pulse_id"),
        }
        Fixture.objects.update_or_create(id=fixture_data["id"], defaults=defaults)


def _sync_element_summary(player_id: int, payload: dict) -> None:
    athlete = Athlete.objects.filter(id=player_id).first()
    if not athlete:
        logger.debug("Skipping element summary for unknown athlete %s", player_id)
        return

    defaults = {
        "fixtures": payload.get("fixtures", []),
        "history": payload.get("history", []),
        "history_past": payload.get("history_past", []),
    }
    ElementSummary.objects.update_or_create(athlete=athlete, defaults=defaults)


def _sync_event_live(event_id: int, payload: dict) -> None:
    elements = payload.get("elements", [])
    for element in elements:
        stats = element.get("stats", {})
        athlete_id = element.get("id")
        athlete = Athlete.objects.filter(id=athlete_id).first()
        if not athlete:
            continue

        defaults = {
            "minutes": stats.get("minutes", 0),
            "goals_scored": stats.get("goals_scored", 0),
            "assists": stats.get("assists", 0),
            "clean_sheets": stats.get("clean_sheets", 0),
            "goals_conceded": stats.get("goals_conceded", 0),
            "own_goals": stats.get("own_goals", 0),
            "penalties_saved": stats.get("penalties_saved", 0),
            "penalties_missed": stats.get("penalties_missed", 0),
            "yellow_cards": stats.get("yellow_cards", 0),
            "red_cards": stats.get("red_cards", 0),
            "saves": stats.get("saves", 0),
            "bonus": stats.get("bonus", 0),
            "bps": stats.get("bps", 0),
            "influence": _to_decimal(stats.get("influence")) or Decimal("0"),
            "creativity": _to_decimal(stats.get("creativity")) or Decimal("0"),
            "threat": _to_decimal(stats.get("threat")) or Decimal("0"),
            "ict_index": _to_decimal(stats.get("ict_index")) or Decimal("0"),
            "starts": stats.get("starts", 0),
            "expected_goals": _to_decimal(stats.get("expected_goals")) or Decimal("0"),
            "expected_assists": _to_decimal(stats.get("expected_assists")) or Decimal("0"),
            "expected_goal_involvements": _to_decimal(stats.get("expected_goal_involvements"))
            or Decimal("0"),
            "expected_goals_conceded": _to_decimal(stats.get("expected_goals_conceded"))
            or Decimal("0"),
            "mng_win": stats.get("mng_win", 0),
            "mng_draw": stats.get("mng_draw", 0),
            "mng_loss": stats.get("mng_loss", 0),
            "mng_underdog_win": stats.get("mng_underdog_win", 0),
            "mng_underdog_draw": stats.get("mng_underdog_draw", 0),
            "mng_clean_sheets": stats.get("mng_clean_sheets", 0),
            "mng_goals_scored": stats.get("mng_goals_scored", 0),
            "total_points": stats.get("total_points", 0),
            "in_dreamteam": stats.get("in_dreamteam", False),
        }
        AthleteStat.objects.update_or_create(
            athlete=athlete,
            game_week=event_id,
            defaults=defaults,
        )


def _sync_event_status(payload: dict) -> None:
    for status in payload.get("status", []):
        status_value = status.get("status")
        if not status_value:
            logger.debug("Skipping event status entry without status value: %s", status)
            continue
        defaults = {
            "bonus_added": status.get("bonus_added", False),
            "status": status_value,
            "date": _parse_datetime(status.get("date")),
            "notes": status.get("notes"),
        }
        EventStatus.objects.update_or_create(
            event=status.get("event"),
            status=status_value,
            defaults=defaults,
        )


def _sync_set_piece_notes(payload: dict) -> None:
    for team_note in payload.get("notes", []):
        team_id = team_note.get("team") or team_note.get("id")
        if not team_id:
            continue
        team = Team.objects.filter(id=team_id).first()
        if not team:
            continue
        defaults = {
            "last_updated": _parse_datetime(team_note.get("last_updated") or team_note.get("updated")),
            "note": team_note.get("note") or team_note.get("short_note") or "",
        }
        SetPieceNote.objects.update_or_create(team=team, defaults=defaults)


@transaction.atomic
def run_single_pass(client: FPLClient, config: PipelineConfig) -> None:
    logger.info("Starting FPL ETL single pass")
    bootstrap = client.get_bootstrap_static()
    if config.snapshot_payloads:
        _store_snapshot("bootstrap-static", bootstrap)

    teams_payload = bootstrap.get("teams", [])
    _sync_teams(teams_payload)

    elements_payload = bootstrap.get("elements", [])
    if config.player_limit is not None:
        elements_payload = elements_payload[: config.player_limit]
        logger.info("Limiting element processing to first %s players", config.player_limit)
    _sync_athletes(elements_payload)

    events = [event.get("id") for event in bootstrap.get("events", []) if event.get("id")]

    fixtures_payload = client.get_fixtures()
    if config.snapshot_payloads:
        _store_snapshot("fixtures", fixtures_payload)
    _sync_fixtures(fixtures_payload)

    for event_id in events:
        fixtures_by_event = client.get_fixtures(event_id=event_id)
        if config.snapshot_payloads:
            _store_snapshot("fixtures", fixtures_by_event, identifier=f"event-{event_id}")
        _sync_fixtures(fixtures_by_event)

    for athlete_data in elements_payload:
        element_id = athlete_data.get("id")
        if not element_id:
            continue
        summary_payload = client.get_element_summary(element_id)
        if config.snapshot_payloads:
            _store_snapshot("element-summary", summary_payload, identifier=str(element_id))
        _sync_element_summary(element_id, summary_payload)

    for event_id in events:
        event_live_payload = client.get_event_live(event_id)
        if config.snapshot_payloads:
            _store_snapshot("event-live", event_live_payload, identifier=str(event_id))
        _sync_event_live(event_id, event_live_payload)

    event_status_payload = client.get_event_status()
    if config.snapshot_payloads:
        _store_snapshot("event-status", event_status_payload)
    _sync_event_status(event_status_payload)

    set_piece_notes_payload = client.get_set_piece_notes()
    if config.snapshot_payloads:
        _store_snapshot("team/set-piece-notes", set_piece_notes_payload)
    _sync_set_piece_notes(set_piece_notes_payload)

    logger.info("Completed FPL ETL single pass")


def run_pipeline(config: PipelineConfig) -> None:
    with FPLClient() as client:
        while True:
            try:
                run_single_pass(client, config)
            except Exception:  # pragma: no cover - handled by logging and re-raise
                logger.exception("FPL ETL encountered an error")
                raise

            if not config.loop:
                break

            logger.info("Sleeping for %s seconds before next ETL pass", config.sleep_seconds)
            time.sleep(config.sleep_seconds)
