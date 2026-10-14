"""The points model: gradient-boosted trees on the deadline-safe features."""
from __future__ import annotations

import io

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from .features import FEATURES

PARAMS = dict(
    loss="squared_error",
    learning_rate=0.05,
    max_iter=250,
    max_leaf_nodes=31,
    min_samples_leaf=80,
    l2_regularization=1.0,
    random_state=7,
)


def training_rows(features: pd.DataFrame) -> pd.DataFrame:
    """Played weeks only; a player needs some history to be learnable."""
    rows = features[features["total_points"].notna()]
    return rows[rows["appearances"].notna()]


class PointsModel:
    """The regressor plus the columns it was fitted on.

    Columns that are empty or constant in the training window (last season's
    rates when there is no last season; the DefCon flag before 2025/26) carry
    no information, and recent scikit-learn refuses to bin them, so they are
    left out of that fit.
    """

    def __init__(self, columns: list[str], regressor: HistGradientBoostingRegressor):
        self.columns = columns
        self.regressor = regressor

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        return self.regressor.predict(features[self.columns].astype(float))


def fit(features: pd.DataFrame) -> PointsModel:
    rows = training_rows(features)
    X = rows[FEATURES].astype(float)
    columns = [c for c in FEATURES if X[c].nunique(dropna=True) > 1]
    regressor = HistGradientBoostingRegressor(**PARAMS)
    regressor.fit(X[columns], rows["total_points"].astype(float))
    return PointsModel(columns, regressor)


def predict(model: PointsModel, features: pd.DataFrame) -> np.ndarray:
    predictions = model.predict(features)
    # Players with no history at all (new signings, promoted squads) get no
    # forecast rather than a guess from position and price alone.
    return np.where(features["appearances"].isna(), np.nan, predictions)


def dumps(model) -> bytes:
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    return buffer.getvalue()


def loads(payload: bytes):
    return joblib.load(io.BytesIO(bytes(payload)))
