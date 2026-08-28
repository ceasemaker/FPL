#!/usr/bin/env python3
"""Leakage-safe, season-by-season backtest for FPL player decision metrics.

The model for each evaluation season is trained only on earlier seasons. Player
features for gameweek G use results through G-1. Realized effective ownership
is retained for retrospective rank-impact analysis; lagged effective ownership
is used as the actionable ownership forecast.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


SEASON_LABELS = {
    2022: "2022/23",
    2023: "2023/24",
    2024: "2024/25",
    2025: "2025/26",
}

NUMERIC_COLUMNS = [
    "minutes",
    "starts",
    "total_points",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
    "ict_index",
    "bps",
]

FEATURE_COLUMNS = [
    "gameweek",
    "initial_price",
    "history_games",
    "last_points",
    "last_minutes",
    "points_mean_3",
    "points_mean_6",
    "points_sd_6",
    "minutes_mean_3",
    "minutes_mean_6",
    "appearance_rate_6",
    "start_rate_6",
    "xgi_per90_6",
    "xgc_per90_6",
    "ict_per90_6",
    "bps_per90_6",
    "pos_Goalkeeper",
    "pos_Defender",
    "pos_Midfielder",
    "pos_Forward",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("fpl_data"),
        help="Repository FPL data directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/fpl_decision_backtest/output"),
    )
    return parser.parse_args()


def gameweek_from_path(path: Path) -> int:
    match = re.search(r"week-(\d+)", path.name)
    if not match:
        raise ValueError(f"Cannot identify gameweek from {path}")
    return int(match.group(1))


def read_player_season(data_root: Path, season: int) -> pd.DataFrame:
    directory = data_root / str(season) / "player_data"
    files = sorted(directory.glob("public-epl-stats-players-week-*.csv"), key=gameweek_from_path)
    if len(files) != 38:
        raise ValueError(f"Expected 38 player files for {season}; found {len(files)}")

    frames: list[pd.DataFrame] = []
    for path in files:
        frame = pd.read_csv(path, low_memory=False)
        frame["gameweek"] = gameweek_from_path(path)
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data = data.rename(columns={"id": "player_id"})
    data["season"] = season
    data["season_label"] = SEASON_LABELS[season]
    for column in NUMERIC_COLUMNS:
        if column not in data:
            data[column] = 0.0
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0)
    return data


def read_initial_prices(data_root: Path, season: int) -> pd.DataFrame:
    path = data_root / str(season) / "overall_player_data" / "overall_payer_data.csv"
    frame = pd.read_csv(path, low_memory=False)
    frame = frame.rename(columns={"id": "player_id"})
    now_cost = pd.to_numeric(frame["now_cost"], errors="coerce")
    total_change = pd.to_numeric(frame["cost_change_start"], errors="coerce").fillna(0)
    frame["initial_price"] = (now_cost - total_change) / 10.0
    return frame[["player_id", "initial_price"]].drop_duplicates("player_id")


def read_elite_eo(data_root: Path, season: int) -> pd.DataFrame:
    directory = data_root / str(season) / "top_100_teams"
    files = sorted(directory.glob("public-epl-stats-top100-teams-gw-*.csv"))
    if not files:
        return pd.DataFrame(columns=["season", "gameweek", "player_id", "realized_eo"])

    frames: list[pd.DataFrame] = []
    for path in files:
        frame = pd.read_csv(path, low_memory=False)
        if frame.empty:
            continue
        gameweek = int(pd.to_numeric(frame["event"], errors="coerce").dropna().iloc[0])
        manager_count = max(frame.shape[0] / 15.0, 1.0)
        grouped = (
            frame.assign(multiplier=pd.to_numeric(frame["multiplier"], errors="coerce").fillna(0))
            .groupby("element", as_index=False)["multiplier"]
            .sum()
            .rename(columns={"element": "player_id", "multiplier": "multiplier_sum"})
        )
        grouped["realized_eo"] = grouped["multiplier_sum"] / manager_count
        grouped["season"] = season
        grouped["gameweek"] = gameweek
        frames.append(grouped[["season", "gameweek", "player_id", "realized_eo"]])
    return pd.concat(frames, ignore_index=True)


def shifted_rolling_sum(series: pd.Series, window: int) -> pd.Series:
    return series.shift(1).rolling(window, min_periods=1).sum()


def add_historical_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values(["season", "player_id", "gameweek"]).copy()
    grouped = frame.groupby(["season", "player_id"], sort=False, group_keys=False)
    frame["history_games"] = grouped.cumcount()
    frame["last_points"] = grouped["total_points"].shift(1)
    frame["last_minutes"] = grouped["minutes"].shift(1)

    for window in (3, 6):
        frame[f"points_mean_{window}"] = grouped["total_points"].transform(
            lambda values: values.shift(1).rolling(window, min_periods=1).mean()
        )
        frame[f"minutes_mean_{window}"] = grouped["minutes"].transform(
            lambda values: values.shift(1).rolling(window, min_periods=1).mean()
        )
    frame["points_sd_6"] = grouped["total_points"].transform(
        lambda values: values.shift(1).rolling(6, min_periods=2).std()
    )
    frame["appearance_rate_6"] = grouped["minutes"].transform(
        lambda values: (values > 0).astype(float).shift(1).rolling(6, min_periods=1).mean()
    )
    frame["start_rate_6"] = grouped["starts"].transform(
        lambda values: values.shift(1).rolling(6, min_periods=1).mean()
    )

    for numerator, output in (
        ("expected_goal_involvements", "xgi_per90_6"),
        ("expected_goals_conceded", "xgc_per90_6"),
        ("ict_index", "ict_per90_6"),
        ("bps", "bps_per90_6"),
    ):
        numerator_sum = grouped[numerator].transform(lambda values: shifted_rolling_sum(values, 6))
        minute_sum = grouped["minutes"].transform(lambda values: shifted_rolling_sum(values, 6))
        frame[output] = np.where(minute_sum > 0, 90.0 * numerator_sum / minute_sum, np.nan)

    position_dummies = pd.get_dummies(frame["position"], prefix="pos", dtype=float)
    frame = pd.concat([frame, position_dummies], axis=1)
    for position in ("Goalkeeper", "Defender", "Midfielder", "Forward"):
        column = f"pos_{position}"
        if column not in frame:
            frame[column] = 0.0
    return frame


class RidgeModel:
    """Small dependency-free ridge regression with median imputation."""

    def __init__(self, alpha: float = 25.0) -> None:
        self.alpha = alpha
        self.medians: np.ndarray | None = None
        self.means: np.ndarray | None = None
        self.scales: np.ndarray | None = None
        self.coefficients: np.ndarray | None = None

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

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> "RidgeModel":
        design = self._prepare(frame, fit=True)
        penalty = np.eye(design.shape[1]) * self.alpha
        penalty[0, 0] = 0.0
        self.coefficients = np.linalg.solve(
            design.T @ design + penalty,
            design.T @ target.to_numpy(dtype=float),
        )
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        assert self.coefficients is not None
        return self._prepare(frame, fit=False) @ self.coefficients


def fit_predict_walk_forward(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions: list[pd.DataFrame] = []
    model_rows: list[dict[str, float | int | str]] = []
    for season in (2023, 2024, 2025):
        train = data[(data["season"] < season) & (data["history_games"] >= 1)].copy()
        test = data[data["season"] == season].copy()
        x_train = train[FEATURE_COLUMNS]
        y_train = train["total_points"].clip(-5, 25)
        x_test = test[FEATURE_COLUMNS]

        mean_model = RidgeModel().fit(x_train, y_train)
        train_prediction = np.clip(mean_model.predict(x_train), 0, 18)
        train_residual = y_train.to_numpy() - train_prediction
        train_decision_mask = train["minutes_mean_3"].fillna(0) >= 60
        train_with_residual = train.loc[train_decision_mask, ["position"]].copy()
        train_with_residual["residual"] = train_residual[train_decision_mask.to_numpy()]
        residual_bounds = train_with_residual.groupby("position")["residual"].quantile([0.10, 0.90]).unstack()
        global_low, global_high = np.quantile(train_with_residual["residual"], [0.10, 0.90])

        test["predicted_points"] = np.clip(mean_model.predict(x_test), 0, 18)
        low_adjustment = test["position"].map(residual_bounds.get(0.10, pd.Series(dtype=float))).fillna(global_low)
        high_adjustment = test["position"].map(residual_bounds.get(0.90, pd.Series(dtype=float))).fillna(global_high)
        test["points_p10"] = np.clip(test["predicted_points"] + low_adjustment, -3, 18)
        test["points_p90"] = np.clip(test["predicted_points"] + high_adjustment, 0, 25)
        test["points_p10"] = np.minimum(test["points_p10"], test["predicted_points"])
        test["points_p90"] = np.maximum(test["points_p90"], test["predicted_points"])
        test["predictive_sd"] = (test["points_p90"] - test["points_p10"]) / 2.563
        predictions.append(test)

        actual = test["total_points"]
        predicted = test["predicted_points"]
        correlation = actual.corr(predicted)
        interval_coverage = ((actual >= test["points_p10"]) & (actual <= test["points_p90"])).mean()
        decision_mask = test["minutes_mean_3"].fillna(0) >= 60
        decision_actual = actual[decision_mask]
        decision_predicted = predicted[decision_mask]
        naive_prediction = test.loc[decision_mask, "points_mean_3"].fillna(0).clip(0, 18)
        decision_coverage = (
            (decision_actual >= test.loc[decision_mask, "points_p10"])
            & (decision_actual <= test.loc[decision_mask, "points_p90"])
        ).mean()
        model_rows.append(
            {
                "season": season,
                "season_label": SEASON_LABELS[season],
                "train_rows": len(train),
                "test_rows": len(test),
                "mae": np.mean(np.abs(actual - predicted)),
                "rmse": math.sqrt(np.mean(np.square(actual - predicted))),
                "correlation": correlation,
                "p10_p90_coverage": interval_coverage,
                "decision_rows": int(decision_mask.sum()),
                "decision_mae": np.mean(np.abs(decision_actual - decision_predicted)),
                "decision_rmse": math.sqrt(np.mean(np.square(decision_actual - decision_predicted))),
                "decision_correlation": decision_actual.corr(decision_predicted),
                "naive_last3_mae": np.mean(np.abs(decision_actual - naive_prediction)),
                "decision_p10_p90_coverage": decision_coverage,
            }
        )
    return pd.concat(predictions, ignore_index=True), pd.DataFrame(model_rows)


def add_cross_sectional_price_curve(data: pd.DataFrame, eligible: pd.Series) -> pd.DataFrame:
    """Estimate each week's position-specific expected-points price curve."""
    data = data.copy()
    data["fair_expected_at_price"] = np.nan
    data["marginal_xp_per_m"] = np.nan
    data["fair_price"] = np.nan
    keys = ["season", "gameweek", "position"]
    for _, group in data[eligible].groupby(keys):
        x = group["initial_price"].to_numpy(dtype=float)
        y = group["predicted_points"].to_numpy(dtype=float)
        valid = np.isfinite(x) & np.isfinite(y)
        if valid.sum() < 5 or np.std(x[valid]) < 1e-9:
            slope = 0.0
            intercept = float(np.nanmedian(y))
        else:
            raw_slope = np.cov(x[valid], y[valid], ddof=0)[0, 1] / np.var(x[valid])
            slope = float(np.clip(raw_slope, 0.0, 2.0))
            intercept = float(np.mean(y[valid]) - slope * np.mean(x[valid]))
        indexes = group.index
        fair_expected = intercept + slope * group["initial_price"]
        data.loc[indexes, "fair_expected_at_price"] = fair_expected
        data.loc[indexes, "marginal_xp_per_m"] = slope
        if slope > 0.05:
            data.loc[indexes, "fair_price"] = (
                group["predicted_points"] - intercept
            ) / slope
    return data


