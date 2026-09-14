"""Transparent, cached player-level FPL analysis for the decision lab.

The service evaluates the saved inputs from the Excel workbench. It reads the latest
dated pre-deadline input snapshot and performs no network requests, so a page
view can never consume an odds API allowance or introduce post-deadline data.
"""

from __future__ import annotations

import html
import json
import math
import os
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings
from scipy.stats import poisson


POSITION_PRIORS = {
    "GKP": {"start": 0.55, "xg90": 0.00, "xa90": 0.00, "bonus90": 0.10, "goal_points": 10, "cs_points": 4, "dc_threshold": 999, "dc90": 0},
    "DEF": {"start": 0.65, "xg90": 0.05, "xa90": 0.07, "bonus90": 0.10, "goal_points": 6, "cs_points": 4, "dc_threshold": 10, "dc90": 8},
    "MID": {"start": 0.70, "xg90": 0.18, "xa90": 0.17, "bonus90": 0.12, "goal_points": 5, "cs_points": 1, "dc_threshold": 12, "dc90": 6},
    "FWD": {"start": 0.75, "xg90": 0.35, "xa90": 0.12, "bonus90": 0.10, "goal_points": 4, "cs_points": 0, "dc_threshold": 12, "dc90": 4},
}

FDR_GOAL_MEAN = {1: 2.60, 2: 2.10, 3: 1.50, 4: 1.10, 5: 0.75}
DEFAULT_ASSUMPTIONS = {
    "prior_minutes": 450.0,
    "sub_appearance_probability": 0.35,
    "substitute_minutes": 20.0,
    "p60_given_start": 0.95,
    "congestion_minutes_factor": 0.92,
    "assisted_goal_share": 0.85,
    "start_prior_strength": 1.0,
    "gameweek_decay": 0.90,
}


def analysis_output_dir() -> Path:
    configured = os.environ.get("FPL_ANALYSIS_OUTPUT_DIR")
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR).parent / "analysis" / "fpl_decision_backtest" / "output"


def latest_snapshot_path() -> Path:
    candidates = sorted(analysis_output_dir().glob("player_workbench_inputs_*.json"))
    if not candidates:
        raise FileNotFoundError("No player workbench snapshot is available. Run build_workbench_inputs.py first.")
    return candidates[-1]


@lru_cache(maxsize=4)
def _read_snapshot_cached(path: str, modified_ns: int) -> dict[str, Any]:
    del modified_ns  # Included in the key so a replaced snapshot invalidates the cache.
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_latest_snapshot() -> dict[str, Any]:
    path = latest_snapshot_path()
    return _read_snapshot_cached(str(path), path.stat().st_mtime_ns)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _round(value: float, digits: int = 4) -> float:
    return round(value, digits)


def _expected_floor_poisson(rate: float, divisor: int) -> float:
    """E[floor(N/divisor)] via survival probabilities (tail < 1e-12)."""
    if rate <= 0.0:
        return 0.0
    upper = int(poisson.ppf(1.0 - 1e-12, rate))
    return float(poisson.sf(range(divisor - 1, upper, divisor), rate).sum())


