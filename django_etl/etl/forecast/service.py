"""Production side of the forecast: train, predict, log shadow picks, score them.

``run_forecast`` is called after each daily ETL pass:

1. Trains on every finished gameweek we hold (past seasons plus this season).
   A gameweek still in progress is not used: its numbers are incomplete.
2. Stores the model in Postgres and writes forecasts for the next three
   gameweeks (only the next one is what the backtest validated).
3. Before the deadline, logs each strategy's captain pick for the next
   gameweek. The latest run before the deadline wins; after it, picks freeze.
4. Scores the picks of finished gameweeks.
"""
from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
from django.db import transaction
from django.utils import timezone

from ..models import (
    Athlete,
    AthleteStat,
    DeadlineSnapshot,
    ForecastPrediction,
    GameweekHistory,
    GameweekSummary,
    ModelArtifact,
    ModelEvaluation,
    ShadowPick,
)
from . import VERSION
from .data import load_fixtures, load_players
from .features import build_features, future_rows
from .model import dumps, fit, predict, training_rows

logger = logging.getLogger(__name__)

MODEL_NAME = "points_forecast"
HORIZON = 3
KEEP_ARTIFACTS = 3
MIN_CHANCE = 75  # FPL's "75% chance of playing" is the usual line for a fit player


def latest_evaluation() -> ModelEvaluation | None:
    return ModelEvaluation.objects.filter(name=MODEL_NAME).order_by("-created_at").first()


def captain_accepted() -> bool:
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


def _season_and_weeks(now: datetime) -> tuple[int, int | None, datetime | None, set[int]] | None:
    season = GameweekSummary.objects.order_by("-season").values_list("season", flat=True).first()
    if season is None:
        return None
    weeks = list(GameweekSummary.objects.filter(season=season).values("gameweek", "deadline_time", "finished"))
    finished = {w["gameweek"] for w in weeks if w["finished"]}
    upcoming = sorted((w["deadline_time"], w["gameweek"]) for w in weeks if w["deadline_time"] and w["deadline_time"] > now)
    if not upcoming:
        return season, None, None, finished
    deadline, gameweek = upcoming[0]
    return season, gameweek, deadline, finished


def run_forecast(now: datetime | None = None, log=logger.info) -> dict:
    now = now or timezone.now()
    context = _season_and_weeks(now)
    if context is None:
        return {"status": "no_season"}
    season, next_gw, deadline, finished = context
    settled = settle_picks(season, finished)
    if next_gw is None:
        return {"status": "season_over", "settled": settled}

    players = load_players()
    fixtures = load_fixtures()
    in_progress = (players["season"] == season) & ~players["gameweek"].isin(finished)
    players = players[~in_progress]
    targets = [gw for gw in range(next_gw, next_gw + HORIZON)
               if ((fixtures["season"] == season) & (fixtures["gameweek"] == gw)).any()]
    future = future_rows(players, season, targets)
    features = build_features(pd.concat([players, future], ignore_index=True), fixtures)

    train = training_rows(features)
    model = fit(train)
    last_week = int(train.loc[train["season"] == season, "gameweek"].max()) if (train["season"] == season).any() else 0
    ModelArtifact.objects.create(
        name=MODEL_NAME, version=VERSION, trained_through_season=season, trained_through_gameweek=last_week,
        training_rows=len(train), payload=dumps(model), metadata={"targets": targets},
    )
    stale = ModelArtifact.objects.filter(name=MODEL_NAME).order_by("-created_at").values_list("id", flat=True)[KEEP_ARTIFACTS:]
    ModelArtifact.objects.filter(id__in=list(stale)).delete()

    upcoming = features[(features["season"] == season) & features["gameweek"].isin(targets)].copy()
    upcoming["pred"] = predict(model, upcoming)
    upcoming = upcoming.dropna(subset=["pred"])
    with transaction.atomic():
        ForecastPrediction.objects.filter(season=season, gameweek__in=targets).delete()
        ForecastPrediction.objects.bulk_create([
            ForecastPrediction(
                season=season, gameweek=int(r.gameweek), element=int(r.element), code=int(r.code),
                predicted_points=round(float(r.pred), 3), horizon=int(r.gameweek) - next_gw + 1, model_version=VERSION,
            )
            for r in upcoming.itertuples(index=False)
        ])

    picks = 0
    if deadline and now < deadline:
        picks = log_picks(season, next_gw, upcoming[upcoming["gameweek"] == next_gw], now)
    result = {"status": "ok", "season": season, "next_gameweek": next_gw, "trained_rows": len(train),
              "forecasts": len(upcoming), "picks_logged": picks, "settled": settled}
    log(f"Forecast {VERSION}: {result}")
    return result