def add_ownership_and_valuation(data: pd.DataFrame, eo: pd.DataFrame) -> pd.DataFrame:
    data = data.merge(eo, how="left", on=["season", "gameweek", "player_id"])
    data["realized_eo"] = data["realized_eo"].fillna(0.0)
    data = data.sort_values(["season", "player_id", "gameweek"])
    data["forecast_eo"] = data.groupby(["season", "player_id"])["realized_eo"].shift(1).fillna(0.0)

    data["predicted_minutes"] = data["minutes_mean_3"].fillna(0.0)
    data["nonowner_expected_drag"] = -data["forecast_eo"] * data["predicted_points"]
    data["nonowner_haul_risk"] = data["forecast_eo"] * data["points_p90"]
    data["nonowner_realized_rank_points"] = -data["realized_eo"] * data["total_points"]
    data["owner_realized_rank_points"] = (1.0 - data["realized_eo"]) * data["total_points"]
    data["captain_realized_rank_points"] = (2.0 - data["realized_eo"]) * data["total_points"]
    data["nonowner_rank_sd"] = data["forecast_eo"] * data["predictive_sd"]
    data["owner_rank_sd"] = (1.0 - data["forecast_eo"]).abs() * data["predictive_sd"]
    data["captain_rank_sd"] = (2.0 - data["forecast_eo"]).abs() * data["predictive_sd"]

    keys = ["season", "gameweek", "position"]
    eligible = data["predicted_minutes"] >= 45
    data["replacement_xp"] = np.nan
    data.loc[eligible, "replacement_xp"] = (
        data[eligible].groupby(keys)["predicted_points"].transform(lambda values: values.quantile(0.25))
    )
    data["replacement_xp"] = data["replacement_xp"].fillna(0.0)
    eligible_min_price = (
        data[eligible].groupby(keys)["initial_price"].min().rename("eligible_min_price").reset_index()
    )
    data = data.merge(eligible_min_price, how="left", on=keys)
    eligible = data["predicted_minutes"] >= 45
    data["position_min_price"] = data["eligible_min_price"].fillna(data["initial_price"])
    price_premium = (data["initial_price"] - data["position_min_price"] + 0.5).clip(lower=0.5)
    data["value_above_replacement_per_m"] = (
        data["predicted_points"] - data["replacement_xp"]
    ) / price_premium

    data = add_cross_sectional_price_curve(data, eligible)
    data["valuation_edge"] = data["predicted_points"] - data["fair_expected_at_price"]
    data["realized_value_edge"] = data["total_points"] - data["fair_expected_at_price"]

    eligible_quantile = (
        data[eligible]
        .groupby(["season", "gameweek"])["predicted_points"]
        .quantile(0.75)
        .rename("weekly_xp_q75")
        .reset_index()
    )
    data = data.merge(eligible_quantile, how="left", on=["season", "gameweek"])
    data["is_differential_candidate"] = (
        (data["forecast_eo"] < 0.10)
        & (data["predicted_minutes"] >= 60)
        & (data["predicted_points"] >= data["weekly_xp_q75"])
    )
    data["is_undervalued"] = (
        (data["predicted_minutes"] >= 60)
        & (data["valuation_edge"] >= 0.5)
        & (data["predicted_points"] >= data["replacement_xp"])
    )
    data["is_overvalued"] = (
        (data["predicted_minutes"] >= 60)
        & (data["valuation_edge"] <= -0.5)
    )
    return data