def _base_calculation(row: dict[str, Any], assumptions: dict[str, float]) -> dict[str, Any]:
    position = str(row.get("position") or "")
    prior = POSITION_PRIORS[position]
    availability = min(1.0, max(0.0, _number(row.get("availability"))))
    if row.get("opponent") == "Blank" or row.get("market_basis") == "Blank":
        availability = 0.0
    starts = _number(row.get("starts"))
    team_matches = max(0.0, _number(row.get("team_matches")))
    season_minutes = max(0.0, _number(row.get("season_minutes")))
    start_rate = (
        starts + assumptions["start_prior_strength"] * prior["start"]
    ) / max(1.0, team_matches + assumptions["start_prior_strength"])
    start_rate = min(1.0, max(0.0, start_rate))
    p_start = availability * start_rate
    p_sub = availability * (1.0 - start_rate) * assumptions["sub_appearance_probability"]
    minutes_per_start = min(90.0, season_minutes / starts) if starts > 0 else 75.0

    previous_europe = row.get("days_previous_europe")
    next_europe = row.get("days_next_europe")
    congested = (
        previous_europe not in (None, "") and _number(previous_europe, 99.0) <= 3.0
    ) or (
        next_europe not in (None, "") and _number(next_europe, 99.0) <= 4.0
    )
    congestion_factor = assumptions["congestion_minutes_factor"] if congested else 1.0
    expected_minutes = congestion_factor * (
        p_start * minutes_per_start + p_sub * assumptions["substitute_minutes"]
    )
    p60 = p_start * assumptions["p60_given_start"] * congestion_factor
    prior_minutes = assumptions["prior_minutes"]
    denominator = season_minutes + prior_minutes
    xg90 = (_number(row.get("expected_goals")) * 90.0 + prior["xg90"] * prior_minutes) / denominator
    xa90 = (_number(row.get("expected_assists")) * 90.0 + prior["xa90"] * prior_minutes) / denominator
    bonus90 = (_number(row.get("bonus")) * 90.0 + prior["bonus90"] * prior_minutes) / denominator
    dc90 = (_number(row.get("defensive_contribution")) * 90.0 + prior["dc90"] * prior_minutes) / denominator

    fdr = int(_number(row.get("fdr")))
    opponent_fdr = int(_number(row.get("opponent_fdr")))
    venue = row.get("venue")
    fallback_team_lambda = FDR_GOAL_MEAN.get(fdr, 0.0) * (1.03 if venue == "H" else 0.98)
    fallback_opponent_lambda = FDR_GOAL_MEAN.get(opponent_fdr, 0.0) * (0.98 if venue == "H" else 1.03)
    market_team_lambda = row.get("team_lambda_market")
    market_opponent_lambda = row.get("opponent_lambda_market")
    team_lambda = fallback_team_lambda if market_team_lambda in (None, "") else _number(market_team_lambda)
    opponent_lambda = fallback_opponent_lambda if market_opponent_lambda in (None, "") else _number(market_opponent_lambda)

    return {
        **row,
        "availability": availability,
        "congested": congested,
        "congestion_factor": congestion_factor,
        "p_start": p_start,
        "p_sub": p_sub,
        "p60": p60,
        "expected_minutes": expected_minutes,
        "start_minutes": congestion_factor * minutes_per_start,
        "sub_minutes": congestion_factor * assumptions["substitute_minutes"],
        "xg90_shrunk": xg90,
        "xa90_shrunk": xa90,
        "bonus90_shrunk": bonus90,
        "dc90_shrunk": dc90,
        "goal_weight": expected_minutes * xg90 / 90.0,
        "assist_weight": expected_minutes * xa90 / 90.0,
        "team_lambda": team_lambda,
        "opponent_lambda": opponent_lambda,
        "data_basis": "market" if market_team_lambda not in (None, "") else "fdr_proxy",
        "position_prior": prior,
    }


def _fixture_key(row: dict[str, Any]) -> tuple:
    # Legacy snapshots contain one row per player/gameweek without fixture IDs.
    return (str(row.get("team")), int(row.get("gameweek") or 0), row.get("fixture_id"))


