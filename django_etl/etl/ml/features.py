"""Feature extraction for ML prediction models.

Every feature for (athlete, game_week) must be knowable at that gameweek's
deadline. Concretely:

- Performance aggregates only read ``AthleteStat`` rows with
  ``game_week < game_week`` — never the target row or anything after it.
- Ownership, transfer and price context comes from the as-of-deadline columns
  on ``AthleteStat`` (populated from element-summary ``history``), not from the
  live ``Athlete`` row. The live row is used only when predicting the next
  unplayed gameweek, where "now" *is* the deadline state.
- Fixture context reads every fixture the team has in the target gameweek, so
  double and blank gameweeks are represented rather than collapsed.

Fields that cannot be reconstructed historically (``chance_of_playing_*``,
``selected_by_percent``) are deliberately not features.
"""
from decimal import Decimal
from typing import Optional

from django.db.models import Count, Max, Q, Sum

from etl.models import Athlete, AthleteStat, Fixture

FORM_WINDOW = 3
DEFAULT_FDR = 3

# Ordered feature vector consumed by every model. Changing this invalidates
# any saved artifacts under etl/ml_models.
FEATURE_NAMES = (
    "position",
    "form_3gw",
    "ppg_to_date",
    "xg_3gw",
    "xa_3gw",
    "xgc_3gw",
    "minutes_3gw",
    "games_to_date",
    "fixture_count",
    "home_fixtures",
    "opponent_fdr",
    "transfers_balance",
    "value",
)


def feature_vector(feature_dict: dict) -> list:
    """Project an ``extract_features`` result onto the ordered vector."""
    return [feature_dict[name] for name in FEATURE_NAMES]


def latest_played_gameweek() -> int:
    """Highest gameweek with recorded per-player stats (0 when none)."""
    return AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"] or 0


def _gameweek_context(athlete: Athlete, game_week: int) -> tuple[Optional[dict], Optional[str]]:
    """
    Ownership/transfer/price state as of the ``game_week`` deadline.

    Returns ``(context, source)`` where source is ``"gameweek"`` (stored
    as-of row), ``"live"`` (current Athlete row, only valid for the next
    unplayed gameweek) or ``None`` when no honest value exists.
    """
    stat = (
        AthleteStat.objects.filter(athlete_id=athlete.id, game_week=game_week)
        .only("transfers_in", "transfers_out", "value", "selected")
        .first()
    )
    if stat is not None and stat.value is not None and stat.transfers_in is not None:
        return (
            {
                "transfers_balance": (stat.transfers_in or 0) - (stat.transfers_out or 0),
                "value": stat.value,
            },
            "gameweek",
        )

    if game_week > latest_played_gameweek():
        # Predicting a gameweek that has not kicked off: the live bootstrap
        # values are the deadline state, and share units with history rows
        # (transfers_*_event == per-round transfers, now_cost == value).
        return (
            {
                "transfers_balance": (athlete.transfers_in_event or 0)
                - (athlete.transfers_out_event or 0),
                "value": athlete.now_cost or 0,
            },
            "live",
        )

    return None, None


def _fixture_context(team_id: Optional[int], game_week: int) -> dict:
    if team_id is None:
        return {"fixture_count": 0, "home_fixtures": 0, "opponent_fdr": DEFAULT_FDR}

    fixtures = Fixture.objects.filter(
        Q(event=game_week) & (Q(team_h_id=team_id) | Q(team_a_id=team_id))
    ).only("team_h_id", "team_h_difficulty", "team_a_difficulty")

    count = 0
    home = 0
    fdr_total = 0
    for fixture in fixtures:
        count += 1
        if fixture.team_h_id == team_id:
            home += 1
            fdr_total += fixture.team_h_difficulty or DEFAULT_FDR
        else:
            fdr_total += fixture.team_a_difficulty or DEFAULT_FDR

    return {
        "fixture_count": count,
        "home_fixtures": home,
        "opponent_fdr": (fdr_total / count) if count else DEFAULT_FDR,
    }


def extract_features(athlete_id: int, game_week: int) -> Optional[dict]:
    """
    Extract deadline-safe features for ``athlete_id`` in ``game_week``.

    The returned dict carries the ``FEATURE_NAMES`` entries plus metadata:
    ``athlete_id`` and ``context_source`` (``"gameweek"``, ``"live"`` or
    ``None``). Callers building training sets should skip rows whose
    ``context_source`` is ``None`` rather than impute.
    """
    athlete = Athlete.objects.filter(id=athlete_id).only(
        "id", "element_type", "team_id", "transfers_in_event",
        "transfers_out_event", "now_cost",
    ).first()
    if not athlete:
        return None

    prior = AthleteStat.objects.filter(athlete_id=athlete_id, game_week__lt=game_week)

    form_stats = prior.filter(game_week__gte=max(1, game_week - FORM_WINDOW)).aggregate(
        points=Sum("total_points"),
        minutes=Sum("minutes"),
        xg=Sum("expected_goals"),
        xa=Sum("expected_assists"),
        xgc=Sum("expected_goals_conceded"),
    )

    season = prior.aggregate(total_points=Sum("total_points"), games=Count("id"))
    games_to_date = season["games"] or 0
    ppg_to_date = (
        float(Decimal(season["total_points"] or 0) / games_to_date) if games_to_date else 0.0
    )

    context, context_source = _gameweek_context(athlete, game_week)
    context = context or {"transfers_balance": 0, "value": 0}

    features = {
        "athlete_id": athlete_id,
        "context_source": context_source,
        "position": athlete.element_type or 0,
        "form_3gw": int(form_stats["points"] or 0),
        "ppg_to_date": ppg_to_date,
        "xg_3gw": float(form_stats["xg"] or 0),
        "xa_3gw": float(form_stats["xa"] or 0),
        "xgc_3gw": float(form_stats["xgc"] or 0),
        "minutes_3gw": int(form_stats["minutes"] or 0),
        "games_to_date": games_to_date,
        "transfers_balance": context["transfers_balance"],
        "value": context["value"],
    }
    features.update(_fixture_context(athlete.team_id, game_week))
    return features


def iter_training_rows(athlete_ids: Optional[list[int]] = None):
    """
    Yield ``(stat, feature_dict)`` for every trainable gameweek row.

    GW1 has no prior history and rows without stored as-of context are
    skipped — they would otherwise be silently imputed with zeros.
    """
    stats = AthleteStat.objects.filter(game_week__gt=1)
    if athlete_ids is not None:
        stats = stats.filter(athlete_id__in=athlete_ids)

    for stat in stats.order_by("athlete_id", "game_week"):
        feature_dict = extract_features(stat.athlete_id, stat.game_week)
        if not feature_dict or feature_dict["context_source"] != "gameweek":
            continue
        yield stat, feature_dict


def get_training_data() -> tuple[list[list], list[int]]:
    """Return ``(X, y)`` for the universal points regressor."""
    features_list: list[list] = []
    targets_list: list[int] = []
    for stat, feature_dict in iter_training_rows():
        features_list.append(feature_vector(feature_dict))
        targets_list.append(stat.total_points)
    return features_list, targets_list