def strategy_summary(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    eligible = data[data["predicted_minutes"] >= 60].copy()
    selections: list[pd.DataFrame] = []
    for (_, _), week in eligible.groupby(["season", "gameweek"]):
        definitions = {
            "model_top_5": week.nlargest(5, "predicted_points"),
            "value_top_5": week.nlargest(5, "value_above_replacement_per_m"),
            "differential_top_5": week[week["is_differential_candidate"]].nlargest(5, "predicted_points"),
            "undervalued_top_5": week[week["is_undervalued"]].nlargest(5, "valuation_edge"),
            "overvalued_bottom_5": week[week["is_overvalued"]].nsmallest(5, "valuation_edge"),
            "template_70_plus": week[week["forecast_eo"] >= 0.70],
        }
        for strategy, selected in definitions.items():
            if selected.empty:
                continue
            selected = selected.copy()
            selected["strategy"] = strategy
            selections.append(selected)
    selected = pd.concat(selections, ignore_index=True)
    selected["haul"] = selected["total_points"] >= 8
    selected["blank"] = selected["total_points"] <= 2
    selected["beat_price_peer"] = selected["realized_value_edge"] > 0
    summary = (
        selected.groupby(["season_label", "strategy"], as_index=False)
        .agg(
            selections=("player_id", "size"),
            mean_actual_points=("total_points", "mean"),
            median_actual_points=("total_points", "median"),
            mean_predicted_points=("predicted_points", "mean"),
            haul_rate=("haul", "mean"),
            blank_rate=("blank", "mean"),
            mean_realized_value_edge=("realized_value_edge", "mean"),
            beat_price_peer_rate=("beat_price_peer", "mean"),
        )
    )
    overall = (
        selected.groupby("strategy", as_index=False)
        .agg(
            selections=("player_id", "size"),
            mean_actual_points=("total_points", "mean"),
            median_actual_points=("total_points", "median"),
            mean_predicted_points=("predicted_points", "mean"),
            haul_rate=("haul", "mean"),
            blank_rate=("blank", "mean"),
            mean_realized_value_edge=("realized_value_edge", "mean"),
            beat_price_peer_rate=("beat_price_peer", "mean"),
        )
    )
    overall["season_label"] = "All evaluation seasons"
    return pd.concat([summary, overall], ignore_index=True), selected


def build_eo_summary(data: pd.DataFrame) -> pd.DataFrame:
    bins = [-0.001, 0.10, 0.30, 0.50, 0.70, 1.00, np.inf]
    labels = ["0-10%", "10-30%", "30-50%", "50-70%", "70-100%", ">100%"]
    exposed = data[(data["realized_eo"] > 0) & (data["minutes"] > 0)].copy()
    exposed["eo_bucket"] = pd.cut(exposed["realized_eo"], bins=bins, labels=labels)
    exposed["haul"] = exposed["total_points"] >= 8
    exposed["blank"] = exposed["total_points"] <= 2
    return (
        exposed.groupby("eo_bucket", observed=False, as_index=False)
        .agg(
            player_weeks=("player_id", "size"),
            mean_eo=("realized_eo", "mean"),
            mean_points=("total_points", "mean"),
            points_sd=("total_points", "std"),
            haul_rate=("haul", "mean"),
            blank_rate=("blank", "mean"),
            mean_nonowner_rank_points=("nonowner_realized_rank_points", "mean"),
        )
    )


def build_weekly_summary(data: pd.DataFrame) -> pd.DataFrame:
    eligible = data[data["predicted_minutes"] >= 60].copy()
    return (
        eligible.groupby(["season", "season_label", "gameweek"], as_index=False)
        .agg(
            eligible_players=("player_id", "size"),
            mean_actual_points=("total_points", "mean"),
            mean_predicted_points=("predicted_points", "mean"),
            differentials=("is_differential_candidate", "sum"),
            undervalued=("is_undervalued", "sum"),
            overvalued=("is_overvalued", "sum"),
        )
    )


def build_volatility_summary(data: pd.DataFrame) -> pd.DataFrame:
    eligible = data[(data["predicted_minutes"] >= 60) & data["points_sd_6"].notna()].copy()
    eligible["volatility_percentile"] = eligible.groupby(
        ["season", "position"]
    )["points_sd_6"].rank(pct=True, method="average")
    eligible["volatility_quartile"] = pd.cut(
        eligible["volatility_percentile"],
        bins=[0, 0.25, 0.50, 0.75, 1.0],
        labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"],
        include_lowest=True,
    )
    eligible["forecast_residual"] = eligible["total_points"] - eligible["predicted_points"]
    eligible["haul"] = eligible["total_points"] >= 8
    eligible["blank"] = eligible["total_points"] <= 2
    return (
        eligible.groupby("volatility_quartile", observed=False, as_index=False)
        .agg(
            player_weeks=("player_id", "size"),
            historical_points_sd=("points_sd_6", "mean"),
            predicted_points=("predicted_points", "mean"),
            actual_points=("total_points", "mean"),
            mean_forecast_residual=("forecast_residual", "mean"),
            actual_points_sd=("total_points", "std"),
            haul_rate=("haul", "mean"),
            blank_rate=("blank", "mean"),
        )
    )


def build_haaland_case(data: pd.DataFrame) -> pd.DataFrame:
    mask = data["web_name"].astype(str).str.contains("Haaland", case=False, na=False)
    columns = [
        "season_label",
        "gameweek",
        "web_name",
        "initial_price",
        "predicted_points",
        "points_p10",
        "points_p90",
        "total_points",
        "forecast_eo",
        "realized_eo",
        "nonowner_expected_drag",
        "nonowner_realized_rank_points",
        "owner_realized_rank_points",
        "value_above_replacement_per_m",
        "fair_price",
        "valuation_edge",
    ]
    return data.loc[mask, columns].sort_values(["season_label", "gameweek"])


def validate_no_leakage(data: pd.DataFrame) -> None:
    sample = data[data["gameweek"] == 2]
    previous = data[data["gameweek"] == 1][["season", "player_id", "total_points"]].rename(
        columns={"total_points": "previous_points"}
    )
    check = sample.merge(previous, on=["season", "player_id"], how="inner")
    if not np.allclose(check["last_points"], check["previous_points"], equal_nan=True):
        raise AssertionError("Lag feature validation failed")
    if data.duplicated(["season", "gameweek", "player_id"]).any():
        raise AssertionError("Duplicate player-week records detected")


def rounded_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    output = frame.copy()
    numeric = output.select_dtypes(include=[np.number]).columns
    output[numeric] = output[numeric].round(4)
    return output.to_dict(orient="records")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    player_frames: list[pd.DataFrame] = []
    eo_frames: list[pd.DataFrame] = []
    for season in SEASON_LABELS:
        players = read_player_season(args.data_root, season)
        prices = read_initial_prices(args.data_root, season)
        player_frames.append(players.merge(prices, on="player_id", how="left"))
        eo_frames.append(read_elite_eo(args.data_root, season))

    all_players = add_historical_features(pd.concat(player_frames, ignore_index=True))
    validate_no_leakage(all_players)
    predictions, model_summary = fit_predict_walk_forward(all_players)
    eo = pd.concat([frame for frame in eo_frames if not frame.empty], ignore_index=True)
    metrics = add_ownership_and_valuation(predictions, eo)

    strategy, selections = strategy_summary(metrics)
    eo_summary = build_eo_summary(metrics)
    weekly = build_weekly_summary(metrics)
    volatility = build_volatility_summary(metrics)
    haaland = build_haaland_case(metrics)

    export_columns = [
        "season_label", "gameweek", "player_id", "web_name", "team", "position",
        "initial_price", "predicted_minutes", "predicted_points", "points_p10", "points_p90",
        "predictive_sd", "total_points", "forecast_eo", "realized_eo",
        "nonowner_expected_drag", "nonowner_haul_risk", "nonowner_rank_sd",
        "owner_rank_sd", "captain_rank_sd", "nonowner_realized_rank_points",
        "owner_realized_rank_points", "captain_realized_rank_points", "replacement_xp",
        "value_above_replacement_per_m", "fair_expected_at_price", "marginal_xp_per_m",
        "fair_price", "valuation_edge", "is_differential_candidate",
        "realized_value_edge", "is_undervalued", "is_overvalued",
    ]
    metrics[export_columns].to_csv(args.output_dir / "player_week_metrics.csv", index=False)
    model_summary.to_csv(args.output_dir / "model_summary.csv", index=False)
    strategy.to_csv(args.output_dir / "strategy_summary.csv", index=False)
    weekly.to_csv(args.output_dir / "weekly_summary.csv", index=False)
    eo_summary.to_csv(args.output_dir / "eo_bucket_summary.csv", index=False)
    volatility.to_csv(args.output_dir / "volatility_summary.csv", index=False)
    haaland.to_csv(args.output_dir / "haaland_case_study.csv", index=False)
    selections[export_columns + ["strategy"]].to_csv(
        args.output_dir / "weekly_selections.csv", index=False
    )

    manifest = {
        "training_season": "2022/23",
        "evaluation_seasons": ["2023/24", "2024/25", "2025/26"],
        "model_summary": rounded_records(model_summary),
        "strategy_summary": rounded_records(
            strategy[strategy["season_label"] == "All evaluation seasons"]
        ),
        "eo_summary": rounded_records(eo_summary),
        "volatility_summary": rounded_records(volatility),
        "rows_exported": int(len(metrics)),
    }
    (args.output_dir / "summary.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
