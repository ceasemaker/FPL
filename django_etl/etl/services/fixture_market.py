"""Bookmaker-market calibration for FPL player projections.

The points model already contains FPL fixture difficulty. Market data is used
as a bounded correction to that prior, not as a second full fixture modifier.
When odds are missing, stale, or unavailable, callers receive no adjustment.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Iterable

from django.db.models import Q
from django.utils import timezone

from ..models import FixtureOdds


NEUTRAL_TOTAL_GOALS = 2.70
NEUTRAL_CLEAN_SHEET_PROB = math.exp(-(NEUTRAL_TOTAL_GOALS / 2))
MARKET_CORRECTION_STRENGTH = 0.35
MIN_POINTS_MULTIPLIER = 0.82
MAX_POINTS_MULTIPLIER = 1.18
ODDS_MAX_AGE_HOURS = max(24, int(os.getenv("SOFASCORE_ODDS_MAX_AGE_HOURS", "36")))


@dataclass(frozen=True)
class TeamMarketContext:
    """Position-independent market view of one team's fixture."""

    win_prob: float
    draw_prob: float
    lose_prob: float
    over_25_prob: float | None
    btts_prob: float | None
    expected_team_goals: float
    clean_sheet_prob: float
    fpl_difficulty: int


@dataclass(frozen=True)
class MarketAdjustment:
    """Final bounded correction consumed by the prediction command."""

    multiplier: float
    clean_sheet_prob: float
    market_ease: float
    fdr_ease: float
    fixture_count: int = 1


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _as_float(value: Decimal | float | int | None) -> float | None:
    if value in (None, 0):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 1.0 else None


def remove_vig(*decimal_odds: Decimal | float | int | None) -> tuple[float, ...] | None:
    """Convert decimal prices to fair probabilities that sum to one."""
    prices = [_as_float(value) for value in decimal_odds]
    if any(value is None for value in prices):
        return None
    inverse = [1.0 / value for value in prices if value is not None]
    total = sum(inverse)
    if total <= 0:
        return None
    return tuple(value / total for value in inverse)


def poisson_total_goals_from_over_25(over_probability: float | None) -> float:
    """Infer Poisson total-goals mean from P(total goals >= 3).

    A short bisection is deterministic and avoids adding a numerical package.
    Extreme market probabilities are clipped because the one-parameter model
    is only a fixture-environment approximation.
    """
    if over_probability is None:
        return NEUTRAL_TOTAL_GOALS
    target = _clamp(float(over_probability), 0.05, 0.95)
    low, high = 0.05, 7.0
    for _ in range(50):
        lam = (low + high) / 2
        under_25 = math.exp(-lam) * (1 + lam + (lam * lam / 2))
        if 1 - under_25 < target:
            low = lam
        else:
            high = lam
    return (low + high) / 2


def context_from_odds(
    odds: FixtureOdds,
    *,
    is_home: bool,
    fpl_difficulty: int | None,
) -> TeamMarketContext | None:
    """Derive one team's probabilities and scoring environment from a row."""
    match_probs = remove_vig(odds.home_odds, odds.draw_odds, odds.away_odds)
    if match_probs is None:
        return None
    home_win, draw, away_win = match_probs
    team_win = home_win if is_home else away_win
    opponent_win = away_win if is_home else home_win

    totals = remove_vig(odds.over_odds, odds.under_odds)
    over_25 = totals[0] if totals else None
    btts = remove_vig(odds.btts_yes_odds, odds.btts_no_odds)
    btts_yes = btts[0] if btts else None

    total_goals = poisson_total_goals_from_over_25(over_25)
    # Win and half of draw probability form a stable, normalized scoring share.
    team_strength = team_win + 0.5 * draw
    opponent_strength = opponent_win + 0.5 * draw
    strength_total = team_strength + opponent_strength
    team_share = team_strength / strength_total if strength_total else 0.5
    team_goals = total_goals * team_share
    opponent_goals = max(0.05, total_goals - team_goals)
    poisson_clean_sheet = math.exp(-opponent_goals)

    if btts_yes is None:
        clean_sheet = poisson_clean_sheet
    else:
        # BTTS informs score correlation; retain Poisson as the main estimate
        # and use the no-BTTS price as a conservative secondary signal.
        no_btts = 1 - btts_yes
        shutout_share = team_strength / strength_total if strength_total else 0.5
        btts_clean_sheet = no_btts * (0.5 + 0.5 * shutout_share)
        clean_sheet = 0.75 * poisson_clean_sheet + 0.25 * btts_clean_sheet

    return TeamMarketContext(
        win_prob=team_win,
        draw_prob=draw,
        lose_prob=opponent_win,
        over_25_prob=over_25,
        btts_prob=btts_yes,
        expected_team_goals=team_goals,
        clean_sheet_prob=_clamp(clean_sheet, 0.02, 0.80),
        fpl_difficulty=int(fpl_difficulty or 3),
    )


