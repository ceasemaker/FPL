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


def fit(features: pd.DataFrame) -> HistGradientBoostingRegressor:
    rows = training_rows(features)
    model = HistGradientBoostingRegressor(**PARAMS)
    model.fit(rows[FEATURES].astype(float), rows["total_points"].astype(float))
    return model


def predict(model: HistGradientBoostingRegressor, features: pd.DataFrame) -> np.ndarray:
    predictions = model.predict(features[FEATURES].astype(float))
    # Players with no history at all (new signings, promoted squads) get no
    # forecast rather than a guess from position and price alone.
    return np.where(features["appearances"].isna(), np.nan, predictions)


def dumps(model) -> bytes:
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    return buffer.getvalue()


def loads(payload: bytes):
    return joblib.load(io.BytesIO(bytes(payload)))
