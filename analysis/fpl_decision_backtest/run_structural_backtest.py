#!/usr/bin/env python3
"""Leakage-safe structural FPL expected-points backtest.

Opening, no-vig bookmaker prices determine team goal intensities.  Player
minutes and event shares are estimated only from matches before the decision
gameweek, then ordinary FPL scoring converts those events into expected points.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize_scalar
from scipy.stats import poisson

from run_backtest import SEASON_LABELS, read_player_season
from run_odds_backtest import (
    EVALUATION_SEASONS,
    download_once,
    football_data_code,
    no_vig_probabilities,
    normalize_team,
    season_slug,
)


POSITIONS = ("Goalkeeper", "Defender", "Midfielder", "Forward")
GOAL_POINTS = {"Goalkeeper": 10, "Defender": 6, "Midfielder": 5, "Forward": 4}
CS_POINTS = {"Goalkeeper": 4, "Defender": 4, "Midfielder": 1, "Forward": 0}
ROLLING_WINDOW = 6
RATE_PRIOR_MINUTES = 450.0
MINUTES_PRIOR_GAMES = 3.0
# The empirical FPL-assist rate is ~0.90 per goal, but replacing this constant
# with the earlier-season empirical rate worsened validation-season top-five
# selection (6.73 -> 6.66) and test-season top-five (5.01 -> 4.90); the lower
# constant acts as useful shrinkage on assist ceilings. Tested 2026-08-28.
ASSISTED_GOAL_RATE = 0.75

EVENT_COLUMNS = (
    "minutes", "starts", "total_points", "expected_goals", "expected_assists",
    "saves", "bonus", "yellow_cards", "red_cards", "own_goals",
    "penalties_missed", "penalties_saved", "defensive_contribution",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("fpl_data"))
    parser.add_argument(
        "--cache-dir", type=Path,
        default=Path("analysis/fpl_decision_backtest/data/historical_market"),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("analysis/fpl_decision_backtest/output"),
    )
    parser.add_argument("--simulation-draws", type=int, default=300)
    return parser.parse_args()


def total_goals_lambda(over25_probability: float) -> float:
    """Invert P(Poisson(lambda) >= 3)."""
    probability = float(np.clip(over25_probability, 1e-6, 1 - 1e-6))
    return float(brentq(lambda value: poisson.sf(2, value) - probability, 0.01, 10.0))


def poisson_match_probabilities(home_lambda: float, away_lambda: float) -> tuple[float, float, float]:
    goals = np.arange(0, 15)
    matrix = np.outer(poisson.pmf(goals, home_lambda), poisson.pmf(goals, away_lambda))
    home = float(np.tril(matrix, -1).sum())
    draw = float(np.trace(matrix))
    away = float(np.triu(matrix, 1).sum())
    total = home + draw + away
    return home / total, draw / total, away / total


def infer_goal_lambdas(
    home_probability: float,
    draw_probability: float,
    away_probability: float,
    over25_probability: float,
) -> tuple[float, float]:
    """Fit independent home/away Poisson means to no-vig 1X2 and O/U prices."""
    total_lambda = total_goals_lambda(over25_probability)

    def loss(home_share: float) -> float:
        predicted = poisson_match_probabilities(
            total_lambda * home_share, total_lambda * (1.0 - home_share)
        )
        observed = (home_probability, draw_probability, away_probability)
        return float(sum((left - right) ** 2 for left, right in zip(predicted, observed)))

    fitted = minimize_scalar(loss, bounds=(0.03, 0.97), method="bounded")
    home_lambda = total_lambda * float(fitted.x)
    return home_lambda, total_lambda - home_lambda


def load_structural_market(season: int, cache_dir: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    slug = season_slug(season)
    code = football_data_code(season)
    github_root = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{slug}"
    odds_path = download_once(
        f"https://www.football-data.co.uk/mmz4281/{code}/E0.csv", cache_dir / f"{code}-E0.csv"
    )
    fixtures_path = download_once(f"{github_root}/fixtures.csv", cache_dir / f"{slug}-fixtures.csv")
    teams_path = download_once(f"{github_root}/teams.csv", cache_dir / f"{slug}-teams.csv")
    odds = pd.read_csv(odds_path)
    fixtures = pd.read_csv(fixtures_path)
    teams = pd.read_csv(teams_path).set_index("id")["name"]
    fixtures = fixtures[fixtures["event"].notna()].copy()
    fixtures["home_key"] = fixtures["team_h"].map(teams).map(normalize_team)
    fixtures["away_key"] = fixtures["team_a"].map(teams).map(normalize_team)
    odds["home_key"] = odds["HomeTeam"].map(normalize_team)
    odds["away_key"] = odds["AwayTeam"].map(normalize_team)
    required = ["AvgH", "AvgD", "AvgA", "Avg>2.5", "Avg<2.5"]
    odds = odds.dropna(subset=required)
    matches = fixtures.merge(
        odds[["home_key", "away_key", *required]], on=["home_key", "away_key"],
        how="inner", validate="one_to_one",
    )
    if len(matches) != 380:
        raise ValueError(f"Only matched {len(matches)}/380 {slug} matches")

    rows: list[dict[str, object]] = []
    fit_errors: list[float] = []
    for match in matches.to_dict("records"):
        home_p, draw_p, away_p = no_vig_probabilities(match["AvgH"], match["AvgD"], match["AvgA"])
        over_p, _ = no_vig_probabilities(match["Avg>2.5"], match["Avg<2.5"])
        home_lambda, away_lambda = infer_goal_lambdas(home_p, draw_p, away_p, over_p)
        fitted = poisson_match_probabilities(home_lambda, away_lambda)
        fit_errors.append(float(np.mean(np.abs(np.asarray(fitted) - [home_p, draw_p, away_p]))))
        shared = {"season": season, "gameweek": int(match["event"]), "fixture_count": 1}
        rows.extend([
            {**shared, "team_key": match["home_key"], "team_lambda": home_lambda,
             "opponent_lambda": away_lambda, "clean_sheet_probability_sum": np.exp(-away_lambda)},
            {**shared, "team_key": match["away_key"], "team_lambda": away_lambda,
             "opponent_lambda": home_lambda, "clean_sheet_probability_sum": np.exp(-home_lambda)},
        ])
    market = pd.DataFrame(rows).groupby(["season", "gameweek", "team_key"], as_index=False).sum()
    return market, {
        "season": season, "matches": len(matches), "team_gameweeks": len(market),
        "double_gameweek_team_rows": len(rows) - len(market),
        "mean_1x2_fit_absolute_error": round(float(np.mean(fit_errors)), 6),
    }


def shifted_sum(grouped: pd.core.groupby.DataFrameGroupBy, column: str) -> pd.Series:
    return grouped[column].transform(
        lambda values: values.shift(1).rolling(ROLLING_WINDOW, min_periods=1).sum()
    ).fillna(0.0)


def add_lagged_event_history(data: pd.DataFrame) -> pd.DataFrame:
    # The 2024/25 archive also contains the short-lived FPL Challenge manager
    # position.  It is not an ordinary squad position and has no FPL event model.
    data = data[data["position"].isin(POSITIONS)].copy()
    data = data.sort_values(["season", "player_id", "gameweek"]).copy()
    for column in EVENT_COLUMNS:
        if column not in data:
            data[column] = 0.0
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0)
    grouped = data.groupby(["season", "player_id"], sort=False)
    data["history_games"] = grouped.cumcount()
    data["history_window"] = data["history_games"].clip(upper=ROLLING_WINDOW)
    data["appearance"] = (data["minutes"] > 0).astype(float)
    data["played_60"] = (data["minutes"] >= 60).astype(float)
    # Three-state minutes history: starts and substitute appearances behave very
    # differently (league-wide roughly 85 vs 18 minutes), so track them apart.
    data["start_appearance"] = (data["starts"] > 0).astype(float)
    data["sub_appearance"] = data["appearance"] - data["start_appearance"]
    data["start_minutes"] = data["minutes"] * data["start_appearance"]
    data["sub_minutes"] = data["minutes"] * data["sub_appearance"]
    data["played_60_start"] = data["played_60"] * data["start_appearance"]
    extra = (
        "appearance", "played_60", "start_appearance", "sub_appearance",
        "start_minutes", "sub_minutes", "played_60_start",
    )
    for column in (*EVENT_COLUMNS, *extra):
        data[f"lag_{column}"] = shifted_sum(grouped, column)
    return data


def prior_table(data: pd.DataFrame, season: int) -> pd.DataFrame:
    past = data[data["season"] < season].copy()
    if past.empty:
        raise ValueError(f"No earlier-season priors available for {season}")
    grouped = past.groupby("position")
    rows = []
    for position in POSITIONS:
        frame = grouped.get_group(position)
        minutes = max(float(frame["minutes"].sum()), 1.0)
        appearances = max(float((frame["minutes"] > 0).sum()), 1.0)
        games = max(float(len(frame)), 1.0)
        started = frame["starts"] > 0
        sub_appearance = (frame["minutes"] > 0) & ~started
        starts_count = max(float(started.sum()), 1.0)
        subs_count = max(float(sub_appearance.sum()), 1.0)
        rows.append({
            "position": position,
            "prior_play": float((frame["minutes"] > 0).mean()),
            "prior_60": float((frame["minutes"] >= 60).mean()),
            "prior_minutes": float(frame["minutes"].mean()),
            "prior_start": float(started.mean()),
            "prior_sub": float(sub_appearance.mean()),
            "prior_mins_start": float(frame.loc[started, "minutes"].sum()) / starts_count,
            "prior_mins_sub": float(frame.loc[sub_appearance, "minutes"].sum()) / subs_count,
            "prior_60_start": float((frame.loc[started, "minutes"] >= 60).mean()) if started.any() else 0.9,
            "prior_xg90": 90.0 * float(frame["expected_goals"].sum()) / minutes,
            "prior_xa90": 90.0 * float(frame["expected_assists"].sum()) / minutes,
            "prior_saves90": 90.0 * float(frame["saves"].sum()) / minutes,
            "prior_dc90": 90.0 * float(frame["defensive_contribution"].sum()) / minutes,
            "prior_bonus_app": float(frame["bonus"].sum()) / appearances,
            "prior_yellow_app": float(frame["yellow_cards"].sum()) / appearances,
            "prior_red_app": float(frame["red_cards"].sum()) / appearances,
            "prior_own_goal_app": float(frame["own_goals"].sum()) / appearances,
            "prior_pen_miss_app": float(frame["penalties_missed"].sum()) / appearances,
            "prior_pen_save_app": float(frame["penalties_saved"].sum()) / appearances,
            "registered_games": games,
        })
    return pd.DataFrame(rows)


def bonus_coefficients(data: pd.DataFrame, season: int) -> dict[str, np.ndarray]:
    """Per-position least-squares bonus model fit only on earlier seasons.

    Features: appearance, 60+ minutes, goals, assists, clean sheets, saves.
    """
    past = data[data["season"] < season]
    coefficients: dict[str, np.ndarray] = {}
    for position in POSITIONS:
        frame = past[past["position"] == position]
        design = np.column_stack([
            (frame["minutes"] > 0).astype(float),
            (frame["minutes"] >= 60).astype(float),
            pd.to_numeric(frame["goals_scored"], errors="coerce").fillna(0.0),
            pd.to_numeric(frame["assists"], errors="coerce").fillna(0.0),
            pd.to_numeric(frame["clean_sheets"], errors="coerce").fillna(0.0),
            frame["saves"],
        ])
        target = frame["bonus"].to_numpy(dtype=float)
        fitted, *_ = np.linalg.lstsq(design, target, rcond=None)
        coefficients[position] = fitted
    return coefficients


def expected_floor_poisson(rate: np.ndarray, divisor: int) -> np.ndarray:
    rate = np.clip(np.nan_to_num(np.asarray(rate, dtype=float), nan=0.0, posinf=25.0), 0.0, 25.0)
    values = np.arange(0, 30)
    probabilities = poisson.pmf(values[None, :], rate[:, None])
    return (probabilities * (values // divisor)[None, :]).sum(axis=1)


def build_structural_predictions(
    data: pd.DataFrame, markets: pd.DataFrame, evaluation_seasons: tuple[int, ...] = EVALUATION_SEASONS
) -> pd.DataFrame:
    outputs: list[pd.DataFrame] = []
    for season in evaluation_seasons:
        frame = data[data["season"] == season].copy()
        frame = frame.merge(prior_table(data, season), on="position", how="left", validate="many_to_one")
        frame["team_key"] = frame["team"].map(normalize_team)
        frame = frame.merge(
            markets[markets["season"] == season],
            on=["season", "gameweek", "team_key"], how="left", validate="many_to_one",
        )
        for column in ("fixture_count", "team_lambda", "opponent_lambda", "clean_sheet_probability_sum"):
            frame[column] = frame[column].fillna(0.0)

        # Three-state minutes model: start / substitute appearance / no appearance,
        # each shrunk toward earlier-season positional priors.
        denominator = frame["history_window"] + MINUTES_PRIOR_GAMES
        frame["p_start"] = (
            frame["lag_start_appearance"] + MINUTES_PRIOR_GAMES * frame["prior_start"]
        ) / denominator
        frame["p_sub"] = (
            frame["lag_sub_appearance"] + MINUTES_PRIOR_GAMES * frame["prior_sub"]
        ) / denominator
        frame["p_play"] = np.clip(frame["p_start"] + frame["p_sub"], 0.0, 1.0)
        frame["minutes_per_start"] = (
            frame["lag_start_minutes"] + MINUTES_PRIOR_GAMES * frame["prior_mins_start"]
        ) / (frame["lag_start_appearance"] + MINUTES_PRIOR_GAMES)
        frame["minutes_per_sub"] = (
            frame["lag_sub_minutes"] + MINUTES_PRIOR_GAMES * frame["prior_mins_sub"]
        ) / (frame["lag_sub_appearance"] + MINUTES_PRIOR_GAMES)
        frame["p_60_given_start"] = np.clip((
            frame["lag_played_60_start"] + MINUTES_PRIOR_GAMES * frame["prior_60_start"]
        ) / (frame["lag_start_appearance"] + MINUTES_PRIOR_GAMES), 0.0, 1.0)
        frame["p_60"] = frame["p_start"] * frame["p_60_given_start"]
        frame["expected_minutes_per_fixture"] = (
            frame["p_start"] * frame["minutes_per_start"]
            + frame["p_sub"] * frame["minutes_per_sub"]
        )
        # Unknown registrations must earn trust; otherwise inactive youth players absorb team xG.
        no_history = frame["history_games"] == 0
        frame.loc[no_history, ["p_start", "p_sub"]] = [0.02, 0.03]
        frame.loc[no_history, ["p_play", "p_60", "expected_minutes_per_fixture"]] = [0.05, 0.02, 3.0]
        frame["p_60"] = np.minimum(frame["p_play"], frame["p_60"])
        frame["expected_minutes"] = frame["expected_minutes_per_fixture"] * frame["fixture_count"]

        rate_denominator = frame["lag_minutes"] + RATE_PRIOR_MINUTES
        for event, prior, output in (
            ("expected_goals", "prior_xg90", "xg90"),
            ("expected_assists", "prior_xa90", "xa90"),
            ("saves", "prior_saves90", "saves90"),
            ("defensive_contribution", "prior_dc90", "dc90"),
        ):
            frame[output] = 90.0 * (
                frame[f"lag_{event}"] + RATE_PRIOR_MINUTES * frame[prior] / 90.0
            ) / rate_denominator

        frame["raw_goal_lambda"] = frame["xg90"] * frame["expected_minutes"] / 90.0
        frame["raw_assist_lambda"] = frame["xa90"] * frame["expected_minutes"] / 90.0
        keys = ["season", "gameweek", "team_key"]
        raw_goal_total = frame.groupby(keys)["raw_goal_lambda"].transform("sum")
        raw_assist_total = frame.groupby(keys)["raw_assist_lambda"].transform("sum")
        frame["goal_lambda"] = np.where(
            raw_goal_total > 0, frame["raw_goal_lambda"] / raw_goal_total * frame["team_lambda"], 0.0
        )
        frame["assist_lambda"] = np.where(
            raw_assist_total > 0,
            frame["raw_assist_lambda"] / raw_assist_total * frame["team_lambda"] * ASSISTED_GOAL_RATE,
            0.0,
        )

        frame["appearance_xp"] = (frame["p_play"] + frame["p_60"]) * frame["fixture_count"]
        frame["goal_xp"] = frame["goal_lambda"] * frame["position"].map(GOAL_POINTS)
        frame["assist_xp"] = 3.0 * frame["assist_lambda"]
        frame["clean_sheet_xp"] = (
            frame["p_60"] * frame["clean_sheet_probability_sum"] * frame["position"].map(CS_POINTS)
        )
        exposure = np.clip(frame["expected_minutes_per_fixture"] / 90.0, 0.0, 1.0)
        conceded_rate = frame["opponent_lambda"] * exposure
        frame["conceded_xp"] = 0.0
        defensive = frame["position"].isin(["Goalkeeper", "Defender"])
        if defensive.any():
            frame.loc[defensive, "conceded_xp"] = -expected_floor_poisson(
                conceded_rate.loc[defensive].to_numpy(), 2
            )
        save_rate = frame["saves90"] * frame["expected_minutes"] / 90.0
        frame["save_xp"] = 0.0
        goalkeepers = frame["position"] == "Goalkeeper"
        if goalkeepers.any():
            frame.loc[goalkeepers, "save_xp"] = expected_floor_poisson(
                save_rate.loc[goalkeepers].to_numpy(), 3
            )

        appearance_denominator = frame["lag_appearance"] + MINUTES_PRIOR_GAMES
        for event, prior, output, points in (
            ("bonus", "prior_bonus_app", "bonus_xp", 1.0),
            ("yellow_cards", "prior_yellow_app", "yellow_xp", -1.0),
            ("red_cards", "prior_red_app", "red_xp", -3.0),
            ("own_goals", "prior_own_goal_app", "own_goal_xp", -2.0),
            ("penalties_missed", "prior_pen_miss_app", "penalty_miss_xp", -2.0),
            ("penalties_saved", "prior_pen_save_app", "penalty_save_xp", 5.0),
        ):
            event_per_appearance = (
                frame[f"lag_{event}"] + MINUTES_PRIOR_GAMES * frame[prior]
            ) / appearance_denominator
            frame[output] = points * event_per_appearance * frame["p_play"] * frame["fixture_count"]

        # Blend the rolling empirical bonus with an event-driven bonus model
        # fit on earlier seasons. Validated 2026-08-28 on 2024/25: the 50/50
        # blend improved weekly top-five realized points (6.73 -> 6.78).
        coefficients = bonus_coefficients(data, season)
        event_bonus = np.zeros(len(frame))
        for position in POSITIONS:
            mask = (frame["position"] == position).to_numpy()
            if not mask.any():
                continue
            sub = frame[frame["position"] == position]
            features = np.nan_to_num(np.column_stack([
                sub["p_play"] * sub["fixture_count"],
                sub["p_60"] * sub["fixture_count"],
                sub["goal_lambda"], sub["assist_lambda"],
                sub["p_60"] * sub["clean_sheet_probability_sum"],
                sub["saves90"] * sub["expected_minutes"] / 90.0,
            ]).astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0)
            # macOS Accelerate BLAS raises spurious FP-flag warnings on small
            # matmuls with clean finite inputs; suppress and assert instead.
            with np.errstate(all="ignore"):
                projected = features @ coefficients[position]
            if not np.all(np.isfinite(projected)):
                raise ValueError(f"non-finite event bonus for {position}")
            event_bonus[mask] = np.clip(projected, 0.0, 3.0 * sub["fixture_count"])
        frame["bonus_xp"] = 0.5 * frame["bonus_xp"] + 0.5 * event_bonus

        # Defensive-contribution points did not exist before 2025/26.
        dc_rate = frame["dc90"] * frame["expected_minutes_per_fixture"] / 90.0
        threshold = np.where(frame["position"] == "Defender", 10, 12)
        eligible_dc = frame["position"].isin(["Defender", "Midfielder", "Forward"])
        frame["defensive_contribution_xp"] = 0.0
        frame.loc[eligible_dc, "defensive_contribution_xp"] = (
            2.0 * poisson.sf(threshold[eligible_dc] - 1, dc_rate[eligible_dc])
            * frame.loc[eligible_dc, "p_play"] * frame.loc[eligible_dc, "fixture_count"]
        )

        component_columns = [
            "appearance_xp", "goal_xp", "assist_xp", "clean_sheet_xp", "conceded_xp",
            "save_xp", "bonus_xp", "yellow_xp", "red_xp", "own_goal_xp",
            "penalty_miss_xp", "penalty_save_xp", "defensive_contribution_xp",
        ]
        frame["structural_xp"] = frame[component_columns].sum(axis=1).clip(lower=-2, upper=20)
        outputs.append(frame)
    return pd.concat(outputs, ignore_index=True)


def add_simulated_risk(frame: pd.DataFrame, draws: int) -> pd.DataFrame:
    """Add reproducible player-level distribution summaries around structural xP."""
    frame = frame.copy()
    p_blank, p_haul, p10, p90 = [], [], [], []
    for row in frame.itertuples(index=False):
        seed = int(row.season * 100000 + row.gameweek * 1000 + row.player_id)
        rng = np.random.default_rng(seed)
        p_start = max(0.0, float(row.p_start))
        p_sub = max(0.0, float(row.p_sub))
        p_none = max(0.0, 1.0 - p_start - p_sub)
        weights = np.asarray([p_none, p_sub, p_start])
        categories = rng.choice(3, size=draws, p=weights / weights.sum())
        minutes = np.choose(
            categories, [0.0, float(row.minutes_per_sub), float(row.minutes_per_start)]
        ) * row.fixture_count
        played_60 = (categories == 2) & (rng.random(draws) < float(row.p_60_given_start))
        minute_mean = max(float(row.expected_minutes), 1e-6)
        event_scale = minutes / minute_mean
        goals = rng.poisson(np.maximum(row.goal_lambda * event_scale, 0.0))
        assists = rng.poisson(np.maximum(row.assist_lambda * event_scale, 0.0))
        score = (categories > 0).astype(float) + played_60.astype(float)
        score += goals * GOAL_POINTS[row.position] + assists * 3.0
        if CS_POINTS[row.position] and row.fixture_count > 0:
            conceded = rng.poisson(max(row.opponent_lambda, 0.0), size=draws)
            score += played_60 * (conceded == 0) * CS_POINTS[row.position]
            if row.position in ("Goalkeeper", "Defender"):
                score -= (categories > 0) * (conceded // 2)
        if row.position == "Goalkeeper":
            saves = rng.poisson(np.maximum(row.saves90 * minutes / 90.0, 0.0))
            score += saves // 3
        # Low-frequency and BPS components are retained at their conditional expectation.
        misc = (
            row.bonus_xp + row.yellow_xp + row.red_xp + row.own_goal_xp
            + row.penalty_miss_xp + row.penalty_save_xp + row.defensive_contribution_xp
        )
        score += misc
        p_blank.append(float(np.mean(score <= 2.0)))
        p_haul.append(float(np.mean(score >= 10.0)))
        p10.append(float(np.quantile(score, 0.10)))
        p90.append(float(np.quantile(score, 0.90)))
    frame["blank_probability"] = p_blank
    frame["haul_probability"] = p_haul
    frame["points_p10"] = p10
    frame["points_p90"] = p90
    return frame


def _fit_platt(probabilities: np.ndarray, outcomes: np.ndarray) -> tuple[float, float]:
    """Fit a two-parameter logistic recalibration on the logit scale."""
    from scipy.optimize import minimize

    logits = np.log(np.clip(probabilities, 1e-4, 1 - 1e-4) / (1 - np.clip(probabilities, 1e-4, 1 - 1e-4)))

    def negative_log_likelihood(params: np.ndarray) -> float:
        calibrated = 1.0 / (1.0 + np.exp(-(params[0] + params[1] * logits)))
        calibrated = np.clip(calibrated, 1e-9, 1 - 1e-9)
        return float(-np.mean(outcomes * np.log(calibrated) + (1 - outcomes) * np.log(1 - calibrated)))

    fitted = minimize(negative_log_likelihood, np.array([0.0, 1.0]), method="Nelder-Mead")
    return float(fitted.x[0]), float(fitted.x[1])


def _apply_platt(probabilities: np.ndarray, intercept: float, slope: float) -> np.ndarray:
    clipped = np.clip(probabilities, 1e-4, 1 - 1e-4)
    logits = np.log(clipped / (1 - clipped))
    return 1.0 / (1.0 + np.exp(-(intercept + slope * logits)))


def calibrate_probabilities(
    frame: pd.DataFrame, calibration_season: int = 2024
) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    """Platt-scale simulated blank/haul probabilities per position.

    Calibration parameters are fit on the validation season only, then applied
    everywhere, so the later test season stays untouched by fitting.
    """
    frame = frame.copy()
    frame["blank_actual"] = (frame["total_points"] <= 2).astype(float)
    frame["haul_actual"] = (frame["total_points"] >= 10).astype(float)
    summary: dict[str, dict[str, float]] = {}
    for outcome in ("blank", "haul"):
        raw_column = f"{outcome}_probability"
        calibrated_column = f"{outcome}_probability_calibrated"
        frame[calibrated_column] = frame[raw_column]
        for position in POSITIONS:
            fit_rows = frame[(frame["season"] == calibration_season) & (frame["position"] == position)]
            if len(fit_rows) < 100:
                continue
            intercept, slope = _fit_platt(
                fit_rows[raw_column].to_numpy(), fit_rows[f"{outcome}_actual"].to_numpy()
            )
            mask = frame["position"] == position
            frame.loc[mask, calibrated_column] = _apply_platt(
                frame.loc[mask, raw_column].to_numpy(), intercept, slope
            )
        for season, label in SEASON_LABELS.items():
            rows = frame[frame["season"] == season]
            if rows.empty:
                continue
            actual = rows[f"{outcome}_actual"].to_numpy()
            summary[f"{outcome}_{label}"] = {
                "actual_rate": round(float(actual.mean()), 5),
                "raw_mean": round(float(rows[raw_column].mean()), 5),
                "calibrated_mean": round(float(rows[calibrated_column].mean()), 5),
                "raw_brier": round(float(np.mean((rows[raw_column] - actual) ** 2)), 5),
                "calibrated_brier": round(float(np.mean((rows[calibrated_column] - actual) ** 2)), 5),
            }
    frame = frame.drop(columns=["blank_actual", "haul_actual"])
    return frame, summary


def score_models(predictions: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    ridge = pd.read_csv(output_dir / "odds_player_predictions.csv").rename(
        columns={"odds_prediction": "ridge_xp"}
    )
    joined = predictions.merge(ridge, on=["season", "gameweek", "player_id"], how="inner")
    # The ridge file already contains exactly its decision-player population,
    # so the inner join gives both models the same player-weeks.

    # Realized three-gameweek value of holding a player picked at gameweek G:
    # points(G) + 0.9 * points(G+1) + 0.81 * points(G+2), matching the user's
    # standard decision horizon. A player disappearing from the population
    # contributes zero, but GW37/38 are censored because the season itself has
    # no complete three-week outcome.
    actual_lookup = joined.set_index(["season", "player_id", "gameweek"])["total_points"]
    horizon_weights = (1.0, 0.9, 0.81)
    future = np.zeros(len(joined))
    keys = joined[["season", "player_id", "gameweek"]].to_numpy()
    for step, weight in enumerate(horizon_weights):
        shifted = pd.MultiIndex.from_arrays(
            [keys[:, 0], keys[:, 1], keys[:, 2] + step]
        )
        future += weight * actual_lookup.reindex(shifted).fillna(0.0).to_numpy()
    last_gameweek = joined.groupby("season")["gameweek"].transform("max")
    joined["realized_3gw"] = np.where(
        joined["gameweek"] + len(horizon_weights) - 1 <= last_gameweek,
        future,
        np.nan,
    )

    def top5_3gw_utility(frame: pd.DataFrame, column: str) -> float:
        frame = frame.dropna(subset=["realized_3gw"])
        return float(np.mean([
            week.nlargest(5, column)["realized_3gw"].mean()
            for _, week in frame.groupby("gameweek")
        ]))

    # Choose the blend on 2024/25 only, using three-gameweek squad utility
    # rather than one-week MAE; 2025/26 stays untouched as the test season.
    validation = joined[joined["season"] == 2024].copy()
    weights = np.linspace(0, 1, 21)
    utilities = {}
    for weight in weights:
        validation["candidate_xp"] = (
            weight * validation["structural_xp"] + (1 - weight) * validation["ridge_xp"]
        )
        utilities[float(weight)] = top5_3gw_utility(validation, "candidate_xp")
    structural_weight = max(utilities, key=utilities.get)
    joined["hybrid_xp"] = (
        structural_weight * joined["structural_xp"] + (1 - structural_weight) * joined["ridge_xp"]
    )

    def ndcg_at_k(week: pd.DataFrame, column: str, k: int = 10) -> float:
        gains = week["total_points"].clip(lower=0.0)
        discounts = 1.0 / np.log2(np.arange(2, k + 2))
        predicted = gains.loc[week[column].nlargest(k).index].to_numpy()
        ideal = gains.nlargest(k).to_numpy()
        ideal_dcg = float((ideal * discounts[: len(ideal)]).sum())
        if ideal_dcg <= 0:
            return 1.0
        return float((predicted * discounts[: len(predicted)]).sum()) / ideal_dcg

    models = ("ridge_xp", "structural_xp", "hybrid_xp")
    season_rows, weekly_rows = [], []
    for season, frame in joined.groupby("season"):
        row: dict[str, object] = {
            "season": SEASON_LABELS[int(season)], "player_gameweeks": len(frame),
            "structural_weight": structural_weight,
        }
        for model in models:
            row[f"{model}_mae"] = float(np.abs(frame["total_points"] - frame[model]).mean())
            row[f"{model}_rmse"] = float(np.sqrt(np.mean((frame["total_points"] - frame[model]) ** 2)))
            row[f"{model}_correlation"] = float(frame["total_points"].corr(frame[model]))
        season_rows.append(row)
        for gameweek, week in frame.groupby("gameweek"):
            best_actual = float(week["total_points"].max())
            weekly_rows.append({
                "season": SEASON_LABELS[int(season)], "gameweek": int(gameweek),
                **{f"{model}_mae": float(np.abs(week["total_points"] - week[model]).mean())
                   for model in models},
                **{f"{model}_top5_points": float(week.nlargest(5, model)["total_points"].mean())
                   for model in models},
                **{f"{model}_top5_3gw": float(week.nlargest(5, model)["realized_3gw"].mean())
                   for model in models},
                **{f"{model}_ndcg10": ndcg_at_k(week, model) for model in models},
                # Captain regret: best realized score minus the realized score
                # of the player the model would have captained.
                **{f"{model}_captain_regret": best_actual
                   - float(week.loc[week[model].idxmax(), "total_points"])
                   for model in models},
            })
    return pd.DataFrame(season_rows), pd.DataFrame(weekly_rows), structural_weight


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    player_frames, market_frames, coverage = [], [], []
    for season in SEASON_LABELS:
        player_frames.append(read_player_season(args.data_root, season))
        market, details = load_structural_market(season, args.cache_dir)
        market_frames.append(market)
        coverage.append(details)
    players = add_lagged_event_history(pd.concat(player_frames, ignore_index=True))
    markets = pd.concat(market_frames, ignore_index=True)
    predictions = build_structural_predictions(players, markets)
    predictions = add_simulated_risk(predictions, args.simulation_draws)
    predictions, calibration_summary = calibrate_probabilities(predictions)
    comparison, weekly, weight = score_models(predictions, args.output_dir)
    columns = [
        "season", "gameweek", "player_id", "web_name", "team", "position", "total_points",
        "expected_minutes", "p_play", "p_start", "p_sub", "p_60", "team_lambda", "opponent_lambda",
        "goal_lambda", "assist_lambda", "structural_xp", "blank_probability",
        "haul_probability", "blank_probability_calibrated", "haul_probability_calibrated",
        "points_p10", "points_p90", "appearance_xp", "goal_xp",
        "assist_xp", "clean_sheet_xp", "conceded_xp", "save_xp", "bonus_xp",
        "defensive_contribution_xp",
    ]
    predictions[columns].to_csv(args.output_dir / "structural_player_predictions.csv", index=False)
    comparison.to_csv(args.output_dir / "structural_model_summary.csv", index=False)
    weekly.to_csv(args.output_dir / "structural_weekly_summary.csv", index=False)
    test = comparison[comparison["season"] == "2025/26"].iloc[0]
    test_weekly = weekly[weekly["season"] == "2025/26"]
    ridge_top5 = float(test_weekly["ridge_xp_top5_points"].mean())
    hybrid_top5 = float(test_weekly["hybrid_xp_top5_points"].mean())
    ridge_top5_3gw = float(test_weekly["ridge_xp_top5_3gw"].mean())
    hybrid_top5_3gw = float(test_weekly["hybrid_xp_top5_3gw"].mean())
    ridge_ndcg = float(test_weekly["ridge_xp_ndcg10"].mean())
    hybrid_ndcg = float(test_weekly["hybrid_xp_ndcg10"].mean())
    ridge_regret = float(test_weekly["ridge_xp_captain_regret"].mean())
    hybrid_regret = float(test_weekly["hybrid_xp_captain_regret"].mean())
    accepted = bool(
        test["hybrid_xp_mae"] < test["ridge_xp_mae"]
        and test["hybrid_xp_correlation"] >= test["ridge_xp_correlation"]
        and hybrid_top5 >= ridge_top5
        and hybrid_top5_3gw >= ridge_top5_3gw
    )
    manifest = {
        "method": {
            "goal_model": "independent Poisson calibrated to no-vig opening 1X2 and over/under 2.5 odds",
            "player_model": "six-match lagged xG/xA with earlier-season positional priors",
            "minutes_model": "three-state (start/substitute/none) from lagged starts with positional priors; player-specific minutes per start and per substitute appearance",
            "scoring": "ordinary FPL scoring; chips excluded; 2025/26 defensive contributions included",
            "bonus_model": "50/50 blend of rolling empirical bonus and per-position event-driven least-squares bonus fit on earlier seasons",
            "risk": f"deterministic-seeded Monte Carlo ({args.simulation_draws} draws/player-week); blank/haul Platt-calibrated per position on 2024/25 only",
            "lookahead_control": "all player inputs end at GW-1; priors use earlier seasons only",
        },
        "coverage": coverage,
        "validation_selected_structural_weight": weight,
        "validation_selection_criterion": "three-gameweek weighted top-five realized utility (weights 1.0/0.9/0.81) on 2024/25",
        "probability_calibration": calibration_summary,
        "season_results": json.loads(comparison.round(5).to_json(orient="records")),
        "authority_gate": {
            "accepted_for_optimizer": accepted,
            "rule": "on the 2025/26 evaluation season, hybrid must beat ridge MAE and not reduce correlation, top-five realized points, or complete-horizon three-gameweek top-five utility",
            "test_ridge_mae": round(float(test["ridge_xp_mae"]), 5),
            "test_hybrid_mae": round(float(test["hybrid_xp_mae"]), 5),
            "test_ridge_correlation": round(float(test["ridge_xp_correlation"]), 5),
            "test_hybrid_correlation": round(float(test["hybrid_xp_correlation"]), 5),
            "test_ridge_top5_points": round(ridge_top5, 5),
            "test_hybrid_top5_points": round(hybrid_top5, 5),
            "test_ridge_top5_3gw": round(ridge_top5_3gw, 5),
            "test_hybrid_top5_3gw": round(hybrid_top5_3gw, 5),
            "test_ridge_ndcg10": round(ridge_ndcg, 5),
            "test_hybrid_ndcg10": round(hybrid_ndcg, 5),
            "test_ridge_captain_regret": round(ridge_regret, 5),
            "test_hybrid_captain_regret": round(hybrid_regret, 5),
        },
    }
    (args.output_dir / "structural_backtest_summary.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest["authority_gate"], indent=2))


if __name__ == "__main__":
    main()
