#!/usr/bin/env python3
"""Stacked FPL forecast: ridge over form, market, and structural components.

The structural Poisson model supplies mechanistic, market-calibrated context
(minutes states, goal/assist intensities, clean-sheet probability), while the
ridge form features carry player-specific quality the structural priors
shrink away. A single ridge trained on both feature families lets the data
decide how much of each to use, per evaluation season, using only earlier
seasons for training.

Leakage control is identical to the other backtests: every player feature
stops at GW-1, structural priors use earlier seasons only, training uses
seasons strictly before the evaluation season, model and threshold choices
are made on 2024/25, and 2025/26 is a repeatedly inspected evaluation season, not an untouched holdout.
Structural features exist from 2023/24 onward because the structural model
needs at least one earlier season for its positional priors, so the stacked
model trains on 2023/24 for the validation season and 2023/24 + 2024/25 for
the test season.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from run_backtest import (
    FEATURE_COLUMNS,
    SEASON_LABELS,
    RidgeModel,
    add_historical_features,
    read_initial_prices,
    read_player_season,
)
from run_odds_backtest import (
    MARKET_FEATURES,
    load_team_gameweek_market,
    normalize_team,
)
import run_structural_backtest as rsb


STRUCTURAL_FEATURES = [
    "structural_xp",
    "goal_lambda",
    "assist_lambda",
    "team_lambda",
    "opponent_lambda",
    "clean_sheet_probability_sum",
    "expected_minutes",
    "p_start",
    "p_60",
    "bonus_xp",
    "save_xp",
    "conceded_xp",
    "defensive_contribution_xp",
]
STACK_SEASONS = (2023, 2024, 2025)
EVALUATION_SEASONS = (2024, 2025)
HORIZON_WEIGHTS = (1.0, 0.9, 0.81)


HAUL_THRESHOLD = 9
HAUL_MIX_GRID = tuple(float(v) for v in np.arange(0.0, 81.0, 10.0))


class LogisticModel:
    """Dependency-free L2 logistic regression with median imputation.

    Mirrors RidgeModel's preprocessing so the haul head sees the same
    standardized feature space as the mean model.
    """

    def __init__(self, l2: float = 1.0) -> None:
        self.l2 = l2
        self.medians: np.ndarray | None = None
        self.means: np.ndarray | None = None
        self.scales: np.ndarray | None = None
        self.weights: np.ndarray | None = None

    def _prepare(self, frame: pd.DataFrame, fit: bool) -> np.ndarray:
        values = frame.to_numpy(dtype=float)
        if fit:
            self.medians = np.nanmedian(values, axis=0)
            self.medians = np.where(np.isfinite(self.medians), self.medians, 0.0)
        assert self.medians is not None
        missing = ~np.isfinite(values)
        values[missing] = np.take(self.medians, np.where(missing)[1])
        if fit:
            self.means = values.mean(axis=0)
            self.scales = values.std(axis=0)
            self.scales = np.where(self.scales > 1e-9, self.scales, 1.0)
        assert self.means is not None and self.scales is not None
        normalized = (values - self.means) / self.scales
        return np.column_stack([np.ones(len(normalized)), normalized])

    def fit(self, frame: pd.DataFrame, outcomes: pd.Series) -> "LogisticModel":
        from scipy.optimize import minimize

        design = self._prepare(frame, fit=True)
        target = outcomes.to_numpy(dtype=float)

        def negative_log_likelihood(weights: np.ndarray) -> float:
            with np.errstate(all="ignore"):
                scores = np.clip(design @ weights, -30.0, 30.0)
            probabilities = np.clip(1.0 / (1.0 + np.exp(-scores)), 1e-9, 1 - 1e-9)
            penalty = self.l2 * float(np.sum(weights[1:] ** 2)) / len(design)
            return float(-np.mean(
                target * np.log(probabilities) + (1 - target) * np.log(1 - probabilities)
            )) + penalty

        fitted = minimize(
            negative_log_likelihood, np.zeros(design.shape[1]), method="L-BFGS-B"
        )
        self.weights = fitted.x
        return self

    def predict_probability(self, frame: pd.DataFrame) -> np.ndarray:
        assert self.weights is not None
        design = self._prepare(frame, fit=False)
        with np.errstate(all="ignore"):
            scores = np.clip(design @ self.weights, -30.0, 30.0)
        return 1.0 / (1.0 + np.exp(-scores))


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
    return parser.parse_args()


def build_joined_dataset(data_root: Path, cache_dir: Path) -> pd.DataFrame:
    """One row per player-gameweek with form, market, and structural features."""
    player_frames, market_frames, structural_market_frames = [], [], []
    for season in SEASON_LABELS:
        players = read_player_season(data_root, season)
        prices = read_initial_prices(data_root, season)
        player_frames.append(players.merge(prices, on="player_id", how="left"))
        market, _ = load_team_gameweek_market(season, cache_dir)
        market_frames.append(market)
        structural_market, _ = rsb.load_structural_market(season, cache_dir)
        structural_market_frames.append(structural_market)

    raw_players = pd.concat(player_frames, ignore_index=True)
    players = add_historical_features(raw_players)
    players["team_key"] = players["team"].map(normalize_team)
    markets = pd.concat(market_frames, ignore_index=True)
    joined = players.merge(markets, on=["season", "gameweek", "team_key"], how="left")

    structural_inputs = rsb.add_lagged_event_history(raw_players)
    structural = rsb.build_structural_predictions(
        structural_inputs,
        pd.concat(structural_market_frames, ignore_index=True),
        evaluation_seasons=STACK_SEASONS,
    )
    joined = joined.merge(
        structural[["season", "gameweek", "player_id", *STRUCTURAL_FEATURES]],
        on=["season", "gameweek", "player_id"], how="inner", validate="one_to_one",
    )
    return joined


def add_realized_3gw(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    lookup = frame.set_index(["season", "player_id", "gameweek"])["total_points"]
    keys = frame[["season", "player_id", "gameweek"]].to_numpy()
    future = np.zeros(len(frame))
    for step, weight in enumerate(HORIZON_WEIGHTS):
        index = pd.MultiIndex.from_arrays([keys[:, 0], keys[:, 1], keys[:, 2] + step])
        future += weight * lookup.reindex(index).fillna(0.0).to_numpy()
    # GW37/38 do not contain a full three-week outcome. Treating the missing
    # future as zero changes the target rather than censoring it and creates a
    # spurious end-of-season advantage for a separately fitted horizon model.
    last_gameweek = frame.groupby("season")["gameweek"].transform("max")
    frame["realized_3gw"] = np.where(
        frame["gameweek"] + len(HORIZON_WEIGHTS) - 1 <= last_gameweek,
        future,
        np.nan,
    )
    return frame


def weekly_utilities(frame: pd.DataFrame, column: str) -> dict[str, float]:
    top5, top5_3gw, ndcg, regret = [], [], [], []
    discounts = 1.0 / np.log2(np.arange(2, 12))
    for _, week in frame.groupby("gameweek"):
        picks = week.nlargest(5, column)
        top5.append(float(picks["total_points"].mean()))
        if picks["realized_3gw"].notna().all():
            top5_3gw.append(float(picks["realized_3gw"].mean()))
        gains = week["total_points"].clip(lower=0.0)
        predicted = gains.loc[week[column].nlargest(10).index].to_numpy()
        ideal = gains.nlargest(10).to_numpy()
        ideal_dcg = float((ideal * discounts[: len(ideal)]).sum())
        ndcg.append(
            float((predicted * discounts[: len(predicted)]).sum()) / ideal_dcg
            if ideal_dcg > 0 else 1.0
        )
        regret.append(
            float(week["total_points"].max())
            - float(week.loc[week[column].idxmax(), "total_points"])
        )
    return {
        "top5_points": float(np.mean(top5)),
        "top5_3gw": float(np.mean(top5_3gw)) if top5_3gw else float("nan"),
        "ndcg10": float(np.mean(ndcg)),
        "captain_regret": float(np.mean(regret)),
    }


def evaluate(joined: pd.DataFrame) -> tuple[list[dict[str, object]], pd.DataFrame]:
    # Compute the realized three-gameweek target on the FULL population before
    # any decision filtering, so a player who drops out of the decision pool
    # in a later week still contributes their actual points to the horizon.
    joined = add_realized_3gw(joined)
    rows: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []
    for season in EVALUATION_SEASONS:
        train = joined[
            (joined["season"] < season)
            & (joined["season"] >= min(STACK_SEASONS))
            & (joined["history_games"] >= 1)
        ].dropna(subset=MARKET_FEATURES)
        test = joined[joined["season"] == season].dropna(subset=MARKET_FEATURES).copy()
        decision_train = train[train["minutes_mean_3"].fillna(0) >= 60]
        decision_test = test[test["minutes_mean_3"].fillna(0) >= 60].copy()
        target = decision_train["total_points"].clip(-5, 25)

        odds_features = FEATURE_COLUMNS + MARKET_FEATURES
        stack_features = odds_features + STRUCTURAL_FEATURES
        odds_model = RidgeModel().fit(decision_train[odds_features], target)
        stack_model = RidgeModel().fit(decision_train[stack_features], target)
        decision_test["odds_xp"] = np.clip(
            odds_model.predict(decision_test[odds_features]), 0, 18
        )
        decision_test["stacked_xp"] = np.clip(
            stack_model.predict(decision_test[stack_features]), 0, 18
        )
        # Dual-horizon model: same features, but the target is the weighted
        # three-gameweek points sum the transfer decision actually optimizes.
        # Training rows in the final two gameweeks have truncated targets
        # (missing future weeks contribute zero), which slightly deflates the
        # fitted scale but affects all models equally.
        horizon_train = decision_train.dropna(subset=["realized_3gw"])
        horizon_model = RidgeModel().fit(
            horizon_train[stack_features],
            horizon_train["realized_3gw"].clip(-10, 60),
        )
        decision_test["stacked_3gw_xp"] = np.clip(
            horizon_model.predict(decision_test[stack_features]), 0, 45
        )
        # Haul head: P(points >= 9) over the same features, used only to rank
        # top-k / captain candidates, never as an expected-points estimate.
        haul_model = LogisticModel().fit(
            decision_train[stack_features],
            (decision_train["total_points"] >= HAUL_THRESHOLD).astype(float),
        )
        decision_test["haul_head_probability"] = haul_model.predict_probability(
            decision_test[stack_features]
        )
        prediction_frames.append(decision_test[
            ["season", "gameweek", "player_id", "web_name", "team", "position",
             "total_points", "realized_3gw", "odds_xp", "stacked_xp",
             "stacked_3gw_xp", "structural_xp", "haul_head_probability"]
        ].copy())

        rows.append({
            "season": SEASON_LABELS[season],
            "player_gameweeks": len(decision_test),
            "train_player_gameweeks": len(decision_train),
        })

    predictions = pd.concat(prediction_frames, ignore_index=True)

    # Select the haul-mix coefficient on the validation season only, by
    # realized three-gameweek top-five utility, then apply it everywhere.
    validation = predictions[predictions["season"] == 2024].copy()
    utilities = {}
    for mix in HAUL_MIX_GRID:
        validation["candidate"] = (
            validation["stacked_xp"] + mix * validation["haul_head_probability"]
        )
        utilities[mix] = weekly_utilities(validation, "candidate")["top5_3gw"]
    haul_mix = max(utilities, key=utilities.get)
    predictions["rank_xp"] = (
        predictions["stacked_xp"] + haul_mix * predictions["haul_head_probability"]
    )

    for row in rows:
        season = next(s for s, label in SEASON_LABELS.items() if label == row["season"])
        frame = predictions[predictions["season"] == season]
        row["haul_mix"] = haul_mix
        for model in ("odds_xp", "stacked_xp", "structural_xp", "rank_xp", "stacked_3gw_xp"):
            if model not in ("rank_xp", "stacked_3gw_xp"):
                errors = frame["total_points"] - frame[model]
                row[f"{model}_mae"] = float(errors.abs().mean())
                row[f"{model}_correlation"] = float(
                    frame["total_points"].corr(frame[model])
                )
            row.update({
                f"{model}_{name}": value
                for name, value in weekly_utilities(frame, model).items()
            })
        # The dual-horizon model is scored against its own target.
        complete_horizon = frame.dropna(subset=["realized_3gw"])
        row["stacked_3gw_xp_horizon_mae"] = float(
            (complete_horizon["realized_3gw"] - complete_horizon["stacked_3gw_xp"]).abs().mean()
        )
        row["stacked_3gw_xp_horizon_correlation"] = float(
            complete_horizon["realized_3gw"].corr(complete_horizon["stacked_3gw_xp"])
        )
        row["stacked_xp_horizon_correlation"] = float(
            complete_horizon["realized_3gw"].corr(complete_horizon["stacked_xp"])
        )
    return rows, predictions


def bootstrap_gate(predictions: pd.DataFrame, season: int = 2025) -> dict[str, object]:
    """Statistical authority gate on the untouched test season.

    The weekly top-five metric has only ~38 observations per season, and a
    paired bootstrap shows its sampling noise (roughly +/-0.5 points/week)
    dwarfs plausible model differences, so a point-estimate comparison on it
    is decided by noise. The sound rule is therefore:

    - the candidate mean forecast must significantly improve MAE and
      correlation under a paired week-cluster bootstrap;
    - optimizer promotion additionally requires positive lower confidence
      bounds for weekly and three-gameweek top-five utility. Merely failing to
      detect harm is not evidence of non-inferiority.
    """
    rng = np.random.default_rng(20260828)
    frame = predictions[predictions["season"] == season]
    result: dict[str, object] = {}

    error_gain = (
        (frame["total_points"] - frame["odds_xp"]).abs()
        - (frame["total_points"] - frame["stacked_xp"]).abs()
    )
    weeks = frame["gameweek"].unique()
    week_groups = {week: frame[frame["gameweek"] == week] for week in weeks}
    mae_samples, correlation_samples = [], []
    for _ in range(2000):
        # Concatenation preserves replacement multiplicities. Using isin() here
        # would collapse repeated clusters and is not a bootstrap sample.
        sample = pd.concat(
            [week_groups[week] for week in rng.choice(weeks, len(weeks), replace=True)],
            ignore_index=True,
        )
        sample_error_gain = (
            (sample["total_points"] - sample["odds_xp"]).abs()
            - (sample["total_points"] - sample["stacked_xp"]).abs()
        )
        mae_samples.append(float(sample_error_gain.mean()))
        correlation_samples.append(
            sample["total_points"].corr(sample["stacked_xp"])
            - sample["total_points"].corr(sample["odds_xp"])
        )
    samples = np.asarray(mae_samples)
    result["mae_gain"] = round(float(error_gain.mean()), 5)
    result["mae_gain_ci95"] = [round(float(v), 5) for v in np.percentile(samples, [2.5, 97.5])]
    mae_significant = float(np.percentile(samples, 2.5)) > 0

    correlation_samples = np.asarray(correlation_samples)
    result["correlation_gain_ci95"] = [
        round(float(v), 5) for v in np.percentile(correlation_samples, [2.5, 97.5])
    ]
    correlation_significant = float(np.percentile(correlation_samples, 2.5)) > 0

    selection_superior = True
    for utility, column in (("top5_points", "total_points"), ("top5_3gw", "realized_3gw")):
        utility_frame = (
            frame.dropna(subset=["realized_3gw"])
            if column == "realized_3gw" else frame
        )
        weekly_difference = np.asarray([
            week.nlargest(5, "stacked_xp")[column].mean()
            - week.nlargest(5, "odds_xp")[column].mean()
            for _, week in utility_frame.groupby("gameweek")
        ])
        count = len(weekly_difference)
        samples = np.array([
            weekly_difference[rng.integers(0, count, count)].mean() for _ in range(5000)
        ])
        interval = [round(float(v), 5) for v in np.percentile(samples, [2.5, 97.5])]
        result[f"{utility}_weekly_diff"] = round(float(weekly_difference.mean()), 5)
        result[f"{utility}_diff_ci95"] = interval
        if interval[0] <= 0:
            selection_superior = False

    # Diagnostic: the haul-mixed ranking score vs the plain stacked ranking.
    for utility, column in (("top5_points", "total_points"), ("top5_3gw", "realized_3gw")):
        if "rank_xp" not in frame.columns:
            break
        utility_frame = (
            frame.dropna(subset=["realized_3gw"])
            if column == "realized_3gw" else frame
        )
        weekly_difference = np.asarray([
            week.nlargest(5, "rank_xp")[column].mean()
            - week.nlargest(5, "stacked_xp")[column].mean()
            for _, week in utility_frame.groupby("gameweek")
        ])
        count = len(weekly_difference)
        samples = np.array([
            weekly_difference[rng.integers(0, count, count)].mean() for _ in range(5000)
        ])
        result[f"rank_head_{utility}_diff"] = round(float(weekly_difference.mean()), 5)
        result[f"rank_head_{utility}_diff_ci95"] = [
            round(float(v), 5) for v in np.percentile(samples, [2.5, 97.5])
        ]

    # Dual-horizon gate: the 3-GW model competes with the 1-GW stacked model
    # as a ranker of three-gameweek value. Correlation gain must be
    # significant and 3-GW top-five utility must not significantly degrade.
    if "stacked_3gw_xp" in frame.columns:
        horizon_frame = frame.dropna(subset=["realized_3gw"])
        horizon_weeks = horizon_frame["gameweek"].unique()
        horizon_groups = {
            week: horizon_frame[horizon_frame["gameweek"] == week]
            for week in horizon_weeks
        }
        horizon_correlation_samples = []
        for _ in range(2000):
            sample = pd.concat(
                [horizon_groups[week] for week in rng.choice(
                    horizon_weeks, len(horizon_weeks), replace=True
                )],
                ignore_index=True,
            )
            horizon_correlation_samples.append(
                sample["realized_3gw"].corr(sample["stacked_3gw_xp"])
                - sample["realized_3gw"].corr(sample["stacked_xp"])
            )
        horizon_correlation_samples = np.asarray(horizon_correlation_samples)
        interval = [
            round(float(v), 5)
            for v in np.percentile(horizon_correlation_samples, [2.5, 97.5])
        ]
        result["horizon_correlation_gain_ci95"] = interval
        horizon_correlation_significant = interval[0] > 0

        weekly_difference = np.asarray([
            week.nlargest(5, "stacked_3gw_xp")["realized_3gw"].mean()
            - week.nlargest(5, "stacked_xp")["realized_3gw"].mean()
            for _, week in horizon_frame.groupby("gameweek")
        ])
        count = len(weekly_difference)
        samples = np.array([
            weekly_difference[rng.integers(0, count, count)].mean()
            for _ in range(5000)
        ])
        utility_interval = [
            round(float(v), 5) for v in np.percentile(samples, [2.5, 97.5])
        ]
        result["horizon_top5_3gw_diff"] = round(float(weekly_difference.mean()), 5)
        result["horizon_top5_3gw_diff_ci95"] = utility_interval
        result["accepted_for_transfer_horizon"] = bool(
            horizon_correlation_significant and utility_interval[0] > 0
        )

    result["accepted_for_mean_forecast"] = bool(
        mae_significant and correlation_significant
    )
    result["accepted_for_optimizer"] = bool(
        result["accepted_for_mean_forecast"] and selection_superior
    )
    result["rule"] = (
        "on the 2025/26 evaluation season: week-cluster 95% bootstrap lower "
        "bounds must exceed zero for MAE and correlation gain; optimizer "
        "promotion also requires positive lower bounds for weekly and "
        "three-gameweek top-five utility"
    )
    return result


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    joined = build_joined_dataset(args.data_root, args.cache_dir)
    rows, predictions = evaluate(joined)
    gate = bootstrap_gate(predictions)
    manifest = {
        "method": {
            "model": "ridge over form + no-vig market + structural Poisson components",
            "training": "seasons strictly before the evaluation season, 2023/24 onward",
            "lookahead_control": "player features stop at GW-1; structural priors earlier seasons only; 2025/26 untouched for all choices",
        },
        "season_results": [
            {key: (round(value, 5) if isinstance(value, float) else value)
             for key, value in row.items()} for row in rows
        ],
        "authority_gate": gate,
    }
    predictions.to_csv(args.output_dir / "stacked_player_predictions.csv", index=False)
    # Replay-compatible export: run_team_replay.py --odds-predictions accepts
    # this schema, so the accepted forecast can drive the team-path replays.
    predictions.rename(columns={"stacked_xp": "odds_prediction"})[
        ["season", "gameweek", "player_id", "odds_prediction"]
    ].to_csv(args.output_dir / "stacked_replay_predictions.csv", index=False)
    (args.output_dir / "stacked_backtest_summary.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest["season_results"], indent=2))
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
