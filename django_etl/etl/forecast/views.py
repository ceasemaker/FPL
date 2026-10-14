"""Model Lab API: the forecast's backtest verdict and its live shadow record."""
from __future__ import annotations

from collections import defaultdict

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from ..models import ForecastPrediction, GameweekSummary, ModelArtifact, ShadowPick
from .service import MODEL_NAME, captain_accepted, latest_evaluation

STRATEGY_LABELS = dict(ShadowPick.STRATEGIES)


@require_GET
def forecast_lab(request):
    evaluation = latest_evaluation()
    accepted = captain_accepted()
    artifact = ModelArtifact.objects.filter(name=MODEL_NAME).order_by("-created_at").first()
    now = timezone.now()

    season = GameweekSummary.objects.order_by("-season").values_list("season", flat=True).first()
    deadlines = dict(GameweekSummary.objects.filter(season=season).values_list("gameweek", "deadline_time")) if season else {}
    upcoming = sorted((d, gw) for gw, d in deadlines.items() if d and d > now)
    next_gw = upcoming[0][1] if upcoming else None

    weeks: dict[int, dict] = defaultdict(dict)
    for pick in ShadowPick.objects.filter(season=season).order_by("gameweek"):
        deadline = deadlines.get(pick.gameweek)
        # A pick for a week whose deadline hasn't passed stays hidden unless
        # the model has passed its backtest: until then it's an experiment,
        # not advice. Once the deadline passes it can't change, so it's shown.
        if (deadline is None or deadline > now) and not accepted:
            continue
        weeks[pick.gameweek][pick.strategy] = {
            "label": STRATEGY_LABELS.get(pick.strategy, pick.strategy),
            "player": pick.web_name,
            "predicted": pick.predicted,
            "points": pick.actual_points,
        }
    record = [
        {"gameweek": gw, "deadline": deadlines.get(gw), "settled": all(p["points"] is not None for p in picks.values()), "picks": picks}
        for gw, picks in sorted(weeks.items(), reverse=True)
    ]
    totals: dict[str, dict] = {}
    for week in record:
        if not week["settled"] or "model" not in week["picks"]:
            continue
        for strategy, pick in week["picks"].items():
            entry = totals.setdefault(strategy, {"label": pick["label"], "points": 0, "weeks": 0})
            entry["points"] += pick["points"] or 0
            entry["weeks"] += 1

    pending = ShadowPick.objects.filter(season=season, gameweek=next_gw, strategy="model").exists() if next_gw else False
    payload = {
        "accepted": accepted,
        "season": season,
        "nextGameweek": next_gw,
        "nextDeadline": upcoming[0][0] if upcoming else None,
        "nextPickLogged": pending,
        "model": {
            "version": artifact.version if artifact else None,
            "trainedAt": artifact.created_at if artifact else None,
            "trainingRows": artifact.training_rows if artifact else None,
            "trainedThrough": (
                {"season": artifact.trained_through_season, "gameweek": artifact.trained_through_gameweek} if artifact else None
            ),
        },
        "evaluation": None,
        "record": record,
        "totals": totals,
        "forecastCount": ForecastPrediction.objects.filter(season=season, gameweek=next_gw).count() if next_gw else 0,
    }
    if evaluation:
        summary = evaluation.summary
        payload["evaluation"] = {
            "createdAt": evaluation.created_at,
            "version": evaluation.version,
            "testSeasons": summary.get("test_seasons"),
            "accuracy": summary.get("accuracy"),
            "captain": {k: summary.get("captain", {}).get(k) for k in ("weeks", "points_per_week", "versus", "by_season", "regret")},
            "lineup": summary.get("lineup"),
            "accepted": summary.get("accepted"),
        }
    return JsonResponse(payload)
