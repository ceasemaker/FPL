"""Assemble the local, read-only FPL decision dashboard payload."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db.models import Max


POSITION_SD = {"GKP": 2.8, "DEF": 3.0, "MID": 3.4, "FWD": 3.5}


def _analysis_output_dir() -> Path:
    configured = os.environ.get("FPL_ANALYSIS_OUTPUT_DIR")
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR).parent / "analysis" / "fpl_decision_backtest" / "output"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Decision artifact is missing: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _player_rows(team: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    horizon = int(team.get("horizon") or 1)
    for player in team.get("squad", []):
        predictions = {
            int(gameweek): float(points)
            for gameweek, points in (player.get("predictions") or {}).items()
        }
        ordered = sorted(predictions.items())[:horizon]
        weighted_xp = sum((0.9**index) * points for index, (_, points) in enumerate(ordered))
        next_xp = ordered[0][1] if ordered else 0.0
        ownership = float(player.get("ownership") or 0.0)
        price = max(float(player.get("current_price") or 0.0), 0.1)
        position = str(player.get("position") or "")
        rank_exposure = (1.0 - ownership) * next_xp
        rank_risk = abs(1.0 - ownership) * POSITION_SD.get(position, 3.3)
        if ownership >= 0.65:
            role = "shield"
        elif ownership < 0.10:
            role = "differential"
        else:
            role = "balanced"
        rows.append({
            **player,
            "next_xp": round(next_xp, 2),
            "horizon_xp": round(weighted_xp, 2),
            "xp_per_m": round(weighted_xp / price, 2),
            "rank_exposure": round(rank_exposure, 2),
            "rank_risk": round(rank_risk, 2),
            "role": role,
        })
    return sorted(rows, key=lambda player: player["horizon_xp"], reverse=True)


def _accepted_forecast_summary(stacked: dict[str, Any] | None) -> dict[str, Any] | None:
    """Plain-language summary of the candidate forecast and gate evidence."""
    if not stacked:
        return None
    gate = stacked.get("authority_gate", {})
    return {
        "model": "stacked ridge (form + market odds + structural Poisson components)",
        "accepted_for_mean_forecast": bool(gate.get("accepted_for_mean_forecast")),
        "accepted_for_optimizer": bool(gate.get("accepted_for_optimizer")),
        "accepted_for_transfer_horizon": bool(gate.get("accepted_for_transfer_horizon")),
        "evidence": {
            "mae_gain_vs_odds_ridge": gate.get("mae_gain"),
            "mae_gain_ci95": gate.get("mae_gain_ci95"),
            "correlation_gain_ci95": gate.get("correlation_gain_ci95"),
            "top5_weekly_diff_ci95": gate.get("top5_points_diff_ci95"),
            "horizon_correlation_gain_ci95": gate.get("horizon_correlation_gain_ci95"),
        },
        "caveat": (
            "Mean-forecast accuracy improves on the 2025/26 evaluation season, "
            "but top-five superiority is unproven and the corrected three-week "
            "bootstrap does not support promotion. The optimizer remains unchanged."
        ),
    }


def _research_summary(
    stacked: dict[str, Any] | None,
    team_replays: list[dict[str, Any]],
) -> dict[str, Any]:
    gate = (stacked or {}).get("authority_gate", {})
    replay_evidence = []
    for replay in team_replays:
        transfer_value = replay.get("transfer_value_results") or {}
        replay_evidence.append({
            "start_gameweek": replay.get("start_gameweek"),
            "manager_count": replay.get("manager_count"),
            "median_transfer_value": transfer_value.get("median_delta"),
            "mean_transfer_value": transfer_value.get("mean_delta"),
            "paths_positive": transfer_value.get("paths_transfers_added_value"),
        })
    return {
        "report_url": "/api/decision-dashboard/research-report/",
        "data": {
            "seasons": ["2022/23", "2023/24", "2024/25", "2025/26"],
            "odds": "Football-Data.co.uk opening-average 1X2 and over/under 2.5",
            "timing": "Player features stop at GW-1; season models train only on earlier seasons.",
        },
        "layers": [
            {"name": "Data and odds", "status": "working", "detail": "Four archived seasons with cached no-vig opening markets."},
            {"name": "Mean player xP", "status": "working", "detail": "Stacked mean accuracy improves under a week-cluster bootstrap."},
            {"name": "Top-player ranking", "status": "research", "detail": "Weekly top-five superiority is not established."},
            {"name": "Three-week decisions", "status": "research", "detail": "Utility is promising, but the corrected correlation interval crosses zero."},
            {"name": "Transfer optimizer", "status": "prototype", "detail": "Restricted point-estimate search; not approved as decision authority."},
        ],
        "pipeline": [
            {"label": "Market", "detail": "Remove bookmaker margin"},
            {"label": "Match", "detail": "Fit home/away Poisson goals"},
            {"label": "Player", "detail": "Allocate minutes, xG and xA"},
            {"label": "FPL", "detail": "Apply ordinary scoring"},
            {"label": "Risk", "detail": "Simulate blanks, hauls and rank exposure"},
        ],
        "evidence": {
            "mae_gain": gate.get("mae_gain"),
            "mae_gain_ci95": gate.get("mae_gain_ci95"),
            "top5_difference": gate.get("top5_points_weekly_diff"),
            "top5_ci95": gate.get("top5_points_diff_ci95"),
            "horizon_utility_difference": gate.get("horizon_top5_3gw_diff"),
            "horizon_utility_ci95": gate.get("horizon_top5_3gw_diff_ci95"),
            "horizon_correlation_ci95": gate.get("horizon_correlation_gain_ci95"),
        },
        "replay_evidence": replay_evidence,
        "limitations": [
            "No reliable historical weekly purchase and selling prices.",
            "No deadline-level injury, predicted-lineup, penalty or set-piece role feed.",
            "Player events are not yet simulated jointly within one shared match state.",
            "Replay starting squads come from an ex-post-selected eventual top-100 cohort.",
            "2025/26 is evaluation evidence, not a pristine untouched authority holdout.",
        ],
    }


def _live_next_gameweek() -> int | None:
    """Next gameweek according to the database the ETL refreshes.

    The dashboard is built from a saved local analysis, so it can silently fall
    behind the live season. Comparing against this lets the UI say so instead
    of presenting an old run as current.
    """
    from ..models import AthleteStat

    latest_completed = AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"]
    if not latest_completed:
        return None
    return latest_completed + 1


def build_decision_dashboard(manager_id: int, risk_profile: str = "balanced") -> dict[str, Any]:
    if risk_profile not in {"protect", "balanced", "chase"}:
        raise ValueError("risk_profile must be protect, balanced, or chase")
    output_dir = _analysis_output_dir()
    team = _read_json(output_dir / f"team_{manager_id}_live.json")
    if int(team.get("entry", {}).get("id") or 0) != manager_id:
        raise ValueError("The saved team analysis does not match this manager")
    base_backtest = _read_json(output_dir / "summary.json")
    odds_backtest = _read_json(output_dir / "odds_backtest_summary.json")
    stacked_path = output_dir / "stacked_backtest_summary.json"
    stacked_backtest = _read_json(stacked_path) if stacked_path.exists() else None
    replay_path = output_dir / "team_replay_gw10_summary.json"
    team_replay = _read_json(replay_path) if replay_path.exists() else None
    team_replays = []
    for replay_gameweek in (2, 10):
        candidate = output_dir / f"team_replay_gw{replay_gameweek}_summary.json"
        if candidate.exists():
            team_replays.append(_read_json(candidate))
    players = _player_rows(team)
    profile = team.get("profiles", {}).get(risk_profile, {})
    lineup = (profile.get("lineups") or [{}])[0]
    player_lookup = {int(player["id"]): player for player in players}
    starters = [player_lookup[player_id] for player_id in lineup.get("starters", []) if player_id in player_lookup]
    captain_id = lineup.get("captain")
    shields = [player for player in players if player["role"] == "shield"]
    differentials = [player for player in players if player["role"] == "differential"]
    weak_spots = sorted(players, key=lambda player: (player["next_xp"], player["horizon_xp"]))[:3]
    total_next_xp = sum(player["next_xp"] for player in starters)
    if captain_id in player_lookup:
        total_next_xp += player_lookup[captain_id]["next_xp"]

    saved_next_gameweek = team.get("start_gameweek")
    live_next_gameweek = _live_next_gameweek()
    is_stale = bool(
        saved_next_gameweek
        and live_next_gameweek
        and int(saved_next_gameweek) != int(live_next_gameweek)
    )

    return {
        "meta": {
            "manager_id": manager_id,
            "generated_at": team.get("generated_at"),
            "risk_profile": risk_profile,
            "data_mode": "saved local analysis",
            "projection_warning": team.get("projection_warning"),
            "public_squad_warning": team.get("public_squad_warning"),
            "saved_for_gameweek": saved_next_gameweek,
            "live_next_gameweek": live_next_gameweek,
            "is_stale": is_stale,
        },
        "manager": team.get("entry", {}),
        "gameweek": {
            "current": team.get("current_gameweek"),
            "next": team.get("start_gameweek"),
            "deadline": team.get("deadline"),
            "horizon": team.get("horizon"),
            "next_xp": round(total_next_xp, 2),
            "captain": player_lookup.get(captain_id),
        },
        "decision": {
            "recommended_action": profile.get("recommended_action"),
            "hold_expected_points": round(float(profile.get("hold_expected_points") or 0.0), 2),
            "minimum_gain_to_spend_transfer": profile.get("minimum_gain_to_spend_transfer"),
            "transfers": (profile.get("top_one_transfer_moves") or [])[:5],
        },
        "squad": players,
        "signals": {
            "shields": shields,
            "differentials": differentials,
            "weak_spots": weak_spots,
        },
        "backtest": {
            "baseline": base_backtest,
            "odds": odds_backtest,
            "stacked": stacked_backtest,
            "team_replay": team_replay,
            "team_replays": team_replays,
        },
        "accepted_forecast": _accepted_forecast_summary(stacked_backtest),
        "research": _research_summary(stacked_backtest, team_replays),
    }
