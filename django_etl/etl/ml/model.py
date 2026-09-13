"""ML models for FPL predictions."""
import logging
import os
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from etl.ml.features import (
    extract_features,
    feature_vector,
    get_training_data,
    iter_training_rows,
)
from etl.models import Athlete

logger = logging.getLogger(__name__)

# Model storage directory
MODELS_DIR = Path(__file__).parent.parent / "ml_models"
MODELS_DIR.mkdir(exist_ok=True)


def get_model_path(model_name: str) -> Path:
    """Get the file path for a saved model."""
    return MODELS_DIR / f"fpl_{model_name}.joblib"


@lru_cache(maxsize=16)
def _load_model(path: str):
    """Load each immutable model artifact once per prediction process."""
    return joblib.load(path)


def train_points_regressor(X_train: list, y_train: list) -> Pipeline:
    """Train regression model for predicted points."""
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("regressor", RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            random_state=42,
            n_jobs=-1,
            verbose=0
        )),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def train_clean_sheet_classifier(X_train: list, y_train: list) -> Pipeline:
    """Train classifier for clean sheet probability (GK/DEF only)."""
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            random_state=42,
            n_jobs=-1,
            verbose=0
        )),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def train_goal_classifier(X_train: list, y_train: list) -> Pipeline:
    """Train classifier for goal scoring probability (MID/FWD only)."""
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            random_state=42,
            n_jobs=-1,
            verbose=0
        )),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def train_assist_classifier(X_train: list, y_train: list) -> Pipeline:
    """Train classifier for assist probability (MID/FWD only)."""
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            random_state=42,
            n_jobs=-1,
            verbose=0
        )),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def train_bonus_classifier(X_train: list, y_train: list) -> Pipeline:
    """Train classifier for bonus point probability."""
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            random_state=42,
            n_jobs=-1,
            verbose=0
        )),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def prepare_training_data_by_position(position: int) -> tuple[list, list, list, list, list, list]:
    """
    Prepare training data filtered by player position.
    Returns: (X_all, y_points, y_clean_sheet, y_goals, y_assists, y_bonus)
    """
    athlete_ids = list(
        Athlete.objects.filter(element_type=position).values_list("id", flat=True)
    )

    X_all = []
    y_points = []
    y_clean_sheets = []
    y_goals = []
    y_assists = []
    y_bonus = []

    for stat, feature_dict in iter_training_rows(athlete_ids):
        X_all.append(feature_vector(feature_dict))
        y_points.append(stat.total_points)
        y_clean_sheets.append(1 if stat.clean_sheets >= 1 else 0)
        y_goals.append(1 if stat.goals_scored >= 1 else 0)
        y_assists.append(1 if stat.assists >= 1 else 0)
        y_bonus.append(1 if stat.bonus >= 2 else 0)

    return X_all, y_points, y_clean_sheets, y_goals, y_assists, y_bonus


def train_and_save_models() -> None:
    """Train all models and save them."""
    logger.info("Starting ML model training...")

    # Position: 1=GK, 2=DEF, 3=MID, 4=FWD
    positions = {
        1: "goalkeeper",
        2: "defender",
        3: "midfielder",
        4: "forward",
    }

    try:
        # Train universal points predictor
        logger.info("Training points regressor...")
        X_train, y_train = get_training_data()

        if X_train:
            points_model = train_points_regressor(X_train, y_train)
            joblib.dump(points_model, get_model_path("points_regressor"))
            logger.info(f"Saved points_regressor model")
        else:
            logger.warning("Insufficient training data for points regressor")

        # Train position-specific models
        for position_id, position_name in positions.items():
            logger.info(f"Training models for {position_name}s (position {position_id})...")

            X_all, y_points, y_cs, y_goals, y_assists, y_bonus = prepare_training_data_by_position(position_id)

            if not X_all:
                logger.warning(f"No training data for position {position_name}")
                continue

            # Clean sheet probability (GK/DEF only)
            if position_id in (1, 2) and sum(y_cs) > 0:
                cs_model = train_clean_sheet_classifier(X_all, y_cs)
                joblib.dump(cs_model, get_model_path(f"{position_name}_clean_sheet"))
                logger.info(f"Saved {position_name}_clean_sheet model")

            # Goal probability (MID/FWD only)
            if position_id in (3, 4) and sum(y_goals) > 0:
                goal_model = train_goal_classifier(X_all, y_goals)
                joblib.dump(goal_model, get_model_path(f"{position_name}_goal"))
                logger.info(f"Saved {position_name}_goal model")

            # Assist probability (MID/FWD only)
            if position_id in (3, 4) and sum(y_assists) > 0:
                assist_model = train_assist_classifier(X_all, y_assists)
                joblib.dump(assist_model, get_model_path(f"{position_name}_assist"))
                logger.info(f"Saved {position_name}_assist model")

            # Bonus probability (all positions)
            if sum(y_bonus) > 0:
                bonus_model = train_bonus_classifier(X_all, y_bonus)
                joblib.dump(bonus_model, get_model_path(f"{position_name}_bonus"))
                logger.info(f"Saved {position_name}_bonus model")

        logger.info("ML model training completed successfully")
        _load_model.cache_clear()

    except Exception as e:
        logger.error(f"Error training ML models: {e}", exc_info=True)
        raise


def predict_points(athlete_id: int, game_week: int) -> float:
    """Predict points for a player in a specific gameweek."""
    feature_dict = extract_features(athlete_id, game_week)
    if not feature_dict:
        return 0.0

    features = feature_vector(feature_dict)

    model_path = get_model_path("points_regressor")
    if not model_path.exists():
        return 0.0

    model = _load_model(str(model_path))
    prediction = model.predict([features])[0]
    return max(0, float(prediction))  # Ensure non-negative


def predict_probability(athlete_id: int, game_week: int, prob_type: str) -> float:
    """
    Predict probability for a specific event type.
    prob_type: 'clean_sheet', 'goal', 'assist', 'bonus'
    """
    athlete = Athlete.objects.filter(id=athlete_id).first()
    if not athlete:
        return 0.0

    feature_dict = extract_features(athlete_id, game_week)
    if not feature_dict:
        return 0.0

    features = feature_vector(feature_dict)

    # Map position to model name
    position_names = {
        1: "goalkeeper",
        2: "defender",
        3: "midfielder",
        4: "forward",
    }
    position_name = position_names.get(athlete.element_type, "forward")

    # Determine which model to use based on position and prob_type
    if prob_type == "clean_sheet" and athlete.element_type in (1, 2):
        model_path = get_model_path(f"{position_name}_clean_sheet")
    elif prob_type == "goal" and athlete.element_type in (3, 4):
        model_path = get_model_path(f"{position_name}_goal")
    elif prob_type == "assist" and athlete.element_type in (3, 4):
        model_path = get_model_path(f"{position_name}_assist")
    elif prob_type == "bonus":
        model_path = get_model_path(f"{position_name}_bonus")
    else:
        return 0.0  # Unsupported combination

    if not model_path.exists():
        return 0.0

    model = _load_model(str(model_path))
    # For classifiers, get probability of the positive class
    proba = model.predict_proba([features])
    return min(1.0, max(0.0, float(proba[0][1])))  # Ensure 0-1 range