def calculate_fixture_snapshot(
    snapshot: dict[str, Any],
    assumptions: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    active_assumptions = {**DEFAULT_ASSUMPTIONS, **(assumptions or {})}
    calculated = [_base_calculation(row, active_assumptions) for row in snapshot.get("rows", [])]
    seen = set()
    for row in calculated:
        identity = (row["player_id"], row["gameweek"], row.get("fixture_id"))
        if identity in seen:
            raise ValueError("Duplicate player fixture; multiple matches require distinct fixture_id values.")
        seen.add(identity)
    goal_totals: dict[tuple, float] = defaultdict(float)
    assist_totals: dict[tuple, float] = defaultdict(float)
    for row in calculated:
        key = _fixture_key(row)
        goal_totals[key] += row["goal_weight"]
        assist_totals[key] += row["assist_weight"]

    final_rows = []
    for row in calculated:
        prior = row["position_prior"]
        key = _fixture_key(row)
        goal_lambda = row["team_lambda"] * row["goal_weight"] / goal_totals[key] if goal_totals[key] else 0.0
        assist_lambda = (
            row["team_lambda"]
            * active_assumptions["assisted_goal_share"]
            * row["assist_weight"]
            / assist_totals[key]
            if assist_totals[key]
            else 0.0
        )
        appearance_xp = row["p_start"] + row["p_sub"] + row["p60"]
        goal_xp = prior["goal_points"] * goal_lambda
        assist_xp = 3.0 * assist_lambda
        clean_sheet_probability = math.exp(-max(0.0, row["opponent_lambda"]))
        clean_sheet_xp = prior["cs_points"] * clean_sheet_probability * row["p60"]
        season_minutes = max(0.0, _number(row.get("season_minutes")))
        # Nonlinear rewards must be calculated conditional on playing, then
        # averaged over start/sub/no-show states, not applied to mean minutes.
        states = ((row["p_start"], row["start_minutes"]), (row["p_sub"], row["sub_minutes"]))
        saves90 = max(0.0, _number(row.get("saves"))) / max(1.0, season_minutes / 90.0)
        save_xp = sum(
            probability * _expected_floor_poisson(saves90 * minutes / 90.0, 3)
            for probability, minutes in states
        ) if row.get("position") == "GKP" else 0.0
        conceded_xp = -sum(
            probability * _expected_floor_poisson(max(0.0, row["opponent_lambda"]) * minutes / 90.0, 2)
            for probability, minutes in states
        ) if row.get("position") in ("GKP", "DEF") else 0.0
        bonus_xp = row["bonus90_shrunk"] * row["expected_minutes"] / 90.0
        dc_xp = 0.0 if prior["dc_threshold"] > 100 else 2.0 * sum(
            probability * float(poisson.sf(prior["dc_threshold"] - 1, max(0.0, row["dc90_shrunk"]) * minutes / 90.0))
            for probability, minutes in states
        )
        card_xp = -(
            _number(row.get("yellow_cards")) + 3.0 * _number(row.get("red_cards"))
        ) * row["expected_minutes"] / max(90.0, season_minutes)
        components = {
            "appearance": appearance_xp,
            "goals": goal_xp,
            "assists": assist_xp,
            "clean_sheet": clean_sheet_xp,
            "goals_conceded": conceded_xp,
            "saves": save_xp,
            "bonus": bonus_xp,
            "defensive_contribution": dc_xp,
            "cards": card_xp,
        }
        expected_points = sum(components.values())
        attack_lambda = goal_lambda + assist_lambda
        return_probability = 0.0
        multiple_return_probability = 0.0
        if row["expected_minutes"] > 0.0:
            for probability, minutes in states:
                conditional_lambda = attack_lambda * minutes / row["expected_minutes"]
                return_probability += probability * -math.expm1(-conditional_lambda)
                multiple_return_probability += probability * float(poisson.sf(1, conditional_lambda))
        ownership = min(1.0, max(0.0, _number(row.get("ownership"))))
        price = max(0.1, _number(row.get("price_m"), 0.1))
        final_rows.append({
            **{key: value for key, value in row.items() if key != "position_prior"},
            "goal_lambda": _round(goal_lambda),
            "assist_lambda": _round(assist_lambda),
            "attack_lambda": _round(attack_lambda),
            "clean_sheet_probability": _round(clean_sheet_probability),
            "return_probability": _round(return_probability),
            "attacking_blank_probability": _round(1.0 - return_probability),
            "multiple_return_probability": _round(multiple_return_probability),
            "expected_points": _round(expected_points),
            "xp_per_m": _round(expected_points / price),
            "differential_upside": _round(expected_points * (1.0 - ownership)),
            "omission_risk": _round(expected_points * ownership),
            "non_start_probability": _round(1.0 - row["p_start"]),
            "components": {name: _round(value) for name, value in components.items()},
        })
    return final_rows


def calculate_snapshot(
    snapshot: dict[str, Any],
    assumptions: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Score matches independently, then return one summary per player/gameweek.

    Expected points add without an independence assumption. Week-level event
    probabilities below assume independent matches (including availability).
    """
    grouped = defaultdict(list)
    for row in calculate_fixture_snapshot(snapshot, assumptions):
        grouped[(row["player_id"], row["gameweek"])].append(row)
    summaries = []
    for matches in grouped.values():
        matches.sort(key=lambda row: (row.get("kickoff_time") or "9999", row.get("fixture_id") or 0))
        first = matches[0]
        summary = {**first, "matches": matches, "fixture_count": sum(row.get("opponent") != "Blank" for row in matches)}
        if len(matches) > 1:
            for field in ("expected_points", "expected_minutes", "team_lambda", "opponent_lambda", "goal_lambda", "assist_lambda", "attack_lambda", "xp_per_m", "differential_upside", "omission_risk"):
                summary[field] = _round(sum(row[field] for row in matches))
            summary["components"] = {name: _round(sum(row["components"][name] for row in matches)) for name in first["components"]}
            # Convolve the probabilities of zero and exactly one return.
            p_zero, p_one = 1.0, 0.0
            for row in matches:
                zero = row["attacking_blank_probability"]
                one = max(0.0, row["return_probability"] - row["multiple_return_probability"])
                p_zero, p_one = p_zero * zero, p_one * zero + p_zero * one
            summary["attacking_blank_probability"] = _round(p_zero)
            summary["return_probability"] = _round(1.0 - p_zero)
            summary["multiple_return_probability"] = _round(max(0.0, 1.0 - p_zero - p_one))
            summary["non_start_probability"] = _round(math.prod(1.0 - row["p_start"] for row in matches))
            summary["p_start"] = 1.0 - summary["non_start_probability"]
            summary["p_sub"] = math.prod(1.0 - row["p_start"] for row in matches) - math.prod(1.0 - row["p_start"] - row["p_sub"] for row in matches)
            summary["p60"] = 1.0 - math.prod(1.0 - row["p60"] for row in matches)
            summary["clean_sheet_probability"] = _round(1.0 - math.prod(1.0 - row["clean_sheet_probability"] for row in matches))
            summary["opponent"] = " / ".join(f"{row['opponent']} ({row['venue']})" for row in matches)
            summary["venue"] = ""
            bases = {row["data_basis"] for row in matches}
            summary["data_basis"] = next(iter(bases)) if len(bases) == 1 else "mixed"
            summary["congested"] = any(row["congested"] for row in matches)
            summary["fixture_id"] = None
        summaries.append(summary)
    return summaries


def player_catalogue(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = snapshot or load_latest_snapshot()
    available_gameweeks = sorted({int(row["gameweek"]) for row in payload.get("rows", [])})
    player_meta: dict[int, dict[str, Any]] = {}
    for row in payload.get("rows", []):
        player_id = int(row["player_id"])
        player_meta.setdefault(player_id, {
            "id": player_id,
            "name": row["player"],
            "label": row["player_label"],
            "team": row["team"],
            "position": row["position"],
            "price_m": _number(row.get("price_m")),
            "ownership": _number(row.get("ownership")),
        })
    return {
        "snapshot_date": payload.get("snapshot_date"),
        "generated_at": payload.get("generated_at"),
        "available_gameweeks": available_gameweeks,
        "players": sorted(player_meta.values(), key=lambda player: (player["name"].lower(), player["team"])),
    }


def build_player_analysis(
    player_ids: list[int],
    gameweek: int | None = None,
    horizon: int = 3,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = snapshot or load_latest_snapshot()
    catalogue = player_catalogue(payload)
    available_gameweeks = catalogue["available_gameweeks"]
    if not available_gameweeks:
        raise ValueError("The player snapshot contains no gameweeks.")
    focus_gameweek = gameweek if gameweek is not None else available_gameweeks[0]
    if focus_gameweek not in available_gameweeks:
        raise ValueError(f"gameweek must be one of {available_gameweeks}")
    horizon = min(max(1, int(horizon)), 3)
    selected_gameweeks = [gw for gw in available_gameweeks if gw >= focus_gameweek][:horizon]
    selected_ids = list(dict.fromkeys(player_ids))[:8]
    if not selected_ids:
        raise ValueError("At least one player_id is required.")

    rows = calculate_snapshot(payload)
    row_lookup = {(int(row["player_id"]), int(row["gameweek"])): row for row in rows}
    catalogue_lookup = {int(player["id"]): player for player in catalogue["players"]}
    missing = [player_id for player_id in selected_ids if player_id not in catalogue_lookup]
    if missing:
        raise ValueError(f"Unknown player_id: {', '.join(map(str, missing))}")

    player_results = []
    for player_id in selected_ids:
        fixtures = [row_lookup[(player_id, gw)] for gw in selected_gameweeks if (player_id, gw) in row_lookup]
        weighted_xp = sum(
            (DEFAULT_ASSUMPTIONS["gameweek_decay"] ** (int(row["gameweek"]) - focus_gameweek)) * row["expected_points"]
            for row in fixtures
        )
        focus = row_lookup.get((player_id, focus_gameweek))
        if focus is None:
            raise ValueError(f"Player {player_id} has no row for gameweek {focus_gameweek}.")
        role = "shield" if focus["ownership"] >= 0.65 else "differential" if focus["ownership"] < 0.10 else "balanced"
        player_results.append({
            **catalogue_lookup[player_id],
            "role": role,
            "focus": focus,
            "fixtures": fixtures,
            "weighted_horizon_xp": _round(weighted_xp),
            "captain_total_xp": _round(2.0 * focus["expected_points"]),
            "triple_captain_total_xp": _round(3.0 * focus["expected_points"]),
            "triple_captain_increment": focus["expected_points"],
        })

    focus_rows = [row for row in rows if int(row["gameweek"]) == focus_gameweek]
    ranking = sorted(focus_rows, key=lambda row: row["expected_points"], reverse=True)
    rank_lookup = {int(row["player_id"]): index + 1 for index, row in enumerate(ranking)}
    for result in player_results:
        result["focus_rank"] = rank_lookup[result["id"]]

    return {
        "meta": {
            "model_version": "workbench-v3-fixture-scoring",
            "input_schema_version": payload.get("schema_version", 1),
            "snapshot_date": payload.get("snapshot_date"),
            "generated_at": payload.get("generated_at"),
            "focus_gameweek": focus_gameweek,
            "horizon": len(selected_gameweeks),
            "gameweeks": selected_gameweeks,
            "player_count": len(catalogue["players"]),
            "data_policy": "Saved pre-deadline snapshot; no network request on page load.",
            "authority": "Decision support. The optimizer is not approved as an autonomous authority.",
        },
        "players": player_results,
        "top_players": [{
            "id": int(row["player_id"]),
            "name": row["player"],
            "team": row["team"],
            "position": row["position"],
            "expected_points": row["expected_points"],
            "ownership": row["ownership"],
            "price_m": row["price_m"],
        } for row in ranking[:10]],
        "assumptions": DEFAULT_ASSUMPTIONS,
        "limitations": [
            "Team goal means use a 1X2-only Poisson fit until totals markets are available.",
            "Gameweeks without market prices use a labelled FDR fallback.",
            "European fixtures are a partial schedule and only alter the editable minutes factor.",
            "Differential and omission indices use headline ownership, not rank-tier effective ownership.",
            "Bonus and defensive-contribution expectations remain approximations.",
            "Save, conceded-goal and defensive-contribution counts use Poisson distributions conditional on start/sub minutes; these distributions are not yet calibrated.",
            "Clean sheets still use a full-match opponent goal mean and a fixed conditional 60-minute probability.",
            "Multi-match gameweek return and non-start probabilities assume independent matches, including availability; persistent injuries can violate this assumption.",
            "Legacy snapshots without fixture IDs cannot recover double fixtures that were omitted when the snapshot was built.",
        ],
    }


def _latex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in text)


def render_player_report_tex(analysis: dict[str, Any]) -> str:
    meta = analysis["meta"]
    title_names = " vs ".join(_latex_escape(player["name"]) for player in analysis["players"])
    rows = []
    for player in analysis["players"]:
        focus = player["focus"]
        rows.append(
            f"{_latex_escape(player['name'])} & {_latex_escape(player['team'])} & "
            f"{focus['expected_points']:.2f} & {focus['expected_minutes']:.1f} & "
            f"{100 * focus['return_probability']:.1f}\\% & {player['weighted_horizon_xp']:.2f} & "
            f"{focus['xp_per_m']:.3f} & {focus['omission_risk']:.2f} \\\\" 
        )
    fixture_sections = []
    for player in analysis["players"]:
        fixture_rows = "\n".join(
            f"{row['gameweek']} & {_latex_escape(row['opponent'])} ({_latex_escape(row['venue'])}) & "
            f"{row['expected_points']:.2f} & {row['goal_lambda']:.3f} & {row['assist_lambda']:.3f} & "
            f"{100 * row['return_probability']:.1f}\\% & {_latex_escape(row['data_basis'])} \\\\" 
            for week in player["fixtures"] for row in week.get("matches", [week])
        )
        fixture_sections.append(f"""
\\subsection*{{{_latex_escape(player['name'])}: fixture path}}
\\begin{{tabularx}}{{\\textwidth}}{{l l r r r r X}}
\\toprule GW & Fixture & xP & $\\lambda_g$ & $\\lambda_a$ & Return & Basis \\\\
\\midrule
{fixture_rows}
\\bottomrule
\\end{{tabularx}}
""")
    summary_rows = "\n".join(rows)
    limitations_tex = "\n".join(
        r"\item " + _latex_escape(item) for item in analysis["limitations"]
    )
    return f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[margin=22mm]{{geometry}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{lmodern,microtype,amsmath,booktabs,tabularx,xcolor,hyperref}}
\\definecolor{{Navy}}{{HTML}}{{132238}}
\\hypersetup{{colorlinks=true,linkcolor=Navy,urlcolor=blue}}
\\setlength{{\\parindent}}{{0pt}}
\\setlength{{\\parskip}}{{0.6em}}
\\begin{{document}}
{{\\Huge\\bfseries\\color{{Navy}} Player Analysis: {title_names}}}\\par
\\vspace{{2mm}}
Snapshot {_latex_escape(meta['snapshot_date'])}; focus GW{meta['focus_gameweek']}; horizon {meta['horizon']} gameweeks.\\par
\\textbf{{Authority:}} {_latex_escape(meta['authority'])}

\\section*{{Decision summary}}
\\begin{{tabularx}}{{\\textwidth}}{{l l r r r r r r}}
\\toprule Player & Team & xP & Mins & Return & 3GW xP & xP/\\pounds m & Omission \\\\
\\midrule
{summary_rows}
\\bottomrule
\\end{{tabularx}}

{''.join(fixture_sections)}

\\section*{{Model}}
Expected points include appearances, goals, assists, clean sheets, saves, goals-conceded deductions, bonus, defensive contributions and cards. Saves use expected completed groups of three; conceded-goal deductions use completed groups of two. Defensive contributions award two points times the probability of reaching the positional threshold. These count distributions are conditional on start/sub minutes.
For each playing state $s$, let $p_s$ be its probability and $\\lambda_s$ its conditional attacking mean. Then
\\[
P(\\text{{return}})=\\sum_s p_s(1-e^{{-\\lambda_s}}), \\qquad
P(\\text{{two or more}})=\\sum_s p_s[1-e^{{-\\lambda_s}}(1+\\lambda_s)].
\\]
The no-appearance state contributes zero returns. The saved workbook uses an earlier formula version; this report uses workbench-v3-fixture-scoring.
Clean-sheet probability is $e^{{-\\lambda_{{opp}}}}$ and is multiplied by the probability of reaching 60 minutes.

\\section*{{Limitations}}
\\begin{{itemize}}
{limitations_tex}
\\end{{itemize}}

\\section*{{Verdict}}
This report is generated from the same saved inputs and scoring implementation as the website. It is a decision aid, not permission for the optimizer to make an automatic transfer.
\\end{{document}}
"""


def render_player_report_html(analysis: dict[str, Any]) -> str:
    meta = analysis["meta"]
    cards = []
    for player in analysis["players"]:
        focus = player["focus"]
        fixture_rows = "".join(
            f"<tr><td>GW{row['gameweek']}</td><td>{html.escape(str(row['opponent']))} {html.escape(str(row['venue']))}</td>"
            f"<td>{row['expected_points']:.2f}</td><td>{row['goal_lambda']:.3f}</td><td>{row['assist_lambda']:.3f}</td>"
            f"<td>{100 * row['return_probability']:.1f}%</td><td>{html.escape(str(row['data_basis']))}</td></tr>"
            for week in player["fixtures"] for row in week.get("matches", [week])
        )
        cards.append(f"""
        <section class="player-card">
          <p class="eyebrow">{html.escape(player['position'])} / {html.escape(player['team'])} / model rank {player['focus_rank']}</p>
          <h2>{html.escape(player['name'])}</h2>
          <div class="metrics">
            <div><span>Focus xP</span><strong>{focus['expected_points']:.2f}</strong></div>
            <div><span>Expected minutes</span><strong>{focus['expected_minutes']:.1f}</strong></div>
            <div><span>Return probability</span><strong>{100 * focus['return_probability']:.1f}%</strong></div>
            <div><span>Multi-return proxy</span><strong>{100 * focus['multiple_return_probability']:.1f}%</strong></div>
            <div><span>Omission risk</span><strong>{focus['omission_risk']:.2f}</strong></div>
            <div><span>Weighted horizon</span><strong>{player['weighted_horizon_xp']:.2f}</strong></div>
          </div>
          <table><thead><tr><th>GW</th><th>Fixture</th><th>xP</th><th>Goal lambda</th><th>Assist lambda</th><th>Return</th><th>Basis</th></tr></thead><tbody>{fixture_rows}</tbody></table>
        </section>
        """)
    limitations = "".join(f"<li>{html.escape(item)}</li>" for item in analysis["limitations"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>FPL player analysis</title><style>
    :root{{--ink:#132238;--blue:#1d4ed8;--line:#cbd5e1;--muted:#64748b;--paper:#f8fafc}}
    *{{box-sizing:border-box}} body{{margin:0;background:#e2e8f0;color:var(--ink);font:15px/1.55 Arial,sans-serif}}
    main{{max-width:1040px;margin:28px auto;background:white;padding:42px;box-shadow:0 20px 55px #64748b33}}
    h1{{font-size:34px;margin:.15rem 0}} h2{{font-size:24px;margin:.15rem 0 1rem}} .eyebrow{{color:var(--blue);font-weight:800;text-transform:uppercase;letter-spacing:.11em;font-size:11px}}
    .meta{{color:var(--muted);margin-bottom:28px}} .player-card{{border-top:5px solid var(--blue);padding:24px 0 32px}}
    .metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:22px}} .metrics div{{background:var(--paper);border:1px solid var(--line);padding:14px}}
    .metrics span,.metrics strong{{display:block}} .metrics span{{color:var(--muted);font-size:12px}} .metrics strong{{font-size:24px;margin-top:3px}}
    table{{width:100%;border-collapse:collapse}} th,td{{text-align:left;border-bottom:1px solid var(--line);padding:9px 7px}} th{{background:var(--ink);color:white;font-size:12px}}
    .note{{background:#eff6ff;border-left:4px solid var(--blue);padding:14px 18px}} a{{color:var(--blue)}}
    @media(max-width:700px){{main{{margin:0;padding:22px}}.metrics{{grid-template-columns:repeat(2,1fr)}}table{{font-size:12px}}}}
    .report-actions{{display:flex;justify-content:flex-end;margin-bottom:18px}} .print-button{{border:0;border-radius:9px;padding:11px 16px;color:#101011;background:#a5ff01;font:inherit;font-weight:800;cursor:pointer}}
    @media print{{body{{background:white}}main{{margin:0;box-shadow:none;max-width:none}}.report-actions{{display:none}}}}
    </style></head><body><main>
    <div class="report-actions"><button class="print-button" onclick="window.print()">Print / Save PDF</button></div>
    <p class="eyebrow">FPL quantitative decision system</p><h1>Dynamic player analysis</h1>
    <p class="meta">Snapshot {html.escape(str(meta['snapshot_date']))} / focus GW{meta['focus_gameweek']} / {meta['horizon']}-gameweek horizon</p>
    <p class="note"><strong>Authority:</strong> {html.escape(meta['authority'])}</p>
    {''.join(cards)}
    <section><h2>How to read it</h2><p>Football value, budget efficiency, differential upside, and omission risk answer different questions. Goal, assist, and clean-sheet events use Poisson means; minutes and availability are modelled separately.</p><ul>{limitations}</ul></section>
    </main></body></html>"""
