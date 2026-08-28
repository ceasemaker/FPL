#!/usr/bin/env python3
"""Dependency-free live FPL squad and one-transfer evaluator.

This is deliberately a transparent phase-two bridge. It reads only public FPL
API data, reconstructs the last public squad, projects a short horizon from FPL
expected points/form/PPG plus fixture difficulty, and evaluates every legal
same-position one-transfer move under protect, balanced, and chase objectives.
"""

from __future__ import annotations

import argparse
import json
import math
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API_ROOT = "https://fantasy.premierleague.com/api"
POSITION = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
FORMATIONS = [(3, 4, 3), (3, 5, 2), (4, 4, 2), (4, 5, 1), (5, 3, 2), (5, 4, 1), (5, 2, 3)]
FDR_FACTOR = {1: 1.25, 2: 1.12, 3: 1.0, 4: 0.86, 5: 0.72}
POSITION_SD = {1: 2.8, 2: 3.0, 3: 3.4, 4: 3.5}
RISK_STRENGTH = {"protect": -0.04, "balanced": 0.0, "chase": 0.025}


@dataclass(frozen=True)
class Player:
    player_id: int
    name: str
    team: int
    position: int
    price: int
    ownership: float
    status: str
    chance: float
    predictions: dict[int, float]
    variances: dict[int, float]


