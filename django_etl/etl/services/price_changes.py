"""FPL's own price-change tracker, from bootstrap-static.

Since 2026/27 FPL publishes, per player:

* ``price_change_percent``: progress towards the next change (+100 means a
  rise is due, -100 a fall);
* ``price_change_projections``: FPL's estimate for each of the next three
  price-change runs (``offset`` 0, 1, 2), with ``projected_percent`` and a
  ``likelihood`` from -5 (very likely to drop) to +5 (very likely to rise);
* ``price_change_hourly_rate``: the net transfer rate behind the trend;
* ``price_change_locked_until``: a player who just changed can't change again
  until then;

plus, in ``game_config``, the times of the next price-change runs and when the
tracker was last updated. FPL refreshes it every 15 minutes; so does
``refresh_price_changes`` (in the worker: one request and a bulk update).
"""
from __future__ import annotations

import logging

from django.core.cache import cache
from django.utils.dateparse import parse_datetime

from ..models import Athlete

logger = logging.getLogger(__name__)

META_KEY = "fpl:price-change-meta"
PAYLOAD_KEY = "fpl:price-changes:v1"
FIELDS = ["price_change_percent", "price_change_projections", "price_change_hourly_rate",
          "price_change_locked_until", "price_change_calibrating"]

# FPL's likelihood score -> the label FPL's own tracker shows.
LABELS = {5: "Very likely to rise", 4: "Likely to rise", -4: "Likely to drop", -5: "Very likely to drop"}


def label(likelihood: int | None) -> str:
    return LABELS.get(likelihood or 0, "Unlikely to change")


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def price_change_fields(element: dict) -> dict:
    """The tracker fields for one bootstrap element, ready for the Athlete row."""
    locked = element.get("price_change_locked_until")
    return {
        "price_change_percent": _float(element.get("price_change_percent")),
        "price_change_projections": [
            {"offset": p.get("offset"), "percent": _float(p.get("projected_percent")), "likelihood": p.get("likelihood")}
            for p in element.get("price_change_projections") or []
        ],
        "price_change_hourly_rate": element.get("price_change_hourly_rate"),
        "price_change_locked_until": parse_datetime(locked) if locked else None,
        "price_change_calibrating": bool(element.get("price_change_calibrating")),
    }


def store_meta(bootstrap: dict) -> dict:
    """Keep the next price-change times and FPL's last-updated stamp."""
    config = bootstrap.get("game_config") or {}
    meta = {
        "deadlines": (config.get("settings") or {}).get("price_change_deadlines") or [],
        "lastUpdated": (config.get("status") or {}).get("price_change_last_updated"),
    }
    cache.set(META_KEY, meta, None)
    cache.delete(PAYLOAD_KEY)
    return meta


def refresh_price_changes(client=None) -> dict:
    """Update only the tracker fields on every player (cheap; runs every 15 minutes)."""
    from .fpl_client import FPLClient

    if client is None:
        with FPLClient() as fpl:
            bootstrap = fpl.get_bootstrap_static()
    else:
        bootstrap = client.get_bootstrap_static()
    fields = {e["id"]: price_change_fields(e) for e in bootstrap.get("elements", []) if "id" in e}
    athletes = list(Athlete.objects.filter(id__in=fields).only("id", *FIELDS))
    for athlete in athletes:
        for name, value in fields[athlete.id].items():
            setattr(athlete, name, value)
    Athlete.objects.bulk_update(athletes, FIELDS, batch_size=500)
    meta = store_meta(bootstrap)
    return {"updated": len(athletes), "lastUpdated": meta["lastUpdated"]}


def build_payload() -> dict:
    """Every active player's tracker row, plus the countdown times."""
    cached = cache.get(PAYLOAD_KEY)
    if cached:
        return cached
    rows = []
    for a in (Athlete.objects.filter(removed=False).exclude(price_change_percent=None)
              .select_related("team").only("id", "web_name", "element_type", "now_cost", "selected_by_percent", "status",
                                           "team__short_name", "team__code", *FIELDS)):
        next_run = (a.price_change_projections or [{}])[0] if a.price_change_projections else {}
        rows.append({
            "id": a.id,
            "name": a.web_name,
            "team": a.team.short_name if a.team else None,
            "position": {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}.get(a.element_type, ""),
            "price": (a.now_cost or 0) / 10,
            "ownership": float(a.selected_by_percent) if a.selected_by_percent is not None else None,
            "status": a.status,
            "progress": a.price_change_percent,
            "predicted": next_run.get("percent"),
            "likelihood": next_run.get("likelihood"),
            "label": label(next_run.get("likelihood")),
            "projections": a.price_change_projections,
            "hourlyRate": a.price_change_hourly_rate,
            "trend": "up" if (a.price_change_hourly_rate or 0) > 0 else "down" if (a.price_change_hourly_rate or 0) < 0 else "flat",
            "lockedUntil": a.price_change_locked_until.isoformat() if a.price_change_locked_until else None,
            "calibrating": a.price_change_calibrating,
        })
    rows.sort(key=lambda r: -abs(r["progress"] or 0))
    payload = {"meta": cache.get(META_KEY) or {"deadlines": [], "lastUpdated": None}, "players": rows}
    cache.set(PAYLOAD_KEY, payload, 15 * 60)
    return payload
