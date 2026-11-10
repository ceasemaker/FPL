"""What the website reads about the forecast: stored evaluations and who is available.

Database lookups only. The web process imports this module on every homepage
request, so it must never import pandas or scikit-learn (``service`` does, to
train: ~120 MB, which the 512 MB instance cannot spare in the web process).
"""
from __future__ import annotations

from ..models import Athlete, ModelEvaluation

MODEL_NAME = "points_forecast"
CAPTAIN_EVALUATION = "captain"
MIN_CHANCE = 75  # FPL's "75% chance of playing" is the usual line for a fit player


def latest_evaluation() -> ModelEvaluation | None:
    return ModelEvaluation.objects.filter(name=MODEL_NAME).order_by("-created_at").first()


def captain_evaluation() -> ModelEvaluation | None:
    """The latest captain backtest (``manage.py evaluate_captain``)."""
    return ModelEvaluation.objects.filter(name=CAPTAIN_EVALUATION).order_by("-created_at").first()


def captain_accepted() -> bool:
    """Whether the captain backtest passed (the newer ``captain`` evaluation wins)."""
    captain = captain_evaluation()
    if captain:
        return captain.accepted
    evaluation = latest_evaluation()
    return bool(evaluation and evaluation.summary.get("accepted", {}).get("captain"))


def available_elements() -> set[int]:
    """Players FPL lists as available, or doubtful with at least a 75% chance."""
    ids = set()
    for a in Athlete.objects.filter(removed=False).values("id", "status", "chance_of_playing_next_round"):
        chance = a["chance_of_playing_next_round"]
        if a["status"] == "a" or (a["status"] == "d" and (chance is None or chance >= MIN_CHANCE)):
            ids.add(a["id"])
    return ids