def fetch_json(path: str) -> Any:
    request = urllib.request.Request(
        f"{API_ROOT}/{path.lstrip('/')}",
        headers={"User-Agent": "FPLDecisionBacktest/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def infer_selling_price(purchase_price: int, current_price: int) -> int:
    if current_price >= purchase_price:
        return purchase_price + (current_price - purchase_price) // 2
    return current_price


def build_players(
    bootstrap: dict[str, Any],
    fixtures: list[dict[str, Any]],
    start_gw: int,
    horizon: int,
) -> dict[int, Player]:
    fixture_lookup: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for fixture in fixtures:
        event = fixture.get("event")
        if event is None:
            continue
        fixture_lookup[(int(fixture["team_h"]), int(event))].append(fixture)
        fixture_lookup[(int(fixture["team_a"]), int(event))].append(fixture)

    players: dict[int, Player] = {}
    for raw in bootstrap["elements"]:
        position = int(raw["element_type"])
        team = int(raw["team"])
        ep_next = max(0.0, number(raw.get("ep_next")))
        form = max(0.0, number(raw.get("form")))
        ppg = max(0.0, number(raw.get("points_per_game")))
        price_m = int(raw["now_cost"]) / 10.0
        price_prior = {
            1: 2.0 + 0.25 * max(0.0, price_m - 4.0),
            2: 2.0 + 0.35 * max(0.0, price_m - 4.0),
            3: 2.0 + 0.45 * max(0.0, price_m - 4.5),
            4: 2.5 + 0.40 * max(0.0, price_m - 4.5),
        }[position]
        estimated_games = max(0.0, number(raw.get("minutes")) / 90.0)
        recent_weight = min(0.30, estimated_games / 20.0)
        ep_weight = 0.40
        prior_weight = 1.0 - ep_weight - recent_weight
        recent_performance = 0.60 * ppg + 0.40 * form
        baseline = max(
            0.0,
            prior_weight * price_prior + ep_weight * ep_next + recent_weight * recent_performance,
        )
        raw_chance = raw.get("chance_of_playing_next_round")
        chance = number(raw_chance, 100.0 if raw.get("status") == "a" else 25.0) / 100.0
        chance = min(max(chance, 0.0), 1.0)

        predictions: dict[int, float] = {}
        variances: dict[int, float] = {}
        for gameweek in range(start_gw, start_gw + horizon):
            player_fixtures = fixture_lookup.get((team, gameweek), [])
            if not player_fixtures:
                predicted = 0.0
            elif gameweek == start_gw and ep_next:
                predicted = ep_next
            else:
                predicted = 0.0
                for fixture in player_fixtures:
                    is_home = int(fixture["team_h"]) == team
                    difficulty = int(
                        fixture["team_h_difficulty"] if is_home else fixture["team_a_difficulty"]
                    )
                    home_factor = 1.03 if is_home else 0.98
                    predicted += baseline * FDR_FACTOR.get(difficulty, 1.0) * home_factor
            predicted *= chance
            predictions[gameweek] = round(predicted, 4)
            uncertainty = POSITION_SD[position] * (1.0 + 0.5 * (1.0 - chance))
            variances[gameweek] = round(uncertainty**2, 4)

        players[int(raw["id"])] = Player(
            player_id=int(raw["id"]),
            name=str(raw["web_name"]),
            team=team,
            position=position,
            price=int(raw["now_cost"]),
            ownership=number(raw.get("selected_by_percent")) / 100.0,
            status=str(raw.get("status") or ""),
            chance=chance,
            predictions=predictions,
            variances=variances,
        )
    return players


def lineup_for_week(
    squad: list[int],
    players: dict[int, Player],
    gameweek: int,
    risk_profile: str,
) -> dict[str, Any]:
    risk_strength = RISK_STRENGTH[risk_profile]

    def starter_utility(player_id: int) -> float:
        player = players[player_id]
        mean = player.predictions[gameweek]
        variance_delta = player.variances[gameweek] * (1.0 - 2.0 * player.ownership)
        return mean + risk_strength * variance_delta

    def captain_utility(player_id: int) -> float:
        player = players[player_id]
        mean = player.predictions[gameweek]
        variance_delta = player.variances[gameweek] * (3.0 - 2.0 * player.ownership)
        return mean + risk_strength * variance_delta

    by_position = {
        position: [player_id for player_id in squad if players[player_id].position == position]
        for position in POSITION
    }
    best: dict[str, Any] | None = None
    for defenders, midfielders, forwards in FORMATIONS:
        starters = []
        starters.extend(sorted(by_position[1], key=starter_utility, reverse=True)[:1])
        starters.extend(sorted(by_position[2], key=starter_utility, reverse=True)[:defenders])
        starters.extend(sorted(by_position[3], key=starter_utility, reverse=True)[:midfielders])
        starters.extend(sorted(by_position[4], key=starter_utility, reverse=True)[:forwards])
        if len(starters) != 11:
            continue
        captain = max(starters, key=captain_utility)
        objective = sum(starter_utility(player_id) for player_id in starters) + captain_utility(captain)
        expected_points = (
            sum(players[player_id].predictions[gameweek] for player_id in starters)
            + players[captain].predictions[gameweek]
        )
        bench = [player_id for player_id in squad if player_id not in starters]
        objective += 0.05 * sum(players[player_id].predictions[gameweek] for player_id in bench)
        candidate = {
            "starters": starters,
            "bench": bench,
            "captain": captain,
            "objective": objective,
            "expected_points": expected_points,
        }
        if best is None or candidate["objective"] > best["objective"]:
            best = candidate
    if best is None:
        raise ValueError("Squad cannot produce a legal starting formation")
    return best


def squad_horizon_score(
    squad: list[int],
    players: dict[int, Player],
    start_gw: int,
    horizon: int,
    risk_profile: str,
) -> tuple[float, float, list[dict[str, Any]]]:
    objective = 0.0
    expected_points = 0.0
    lineups = []
    for offset, gameweek in enumerate(range(start_gw, start_gw + horizon)):
        weight = 0.90**offset
        lineup = lineup_for_week(squad, players, gameweek, risk_profile)
        objective += weight * lineup["objective"]
        expected_points += weight * lineup["expected_points"]
        lineups.append(lineup | {"gameweek": gameweek, "weight": weight})
    return objective, expected_points, lineups


def legal_after_transfer(
    squad: list[int],
    player_out: int,
    player_in: int,
    players: dict[int, Player],
) -> bool:
    if players[player_out].position != players[player_in].position:
        return False
    new_squad = [player_in if player_id == player_out else player_id for player_id in squad]
    if len(set(new_squad)) != 15:
        return False
    return max(Counter(players[player_id].team for player_id in new_squad).values()) <= 3


def analyze(entry_id: int, horizon: int) -> dict[str, Any]:
    bootstrap = fetch_json("bootstrap-static/")
    fixtures = fetch_json("fixtures/")
    entry = fetch_json(f"entry/{entry_id}/")
    history = fetch_json(f"entry/{entry_id}/history/")
    current_event = next((event for event in bootstrap["events"] if event.get("is_current")), None)
    if not current_event:
        raise ValueError("No current FPL event")
    current_gw = int(current_event["id"])
    start_gw = current_gw + 1 if current_event.get("finished") else current_gw
    picks = fetch_json(f"entry/{entry_id}/event/{current_gw}/picks/")
    transfers = fetch_json(f"entry/{entry_id}/transfers/")
    players = build_players(bootstrap, fixtures, start_gw, horizon)
    squad = [int(pick["element"]) for pick in picks["picks"]]
    bank = int(picks.get("entry_history", {}).get("bank", entry.get("last_deadline_bank", 0)) or 0)

    latest_purchase = {
        int(transfer["element_in"]): int(transfer["element_in_cost"])
        for transfer in transfers
        if int(transfer["element_in"]) in squad
    }
    raw_players = {int(raw["id"]): raw for raw in bootstrap["elements"]}
    selling_prices: dict[int, int] = {}
    for player_id in squad:
        raw = raw_players[player_id]
        current_price = int(raw["now_cost"])
        purchase_price = latest_purchase.get(
            player_id,
            current_price - int(raw.get("cost_change_start", 0) or 0),
        )
        selling_prices[player_id] = infer_selling_price(purchase_price, current_price)

    profile_results = {}
    for profile in ("protect", "balanced", "chase"):
        base_objective, base_expected, base_lineups = squad_horizon_score(
            squad, players, start_gw, horizon, profile
        )
        moves = []
        for player_out in squad:
            funds = bank + selling_prices[player_out]
            for player_in, candidate in players.items():
                if player_in in squad or candidate.price > funds:
                    continue
                if candidate.status not in {"a", "d"} or candidate.chance < 0.50:
                    continue
                if not legal_after_transfer(squad, player_out, player_in, players):
                    continue
                new_squad = [player_in if player_id == player_out else player_id for player_id in squad]
                new_objective, new_expected, _ = squad_horizon_score(
                    new_squad, players, start_gw, horizon, profile
                )
                moves.append({
                    "out_id": player_out,
                    "out": players[player_out].name,
                    "in_id": player_in,
                    "in": candidate.name,
                    "position": POSITION[candidate.position],
                    "sell_price": selling_prices[player_out] / 10.0,
                    "buy_price": candidate.price / 10.0,
                    "bank_after": (funds - candidate.price) / 10.0,
                    "objective_gain": new_objective - base_objective,
                    "expected_points_gain": new_expected - base_expected,
                    "incoming_ownership": candidate.ownership,
                    "outgoing_ownership": players[player_out].ownership,
                })
        moves.sort(key=lambda item: item["objective_gain"], reverse=True)
        best_move = moves[0] if moves else None
        minimum_gain_to_spend_transfer = 1.5
        profile_results[profile] = {
            "hold_objective": base_objective,
            "hold_expected_points": base_expected,
            "lineups": base_lineups,
            "recommended_action": (
                "roll_transfer"
                if best_move is None or best_move["objective_gain"] < minimum_gain_to_spend_transfer
                else "make_one_transfer"
            ),
            "minimum_gain_to_spend_transfer": minimum_gain_to_spend_transfer,
            "top_one_transfer_moves": moves[:15],
        }

    used_chips = history.get("chips", [])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entry": {
            "id": entry_id,
            "name": entry.get("name"),
            "overall_points": entry.get("summary_overall_points"),
            "overall_rank": entry.get("summary_overall_rank"),
            "bank": bank / 10.0,
            "team_value": number(entry.get("last_deadline_value")) / 10.0,
            "used_chips": used_chips,
        },
        "current_gameweek": current_gw,
        "start_gameweek": start_gw,
        "horizon": horizon,
        "deadline": next(
            (event.get("deadline_time") for event in bootstrap["events"] if event["id"] == start_gw),
            None,
        ),
        "public_squad_warning": (
            "Public picks show the last revealed squad; transfers made since the last deadline "
            "may not be visible yet."
        ),
        "projection_warning": (
            "GW1 provides a very small sample. GW2 uses official FPL ep_next; later weeks use "
            "a transparent form/PPG/fixture-difficulty heuristic, not bookmaker-calibrated xP."
        ),
        "squad": [
            {
                "id": player_id,
                "name": players[player_id].name,
                "position": POSITION[players[player_id].position],
                "current_price": players[player_id].price / 10.0,
                "selling_price": selling_prices[player_id] / 10.0,
                "ownership": players[player_id].ownership,
                "predictions": players[player_id].predictions,
            }
            for player_id in squad
        ],
        "profiles": profile_results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("entry_id", type=int)
    parser.add_argument("--horizon", type=int, default=3, choices=range(1, 6))
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = analyze(args.entry_id, args.horizon)
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