def log_picks(season: int, gameweek: int, forecast: pd.DataFrame, now: datetime) -> int:
    available = available_elements()
    names = dict(Athlete.objects.values_list("id", "web_name"))
    codes = dict(Athlete.objects.values_list("id", "code"))
    picks: dict[str, tuple[int, float | None]] = {}

    candidates = forecast[forecast["element"].isin(available)]
    if not candidates.empty:
        top = candidates.loc[candidates["pred"].idxmax()]
        picks["model"] = (int(top["element"]), round(float(top["pred"]), 2))

    snapshot = (
        DeadlineSnapshot.objects.filter(season=season, gameweek=gameweek, element__in=available, ep_next__isnull=False)
        .order_by("-ep_next").values_list("element", "ep_next").first()
    )
    if snapshot:
        picks["ep_next"] = (snapshot[0], snapshot[1])

    last_week = AthleteStat.objects.filter(game_week__lt=gameweek).order_by("-game_week").values_list("game_week", flat=True).first()
    if last_week:
        starters = set(AthleteStat.objects.filter(game_week=last_week, starts__gt=0).values_list("athlete_id", flat=True))
        premium = (
            Athlete.objects.filter(id__in=available & starters, element_type__in=(3, 4))
            .order_by("-now_cost", "-form").values_list("id", flat=True).first()
        )
        if premium:
            picks["premium_form"] = (premium, None)

    for strategy, (element, predicted) in picks.items():
        ShadowPick.objects.update_or_create(
            season=season, gameweek=gameweek, strategy=strategy,
            defaults={"element": element, "code": codes.get(element, 0), "web_name": names.get(element, ""),
                      "predicted": predicted, "picked_at": now},
        )
    return len(picks)


def settle_picks(season: int, finished: set[int]) -> int:
    """Score finished weeks, and record FPL's most-captained player as a baseline."""
    names = dict(Athlete.objects.values_list("id", "web_name"))
    codes = dict(Athlete.objects.values_list("id", "code"))
    for summary in GameweekSummary.objects.filter(season=season, gameweek__in=finished, most_captained__isnull=False):
        # Only weeks we were already logging picks for, so the record has no back-filled history.
        if not ShadowPick.objects.filter(season=season, gameweek=summary.gameweek, strategy="model").exists():
            continue
        ShadowPick.objects.get_or_create(
            season=season, gameweek=summary.gameweek, strategy="most_captained",
            defaults={"element": summary.most_captained, "code": codes.get(summary.most_captained, 0),
                      "web_name": names.get(summary.most_captained, ""), "picked_at": summary.deadline_time or timezone.now()},
        )
    settled = 0
    for pick in ShadowPick.objects.filter(season=season, gameweek__in=finished, actual_points__isnull=True):
        points = GameweekHistory.objects.filter(season=season, gameweek=pick.gameweek, code=pick.code).values_list("total_points", flat=True).first()
        pick.actual_points = points or 0
        pick.settled_at = timezone.now()
        pick.save(update_fields=["actual_points", "settled_at"])
        settled += 1
    return settled
