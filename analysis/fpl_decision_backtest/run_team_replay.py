#!/usr/bin/env python3
"""Replay anonymous archived FPL squads against the walk-forward model.

The archived squad export contains 100 managers in a stable row order, but it
does not contain their entry IDs.  This script therefore labels them squad
slots 1-100 and never claims that a slot belongs to a named manager.

The model starts with each manager's real squad at ``start_gameweek``.  From
the following gameweek onward it can hold, make one transfer, or make two
transfers.  Every decision uses the prediction for that gameweek, which was
constructed only from information available through the previous gameweek.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


POSITION_LIMITS = {
    "Goalkeeper": 2,
    "Defender": 5,
    "Midfielder": 5,
    "Forward": 3,
}
FORMATIONS = ((3, 5, 2), (3, 4, 3), (4, 5, 1), (4, 4, 2), (4, 3, 3), (5, 4, 1), (5, 3, 2), (5, 2, 3))
HORIZON_WEIGHTS = (1.0, 0.9, 0.81)
FDR_FACTOR = {1: 1.22, 2: 1.10, 3: 1.0, 4: 0.89, 5: 0.78}


@dataclass(frozen=True)
class SquadState:
    players: tuple[int, ...]
    bank: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--start-gameweek", type=int, default=10)
    parser.add_argument("--manager-limit", type=int, default=100)
    parser.add_argument("--transfer-buffer", type=float, default=1.5)
    parser.add_argument("--data-root", type=Path, default=Path("fpl_data"))
    parser.add_argument(
        "--metrics",
        type=Path,
        default=Path("analysis/fpl_decision_backtest/output/player_week_metrics.csv"),
    )
    parser.add_argument(
        "--odds-predictions",
        type=Path,
        default=Path("analysis/fpl_decision_backtest/output/odds_player_predictions.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/fpl_decision_backtest/output"),
    )
    return parser.parse_args()


def season_label(season: int) -> str:
    return f"{season}/{str(season + 1)[-2:]}"


def load_metrics(
    path: Path,
    data_root: Path,
    season: int,
    odds_predictions_path: Path | None = None,
) -> pd.DataFrame:
    metrics = pd.read_csv(path, low_memory=False)
    metrics = metrics[metrics["season_label"] == season_label(season)].copy()
    numeric = [
        "player_id", "gameweek", "initial_price", "predicted_minutes",
        "predicted_points", "predictive_sd", "total_points", "forecast_eo",
    ]
    for column in numeric:
        metrics[column] = pd.to_numeric(metrics[column], errors="coerce").fillna(0)
    metrics["player_id"] = metrics["player_id"].astype(int)
    metrics["gameweek"] = metrics["gameweek"].astype(int)
    if odds_predictions_path and odds_predictions_path.exists():
        odds = pd.read_csv(odds_predictions_path)
        odds = odds[pd.to_numeric(odds["season"], errors="coerce") == season].copy()
        odds["player_id"] = pd.to_numeric(odds["player_id"], errors="coerce").astype(int)
        odds["gameweek"] = pd.to_numeric(odds["gameweek"], errors="coerce").astype(int)
        metrics = metrics.merge(
            odds[["player_id", "gameweek", "odds_prediction"]],
            on=["player_id", "gameweek"],
            how="left",
            validate="one_to_one",
        )
        metrics["base_predicted_points"] = metrics["predicted_points"]
        metrics["predicted_points"] = metrics["odds_prediction"].fillna(metrics["predicted_points"])
    minute_frames = []
    for gameweek in range(1, 39):
        source = data_root / str(season) / "player_data" / f"public-epl-stats-players-week-{gameweek}.csv"
        minute_frame = pd.read_csv(source, usecols=["id", "minutes"]).rename(
            columns={"id": "player_id", "minutes": "actual_minutes"}
        )
        minute_frame["gameweek"] = gameweek
        minute_frames.append(minute_frame)
    minutes = pd.concat(minute_frames, ignore_index=True)
    metrics = metrics.merge(minutes, on=["player_id", "gameweek"], how="left", validate="one_to_one")
    metrics["actual_minutes"] = pd.to_numeric(metrics["actual_minutes"], errors="coerce").fillna(0)
    return metrics


def load_weekly_squads(data_root: Path, season: int) -> dict[int, list[pd.DataFrame]]:
    squads: dict[int, list[pd.DataFrame]] = {}
    folder = data_root / str(season) / "top_100_teams"
    for gameweek in range(1, 39):
        path = folder / f"public-epl-stats-top100-teams-gw-{gameweek}.csv"
        frame = pd.read_csv(path)
        if len(frame) % 15:
            raise ValueError(f"{path} does not contain complete 15-player squads")
        squads[gameweek] = [frame.iloc[index:index + 15].copy() for index in range(0, len(frame), 15)]
    counts = {len(value) for value in squads.values()}
    if len(counts) != 1:
        raise ValueError(f"Manager count changes across the season: {sorted(counts)}")
    return squads


def normalize_team(value: object) -> str:
    name = re.sub(r"[^a-z0-9]", "", str(value).lower())
    aliases = {
        "tottenham": "spurs",
        "nottinghamforest": "nottmforest",
        "manchesterunited": "manutd",
        "manunited": "manutd",
        "manchestercity": "mancity",
        "newcastleunited": "newcastle",
        "leedsunited": "leeds",
    }
    return aliases.get(name, name)


def load_fixture_factors(cache_dir: Path, season: int) -> dict[tuple[str, int], float]:
    slug = f"{season}-{str(season + 1)[-2:]}"
    fixtures = pd.read_csv(cache_dir / f"{slug}-fixtures.csv")
    teams = pd.read_csv(cache_dir / f"{slug}-teams.csv")
    team_names = teams.set_index("id")["name"]
    factors: dict[tuple[str, int], float] = {}
    for row in fixtures[fixtures["event"].notna()].to_dict("records"):
        gameweek = int(row["event"])
        home = normalize_team(team_names.get(row["team_h"], row["team_h"]))
        away = normalize_team(team_names.get(row["team_a"], row["team_a"]))
        home_factor = FDR_FACTOR.get(int(row.get("team_h_difficulty") or 3), 1.0) * 1.04
        away_factor = FDR_FACTOR.get(int(row.get("team_a_difficulty") or 3), 1.0) * 0.96
        factors[(home, gameweek)] = factors.get((home, gameweek), 0.0) + home_factor
        factors[(away, gameweek)] = factors.get((away, gameweek), 0.0) + away_factor
    return factors


def week_lookup(metrics: pd.DataFrame) -> dict[int, dict[int, dict[str, object]]]:
    result: dict[int, dict[int, dict[str, object]]] = {}
    for gameweek, frame in metrics.groupby("gameweek"):
        result[int(gameweek)] = {
            int(row["player_id"]): row
            for row in frame.to_dict("records")
        }
    return result


def squad_is_legal(players: Iterable[int], lookup: dict[int, dict[str, object]]) -> bool:
    ids = tuple(players)
    if len(ids) != 15 or len(set(ids)) != 15 or any(player not in lookup for player in ids):
        return False
    positions: dict[str, int] = {}
    clubs: dict[str, int] = {}
    for player in ids:
        row = lookup[player]
        position = str(row["position"])
        club = str(row["team"])
        positions[position] = positions.get(position, 0) + 1
        clubs[club] = clubs.get(club, 0) + 1
    return positions == POSITION_LIMITS and max(clubs.values(), default=0) <= 3


def best_lineup(players: Iterable[int], lookup: dict[int, dict[str, object]]) -> tuple[list[int], int, float]:
    by_position: dict[str, list[int]] = {position: [] for position in POSITION_LIMITS}
    for player in players:
        if player in lookup:
            by_position[str(lookup[player]["position"])].append(player)
    for values in by_position.values():
        values.sort(key=lambda player: float(lookup[player]["predicted_points"]), reverse=True)
    goalkeeper = by_position["Goalkeeper"][:1]
    best_ids: list[int] = []
    best_score = -np.inf
    for defenders, midfielders, forwards in FORMATIONS:
        lineup = (
            goalkeeper
            + by_position["Defender"][:defenders]
            + by_position["Midfielder"][:midfielders]
            + by_position["Forward"][:forwards]
        )
        if len(lineup) != 11:
            continue
        score = sum(float(lookup[player]["predicted_points"]) for player in lineup)
        if score > best_score:
            best_ids, best_score = lineup, score
    if not best_ids:
        raise ValueError("No valid starting formation")
    captain = max(best_ids, key=lambda player: float(lookup[player]["predicted_points"]))
    return best_ids, captain, float(best_score + float(lookup[captain]["predicted_points"]))


def frozen_horizon_lookups(
    lookup: dict[int, dict[str, object]],
    fixture_factors: dict[tuple[str, int], float],
    gameweek: int,
) -> list[dict[int, dict[str, object]]]:
    """Move deadline-GW form over known fixtures without using later outcomes."""
    projected = [lookup]
    for offset in range(1, len(HORIZON_WEIGHTS)):
        target_gameweek = gameweek + offset
        target: dict[int, dict[str, object]] = {}
        for player, row in lookup.items():
            team = normalize_team(row["team"])
            current_factor = fixture_factors.get((team, gameweek), 0.0)
            future_factor = fixture_factors.get((team, target_gameweek), 0.0)
            if future_factor <= 0:
                projected_points = 0.0
            elif current_factor <= 0:
                projected_points = float(row["predicted_points"]) * float(np.clip(future_factor, 0.55, 1.65))
            else:
                ratio = future_factor / current_factor
                projected_points = float(row["predicted_points"]) * float(np.clip(ratio, 0.55, 1.65))
            copied = dict(row)
            copied["predicted_points"] = projected_points
            copied["projection_gameweek"] = target_gameweek
            target[player] = copied
        projected.append(target)
    return projected


def horizon_score(
    players: Iterable[int],
    lookups: list[dict[int, dict[str, object]]],
) -> tuple[float, list[int], int, float]:
    total = 0.0
    current_lineup: list[int] = []
    current_captain = 0
    current_expected = 0.0
    for offset, lookup in enumerate(lookups):
        lineup, captain, expected = best_lineup(players, lookup)
        total += HORIZON_WEIGHTS[offset] * expected
        if offset == 0:
            current_lineup, current_captain, current_expected = lineup, captain, expected
    return total, current_lineup, current_captain, current_expected


def realized_normal_points(
    squad: Iterable[int],
    starters: list[int],
    captain: int,
    vice_captain: int,
    bench_order: list[int],
    lookup: dict[int, dict[str, object]],
) -> float:
    starters = list(starters)
    bench = [player for player in bench_order if player in squad and player not in starters]
    bench_goalkeepers = [player for player in bench if lookup[player]["position"] == "Goalkeeper"]
    bench_outfield = [player for player in bench if lookup[player]["position"] != "Goalkeeper"]

    def played(player: int) -> bool:
        return float(lookup[player].get("actual_minutes", 0)) > 0

    def valid_xi(lineup: list[int]) -> bool:
        counts: dict[str, int] = {}
        for player in lineup:
            position = str(lookup[player]["position"])
            counts[position] = counts.get(position, 0) + 1
        return (
            counts.get("Goalkeeper", 0) == 1
            and counts.get("Defender", 0) >= 3
            and counts.get("Midfielder", 0) >= 2
            and counts.get("Forward", 0) >= 1
        )

    for starter in list(starters):
        if played(starter):
            continue
        if lookup[starter]["position"] == "Goalkeeper":
            replacement = next((player for player in bench_goalkeepers if played(player)), None)
            if replacement is not None:
                starters[starters.index(starter)] = replacement
            continue
        for replacement in bench_outfield:
            if replacement in starters or not played(replacement):
                continue
            proposed = [replacement if player == starter else player for player in starters]
            if valid_xi(proposed):
                starters = proposed
                break

    points = sum(float(lookup[player]["total_points"]) for player in starters)
    if played(captain):
        points += float(lookup[captain]["total_points"])
    elif vice_captain in starters and played(vice_captain):
        points += float(lookup[vice_captain]["total_points"])
    return points


def realized_model_points(
    squad: Iterable[int], starters: list[int], captain: int, lookup: dict[int, dict[str, object]]
) -> float:
    vice_captain = max(
        (player for player in starters if player != captain),
        key=lambda player: float(lookup[player]["predicted_points"]),
    )
    bench = sorted(
        (player for player in squad if player not in starters),
        key=lambda player: (
            lookup[player]["position"] != "Goalkeeper",
            float(lookup[player]["predicted_points"]),
        ),
        reverse=True,
    )
    return realized_normal_points(squad, starters, captain, vice_captain, bench, lookup)


def normalized_human_points(squad: pd.DataFrame, lookup: dict[int, dict[str, object]]) -> float:
    ordered = squad.sort_values("position_selected")
    players = [int(player) for player in ordered["element"] if int(player) in lookup]
    starters = [
        int(row["element"])
        for row in ordered.to_dict("records")
        if int(row["position_selected"]) <= 11 and int(row["element"]) in lookup
    ]
    bench = [
        int(row["element"])
        for row in ordered.to_dict("records")
        if int(row["position_selected"]) > 11 and int(row["element"]) in lookup
    ]
    captain_rows = ordered[ordered["is_captain"].astype(bool)]
    vice_rows = ordered[ordered["is_vice_captain"].astype(bool)]
    captain = int(captain_rows.iloc[0]["element"])
    vice_captain = int(vice_rows.iloc[0]["element"])
    return realized_normal_points(players, starters, captain, vice_captain, bench, lookup)


def candidate_pool(
    lookups: list[dict[int, dict[str, object]]], per_position: int = 12
) -> list[int]:
    candidates = []
    lookup = lookups[0]
    frame = pd.DataFrame(lookup.values())
    eligible = frame[frame["predicted_minutes"].astype(float) >= 45].copy()
    eligible["horizon_points"] = eligible["player_id"].map({
        player: sum(
            HORIZON_WEIGHTS[offset] * float(target[player]["predicted_points"])
            for offset, target in enumerate(lookups)
        )
        for player in lookup
    })
    for _, position in eligible.groupby("position"):
        candidates.extend(
            position.nlargest(per_position, "horizon_points")["player_id"].astype(int).tolist()
        )
    return candidates


def transfer_states(
    state: SquadState,
    lookup: dict[int, dict[str, object]],
    pool: list[int] | None = None,
) -> list[tuple[SquadState, list[tuple[int, int]]]]:
    pool = pool or candidate_pool([lookup])
    results: list[tuple[SquadState, list[tuple[int, int]]]] = []
    for player_out in state.players:
        if player_out not in lookup:
            continue
        out_row = lookup[player_out]
        for player_in in pool:
            if player_in in state.players:
                continue
            in_row = lookup[player_in]
            if in_row["position"] != out_row["position"]:
                continue
            bank = state.bank + float(out_row["initial_price"]) - float(in_row["initial_price"])
            if bank < -1e-8:
                continue
            players = tuple(player_in if player == player_out else player for player in state.players)
            if squad_is_legal(players, lookup):
                results.append((SquadState(players, round(bank, 2)), [(player_out, player_in)]))
    return results


def choose_action(
    state: SquadState,
    lookups: list[dict[int, dict[str, object]]],
    free_transfers: int,
    transfer_buffer: float,
) -> tuple[SquadState, list[tuple[int, int]], list[int], int, float, float]:
    lookup = lookups[0]
    hold_objective, hold_lineup, hold_captain, hold_xp = horizon_score(state.players, lookups)
    pool = candidate_pool(lookups)
    choices: list[tuple[float, SquadState, list[tuple[int, int]], list[int], int, float]] = [
        (hold_objective, state, [], hold_lineup, hold_captain, hold_xp)
    ]
    first_moves = transfer_states(state, lookup, pool)
    ranked_first = []
    for next_state, moves in first_moves:
        objective, lineup, captain, expected = horizon_score(next_state.players, lookups)
        utility = objective - transfer_buffer - max(0, 1 - free_transfers) * 4
        ranked_first.append((utility, next_state, moves, lineup, captain, expected))
    choices.extend(ranked_first)

    # A beam keeps the exhaustive second step focused on plausible first moves.
    for _, first_state, first_move, _, _, _ in sorted(ranked_first, reverse=True, key=lambda row: row[0])[:20]:
        first_out, first_in = first_move[0]
        for second_state, second_move in transfer_states(first_state, lookup, pool):
            second_out, second_in = second_move[0]
            if second_out == first_in or second_in == first_out:
                continue
            moves = first_move + second_move
            objective, lineup, captain, expected = horizon_score(second_state.players, lookups)
            utility = objective - (2 * transfer_buffer) - max(0, 2 - free_transfers) * 4
            choices.append((utility, second_state, moves, lineup, captain, expected))

    best = max(choices, key=lambda row: row[0])
    utility, selected_state, moves, lineup, captain, expected = best
    return selected_state, moves, lineup, captain, expected, utility - hold_objective


def replay_manager(
    slot: int,
    squads: dict[int, list[pd.DataFrame]],
    weeks: dict[int, dict[int, dict[str, object]]],
    fixture_factors: dict[tuple[str, int], float],
    start_gameweek: int,
    transfer_buffer: float,
) -> list[dict[str, object]]:
    initial = squads[start_gameweek][slot]
    start_ids = tuple(initial["element"].astype(int).tolist())
    start_lookup = weeks[start_gameweek]
    opening_cost = sum(float(start_lookup[player]["initial_price"]) for player in start_ids)
    state = SquadState(start_ids, max(0.0, round(100.0 - opening_cost, 2)))
    free_transfers = 1
    cumulative_model = 0.0
    cumulative_human = 0.0
    raw_cumulative_model = 0.0
    raw_cumulative_human = 0.0
    # Unbiased internal benchmark: the same starting squad held all season
    # with no transfers, lineup and captain chosen by the same predictions.
    # model-vs-hold isolates the value added (or destroyed) by the transfer
    # engine, free of the cohort's survivorship bias.
    raw_cumulative_hold = 0.0
    rows = []

    # The archived GW10 squad is the initial state. The first counterfactual
    # decision and scored comparison is therefore GW11.
    for gameweek in range(start_gameweek + 1, 39):
        lookup = weeks[gameweek]
        horizon_lookups = frozen_horizon_lookups(lookup, fixture_factors, gameweek)
        state, moves, lineup, captain, expected, gain = choose_action(
            state, horizon_lookups, free_transfers, transfer_buffer
        )
        hit_cost = max(0, len(moves) - free_transfers) * 4
        model_points = realized_model_points(state.players, lineup, captain, lookup) - hit_cost
        hold_squad = [player for player in start_ids if player in lookup]
        hold_lineup, hold_captain, _ = best_lineup(hold_squad, lookup)
        hold_points = realized_model_points(hold_squad, hold_lineup, hold_captain, lookup)
        raw_cumulative_hold += hold_points
        human_squad = squads[gameweek][slot]
        human_points = normalized_human_points(human_squad, lookup)
        chip_values = set(human_squad["active_chip"].dropna().astype(str)) - {"No Chip"}
        comparison_eligible = not chip_values
        raw_cumulative_model += model_points
        raw_cumulative_human += human_points
        if comparison_eligible:
            cumulative_model += model_points
            cumulative_human += human_points
        rows.append({
            "squad_slot": slot + 1,
            "gameweek": gameweek,
            "human_points": round(human_points, 2),
            "model_points": round(model_points, 2),
            "weekly_delta": round(model_points - human_points, 2),
            "cumulative_human": round(cumulative_human, 2),
            "cumulative_model": round(cumulative_model, 2),
            "cumulative_delta": round(cumulative_model - cumulative_human, 2),
            "raw_cumulative_human": round(raw_cumulative_human, 2),
            "raw_cumulative_model": round(raw_cumulative_model, 2),
            "raw_cumulative_delta": round(raw_cumulative_model - raw_cumulative_human, 2),
            "hold_points": round(hold_points, 2),
            "raw_cumulative_hold": round(raw_cumulative_hold, 2),
            "transfer_value_delta": round(raw_cumulative_model - raw_cumulative_hold, 2),
            "comparison_eligible": comparison_eligible,
            "free_transfers_before": free_transfers,
            "transfers": len(moves),
            "hit_cost": hit_cost,
            "predicted_lineup_points": round(expected, 3),
            "predicted_3gw_gain_vs_hold": round(gain, 3),
            "bank": state.bank,
            "captain": str(lookup[captain]["web_name"]),
            "transfer_detail": "; ".join(
                f"{lookup[out_id]['web_name']} -> {lookup[in_id]['web_name']}" for out_id, in_id in moves
            ),
            "human_chip": ", ".join(sorted(chip_values)),
        })
        if moves:
            free_transfers = min(5, max(0, free_transfers - len(moves)) + 1)
        else:
            free_transfers = min(5, free_transfers + 1)
    return rows


def build_summary(weekly: pd.DataFrame, season: int, start_gameweek: int) -> dict[str, object]:
    final = weekly.sort_values("gameweek").groupby("squad_slot", as_index=False).tail(1)
    median_slot = int(final.iloc[(final["cumulative_delta"] - final["cumulative_delta"].median()).abs().argmin()]["squad_slot"])
    return {
        "season": season_label(season),
        "start_gameweek": start_gameweek,
        "end_gameweek": 38,
        "manager_count": int(final.shape[0]),
        "method": {
            "identity": "anonymous stable squad slots from the archived top-100 cohort",
            "lookahead_control": "three-GW player form is frozen at the decision deadline; later realized player outcomes are never used",
            "forecast": "walk-forward player model calibrated with pre-match opening average bookmaker odds",
            "transfer_policy": "three-GW 1.0/0.9/0.81 objective; hold, one transfer, or two transfers; 4-point hits; up to five banked transfers",
            "pricing": "reconstructed season-start prices because weekly prices were not archived",
            "chips": "base-points view strips all chip multipliers and applies one normal captain; chip-excluded view is retained as sensitivity",
            "autosubs": "human and model replay both reconstruct normal autosubs from archived minutes",
        },
        "results": {
            "scoring_view": "all-week base points with normal captain and autosubs",
            "mean_delta": round(float(final["raw_cumulative_delta"].mean()), 2),
            "median_delta": round(float(final["raw_cumulative_delta"].median()), 2),
            "teams_model_beat": int((final["raw_cumulative_delta"] > 0).sum()),
            "teams_tied": int((final["raw_cumulative_delta"] == 0).sum()),
            "teams_model_lost": int((final["raw_cumulative_delta"] < 0).sum()),
            "best_delta": round(float(final["raw_cumulative_delta"].max()), 2),
            "worst_delta": round(float(final["raw_cumulative_delta"].min()), 2),
            "median_example_slot": int(final.iloc[(final["raw_cumulative_delta"] - final["raw_cumulative_delta"].median()).abs().argmin()]["squad_slot"]),
        },
        "transfer_value_results": {
            "benchmark": "paired internal hold: same starting squad held with no transfers, lineup and captain by the same predictions; starting cohort remains ex-post selected",
            "mean_delta": round(float(final["transfer_value_delta"].mean()), 2),
            "median_delta": round(float(final["transfer_value_delta"].median()), 2),
            "paths_transfers_added_value": int((final["transfer_value_delta"] > 0).sum()),
            "paths_tied": int((final["transfer_value_delta"] == 0).sum()),
            "paths_transfers_destroyed_value": int((final["transfer_value_delta"] < 0).sum()),
            "best_delta": round(float(final["transfer_value_delta"].max()), 2),
            "worst_delta": round(float(final["transfer_value_delta"].min()), 2),
        },
        "chip_excluded_results": {
            "mean_delta": round(float(final["cumulative_delta"].mean()), 2),
            "median_delta": round(float(final["cumulative_delta"].median()), 2),
            "teams_model_beat": int((final["cumulative_delta"] > 0).sum()),
            "teams_tied": int((final["cumulative_delta"] == 0).sum()),
            "teams_model_lost": int((final["cumulative_delta"] < 0).sum()),
            "best_delta": round(float(final["cumulative_delta"].max()), 2),
            "worst_delta": round(float(final["cumulative_delta"].min()), 2),
            "median_example_slot": median_slot,
        },
        "weekly_mean": [
            {
                "gameweek": int(gameweek),
                "human_points": round(float(frame["human_points"].mean()), 2),
                "model_points": round(float(frame["model_points"].mean()), 2),
                "cumulative_delta": round(float(frame["raw_cumulative_delta"].mean()), 2),
                "chip_excluded_cumulative_delta": round(float(frame["cumulative_delta"].mean()), 2),
                "eligible_managers": int(frame["comparison_eligible"].sum()),
            }
            for gameweek, frame in weekly.groupby("gameweek")
        ],
    }


def main() -> None:
    args = parse_args()
    metrics = load_metrics(args.metrics, args.data_root, args.season, args.odds_predictions)
    squads = load_weekly_squads(args.data_root, args.season)
    weeks = week_lookup(metrics)
    fixture_factors = load_fixture_factors(
        Path("analysis/fpl_decision_backtest/data/historical_market"), args.season
    )
    available = min(len(squads[args.start_gameweek]), args.manager_limit)
    rows = []
    for slot in range(available):
        rows.extend(replay_manager(
            slot, squads, weeks, fixture_factors, args.start_gameweek, args.transfer_buffer
        ))
    weekly = pd.DataFrame(rows)
    summary = build_summary(weekly, args.season, args.start_gameweek)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"gw{args.start_gameweek}"
    weekly.to_csv(args.output_dir / f"team_replay_{suffix}_weekly.csv", index=False)
    (args.output_dir / f"team_replay_{suffix}_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary["results"], indent=2))


if __name__ == "__main__":
    main()