def position_market_ease(position: int, context: TeamMarketContext) -> float:
    """Map market information to a 0..1 positional fixture-ease score."""
    attack_ease = context.expected_team_goals / (
        context.expected_team_goals + (NEUTRAL_TOTAL_GOALS / 2)
    )
    clean_sheet_ease = context.clean_sheet_prob / (
        context.clean_sheet_prob + NEUTRAL_CLEAN_SHEET_PROB
    )
    over_ease = context.over_25_prob if context.over_25_prob is not None else 0.5
    btts_ease = context.btts_prob if context.btts_prob is not None else 0.5

    if position == 1:  # GK: clean sheets dominate; lower totals also help.
        return _clamp(0.80 * clean_sheet_ease + 0.20 * (1 - over_ease), 0, 1)
    if position == 2:  # DEF: clean-sheet value plus a small attacking environment term.
        return _clamp(0.85 * clean_sheet_ease + 0.15 * attack_ease, 0, 1)
    if position == 3:  # MID: scoring environment, team strength, and BTTS.
        return _clamp(0.60 * attack_ease + 0.25 * context.win_prob + 0.15 * btts_ease, 0, 1)
    # FWD: team scoring expectation is the strongest market input.
    return _clamp(0.70 * attack_ease + 0.20 * context.win_prob + 0.10 * over_ease, 0, 1)


def adjustment_for_context(position: int, context: TeamMarketContext) -> MarketAdjustment:
    market_ease = position_market_ease(position, context)
    # FPL FDR 1..5 becomes 0.9..0.1, leaving room for market disagreement.
    fdr_ease = _clamp(1.1 - 0.2 * context.fpl_difficulty, 0.1, 0.9)
    multiplier = 1 + MARKET_CORRECTION_STRENGTH * (market_ease - fdr_ease)
    return MarketAdjustment(
        multiplier=_clamp(multiplier, MIN_POINTS_MULTIPLIER, MAX_POINTS_MULTIPLIER),
        clean_sheet_prob=context.clean_sheet_prob,
        market_ease=market_ease,
        fdr_ease=fdr_ease,
    )


def _average_adjustments(adjustments: Iterable[MarketAdjustment]) -> MarketAdjustment | None:
    rows = list(adjustments)
    if not rows:
        return None
    count = len(rows)
    return MarketAdjustment(
        multiplier=sum(row.multiplier for row in rows) / count,
        clean_sheet_prob=sum(row.clean_sheet_prob for row in rows) / count,
        market_ease=sum(row.market_ease for row in rows) / count,
        fdr_ease=sum(row.fdr_ease for row in rows) / count,
        fixture_count=count,
    )


def build_market_lookup(gameweek: int) -> dict[tuple[int, int], MarketAdjustment]:
    """Build all team/position adjustments for a GW in one database query."""
    rows = (
        FixtureOdds.objects.filter(
            fixture__fixture__event=gameweek,
            last_updated__gte=timezone.now() - timedelta(hours=ODDS_MAX_AGE_HOURS),
        )
        .filter(
            Q(fixture__fixture__team_h_id__isnull=False)
            & Q(fixture__fixture__team_a_id__isnull=False)
        )
        .select_related("fixture__fixture")
    )
    grouped: dict[tuple[int, int], list[MarketAdjustment]] = {}
    for odds in rows:
        fixture = odds.fixture.fixture
        if fixture is None:
            continue
        for team_id, is_home, difficulty in (
            (fixture.team_h_id, True, fixture.team_h_difficulty),
            (fixture.team_a_id, False, fixture.team_a_difficulty),
        ):
            context = context_from_odds(
                odds,
                is_home=is_home,
                fpl_difficulty=difficulty,
            )
            if context is None or team_id is None:
                continue
            for position in (1, 2, 3, 4):
                grouped.setdefault((team_id, position), []).append(
                    adjustment_for_context(position, context)
                )
    return {
        key: averaged
        for key, values in grouped.items()
        if (averaged := _average_adjustments(values)) is not None
    }


def calibrate_points(base_points: float, adjustment: MarketAdjustment | None) -> float:
    if adjustment is None:
        return max(0.0, float(base_points))
    return max(0.0, float(base_points) * adjustment.multiplier)


def calibrate_probability(
    model_probability: float | None,
    market_probability: float | None,
    *,
    market_weight: float = 0.35,
) -> float | None:
    """Blend independent model and market probabilities without inventing data."""
    if model_probability is None and market_probability is None:
        return None
    if model_probability is None:
        return _clamp(float(market_probability), 0, 1)
    if market_probability is None:
        return _clamp(float(model_probability), 0, 1)
    blended = (1 - market_weight) * float(model_probability) + market_weight * float(market_probability)
    return _clamp(blended, 0, 1)
