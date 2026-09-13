#!/usr/bin/env python3
"""Build flat, auditable inputs for the current-player Excel workbench.

The command deliberately performs no network requests. It reads dated FPL,
market and European-schedule snapshots from ``data/current_market`` so that a
workbook can always be reproduced from the same pre-deadline information.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


POSITION = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_team(value: str | None) -> str:
    value = (value or "").lower()
    replacements = {
        "manchester city": "man city",
        "manchester utd": "man utd",
        "manchester united": "man utd",
        "coventry city": "coventry",
        "hull city": "hull",
        "ipswich town": "ipswich",
        "nottingham": "nottm forest",
        "nottingham forest": "nottm forest",
        "nott'm forest": "nottm forest",
        "tottenham": "spurs",
        "tottenham hotspur": "spurs",
        "newcastle utd": "newcastle",
    }
    value = replacements.get(value.strip(), value)
    return re.sub(r"[^a-z0-9]", "", value)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_inputs(snapshot_date: str, start_gameweek: int, horizon: int, data_dir: Path) -> dict[str, Any]:
    bootstrap_path = data_dir / f"fpl-bootstrap-{snapshot_date}.json"
    fixtures_path = data_dir / f"fpl-fixtures-{snapshot_date}.json"
    odds_path = data_dir / f"premier-league-gw{start_gameweek}-gw{start_gameweek + 1}-odds-{snapshot_date}.json"
    european_path = data_dir / f"champions-league-schedule-odds-{snapshot_date}.json"

    bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
    odds_payload = json.loads(odds_path.read_text(encoding="utf-8"))
    european_payload = json.loads(european_path.read_text(encoding="utf-8"))

    teams = {int(team["id"]): team for team in bootstrap["teams"]}
    team_by_normalized_name = {
        _normalize_team(team["name"]): int(team_id) for team_id, team in teams.items()
    }
    team_by_normalized_name.update({
        _normalize_team(team["short_name"]): int(team_id) for team_id, team in teams.items()
    })

    odds_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for market in odds_payload.get("fixtures", []):
        home, away = market["name"].split(" - ", 1)
        odds_lookup[(_normalize_team(home), _normalize_team(away))] = market

    european_by_team: dict[int, list[datetime]] = {team_id: [] for team_id in teams}
    for event in european_payload.get("fixtures", []):
        kickoff = _parse_datetime(event["start_utc"])
        home, away = event["name"].split(" - ", 1)
        for name in (home, away):
            team_id = team_by_normalized_name.get(_normalize_team(name))
            if team_id is not None:
                european_by_team[team_id].append(kickoff)

    fixture_lookup = defaultdict(list)
    completed_matches = defaultdict(int)
    for fixture in fixtures:
        gameweek = fixture.get("event")
        if gameweek is None:
            continue
        for team_id in (int(fixture["team_h"]), int(fixture["team_a"])):
            fixture_lookup[(team_id, int(gameweek))].append(fixture)
            if fixture.get("finished") and int(gameweek) < start_gameweek:
                completed_matches[team_id] += 1

    players = []
    rows = []
    for raw in bootstrap["elements"]:
        if int(raw.get("element_type") or 0) not in POSITION or raw.get("removed"):
            continue
        player_id = int(raw["id"])
        team_id = int(raw["team"])
        team = teams[team_id]
        player_label = f"{raw['web_name']} — {team['short_name']} ({player_id})"
        players.append({"player_label": player_label, "player_id": player_id})

        raw_chance = raw.get("chance_of_playing_next_round")
        if raw_chance is None:
            availability = 1.0 if raw.get("status") == "a" else 0.25
        else:
            availability = min(max(_number(raw_chance) / 100.0, 0.0), 1.0)

        for gameweek in range(start_gameweek, start_gameweek + horizon):
            scheduled = sorted(fixture_lookup.get((team_id, gameweek), []), key=lambda item: (item.get("kickoff_time") or "9999", int(item["id"])))
            for fixture in scheduled or [None]:
                if fixture is None:
                    opponent = "Blank"
                    venue = "—"
                    fdr = 0
                    opponent_fdr = 0
                    fixture_kickoff = None
                    market = None
                else:
                    is_home = int(fixture["team_h"]) == team_id
                    opponent_id = int(fixture["team_a"] if is_home else fixture["team_h"])
                    opponent = teams[opponent_id]["short_name"]
                    venue = "H" if is_home else "A"
                    fdr = int(fixture["team_h_difficulty"] if is_home else fixture["team_a_difficulty"])
                    opponent_fdr = int(fixture["team_a_difficulty"] if is_home else fixture["team_h_difficulty"])
                    fixture_kickoff = _parse_datetime(fixture["kickoff_time"]) if fixture.get("kickoff_time") else None
                    key = (
                        _normalize_team(teams[int(fixture["team_h"])]["name"]),
                        _normalize_team(teams[int(fixture["team_a"])]["name"]),
                    )
                    market = odds_lookup.get(key)

                days_previous_europe = None
                days_next_europe = None
                if fixture_kickoff is not None:
                    previous = [dt for dt in european_by_team.get(team_id, []) if dt < fixture_kickoff]
                    following = [dt for dt in european_by_team.get(team_id, []) if dt > fixture_kickoff]
                    if previous:
                        days_previous_europe = (fixture_kickoff - max(previous)).total_seconds() / 86400.0
                    if following:
                        days_next_europe = (min(following) - fixture_kickoff).total_seconds() / 86400.0

                if market is not None and fixture is not None:
                    is_home = int(fixture["team_h"]) == team_id
                    team_lambda = market["home_goal_lambda_1x2_fit"] if is_home else market["away_goal_lambda_1x2_fit"]
                    opponent_lambda = market["away_goal_lambda_1x2_fit"] if is_home else market["home_goal_lambda_1x2_fit"]
                    market_basis = "1X2 Poisson fit"
                    source_url = market["event_url"]
                else:
                    team_lambda = None
                    opponent_lambda = None
                    market_basis = "FDR proxy" if fixture is not None else "Blank"
                    source_url = "https://fantasy.premierleague.com/api/fixtures/"

                rows.append({
                    "row_key": f"{player_id}|{gameweek}|{fixture['id'] if fixture else 'blank'}",
                    "fixture_id": int(fixture["id"]) if fixture else None,
                    "kickoff_time": fixture.get("kickoff_time") if fixture else None,
                    "player_label": player_label,
                    "player_id": player_id,
                    "player": raw["web_name"],
                    "position": POSITION[int(raw["element_type"])],
                    "team": team["short_name"],
                    "gameweek": gameweek,
                    "opponent": opponent,
                    "venue": venue,
                    "fdr": fdr,
                    "opponent_fdr": opponent_fdr,
                    "price_m": _number(raw.get("now_cost")) / 10.0,
                    "ownership": _number(raw.get("selected_by_percent")) / 100.0,
                    "status": raw.get("status") or "",
                    "availability": availability,
                    "season_minutes": int(raw.get("minutes") or 0),
                    "starts": int(raw.get("starts") or 0),
                    "team_matches": completed_matches[team_id],
                    "total_points": int(raw.get("total_points") or 0),
                    "form": _number(raw.get("form")),
                    "points_per_game": _number(raw.get("points_per_game")),
                    "expected_goals": _number(raw.get("expected_goals")),
                    "expected_assists": _number(raw.get("expected_assists")),
                    "bonus": int(raw.get("bonus") or 0),
                    "saves": int(raw.get("saves") or 0),
                    "yellow_cards": int(raw.get("yellow_cards") or 0),
                    "red_cards": int(raw.get("red_cards") or 0),
                    "defensive_contribution": int(raw.get("defensive_contribution") or 0),
                    "penalties_order": raw.get("penalties_order"),
                    "set_piece_order": raw.get("corners_and_indirect_freekicks_order"),
                    "team_lambda_market": team_lambda,
                    "opponent_lambda_market": opponent_lambda,
                    "market_basis": market_basis,
                    "days_previous_europe": days_previous_europe,
                    "days_next_europe": days_next_europe,
                    "news": raw.get("news") or "",
                    "source_url": source_url,
                })

    return {
        "schema_version": 2,
        "row_granularity": "player_fixture",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": snapshot_date,
        "start_gameweek": start_gameweek,
        "horizon": horizon,
        "players": sorted(players, key=lambda item: item["player_label"].lower()),
        "rows": rows,
        "sources": {
            "fpl_bootstrap": str(bootstrap_path),
            "fpl_fixtures": str(fixtures_path),
            "premier_league_odds": str(odds_path),
            "european_schedule": str(european_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-date", required=True)
    parser.add_argument("--start-gameweek", type=int, required=True)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "current_market",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_inputs(args.snapshot_date, args.start_gameweek, args.horizon, args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"players": len(payload["players"]), "rows": len(payload["rows"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
