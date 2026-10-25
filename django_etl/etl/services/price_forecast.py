"""Seven-day price-rise forecast, and the backtest that decides whether it is shown.

FPL's own tracker looks about two days ahead. This model asks a longer
question: will this player's price rise within the next seven days? It learns
from the season's price snapshots (one per player per day):

- net transfers (in minus out) over the last 1 and 3 days, and since the
  player's last price change, scaled by his ownership;
- days since that change, his price, ownership and form.

The backtest is chronological: train on the earlier days, predict the later
ones it never saw, and compare with a simple rule (flag the players with the
most net transfers since their last change, per owner). The forecast is only
published when it is right often enough and clearly beats that rule; the
result is stored as ModelEvaluation "price_forecast" either way.
"""
from __future__ import annotations

import math

from django.core.cache import cache

from ..models import ModelEvaluation, PriceSnapshot

HORIZON_DAYS = 7
THRESHOLD = 0.5
MIN_PRECISION = 0.6
MIN_MARGIN = 0.05
MIN_FLAGS = 30
FEATURES = ["net1", "net3", "net_since", "days_since", "price", "own", "form"]


def _signed_log(x: float) -> float:
    return math.copysign(math.log1p(abs(x)), x)


def daily_panel():
    """One row per player per day (the day's last snapshot), with features and the label."""
    import pandas as pd

    rows = list(PriceSnapshot.objects.order_by("snapshot_time").values_list(
        "athlete_id", "snapshot_time", "cost", "transfers_in_total", "transfers_out_total", "selected_by_percent", "form"))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["athlete", "time", "cost", "tin", "tout", "own", "form"])
    df["day"] = df["time"].dt.tz_convert("UTC").dt.normalize()
    df = df.sort_values("time").groupby(["athlete", "day"], as_index=False).last()
    df["own"] = df["own"].astype(float)
    df["form"] = df["form"].astype(float)
    df["net"] = (df["tin"] - df["tout"]).astype(float)
    out = []
    for _, g in df.groupby("athlete"):
        g = g.sort_values("day").reset_index(drop=True)
        g["net1"] = g["net"].diff(1)
        g["net3"] = g["net"].diff(3)
        changed = g["cost"].diff().fillna(0).ne(0)
        g["change_id"] = changed.cumsum()
        g["net_since"] = g["net"] - g.groupby("change_id")["net"].transform("first")
        g["days_since"] = g.groupby("change_id").cumcount()
        future = g.set_index("day")["cost"]
        g["rise"] = [
            int(bool((future[(future.index > d) & (future.index <= d + pd.Timedelta(days=HORIZON_DAYS))] > c).any()))
            for d, c in zip(g["day"], g["cost"])
        ]
        g["has_future"] = g["day"] + pd.Timedelta(days=HORIZON_DAYS) <= g["day"].max()
        out.append(g)
    panel = pd.concat(out, ignore_index=True).dropna(subset=["net1", "net3"])
    scale = panel["own"].clip(lower=0.1)
    for col in ("net1", "net3", "net_since"):
        panel[col] = (panel[col] / scale).map(_signed_log)
    panel["price"] = panel["cost"].astype(float) / 10
    return panel


def backtest(save: bool = True) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    panel = daily_panel()
    usable = panel[panel["has_future"]] if len(panel) else panel
    days = sorted(usable["day"].unique()) if len(usable) else []
    if len(days) < 14:
        result = {"accepted": False, "reason": f"Only {len(days)} days with a full week after them; need 14."}
        if save:
            ModelEvaluation.objects.create(name="price_forecast", version="v1", accepted=False, summary=result)
            cache.delete(CACHE_KEY)
        return result
    cutoff = days[int(len(days) * 0.6)]
    train, test = usable[usable["day"] < cutoff], usable[usable["day"] >= cutoff]
    model = LogisticRegression(max_iter=1000).fit(train[FEATURES], train["rise"])
    prob = model.predict_proba(test[FEATURES])[:, 1]
    flagged = prob >= THRESHOLD
    hits = int((test["rise"].values[flagged] == 1).sum())
    n_flag = int(flagged.sum())
    positives = int(test["rise"].sum())
    precision = hits / n_flag if n_flag else 0.0
    recall = hits / positives if positives else 0.0
    # The simple rule, given the same number of flags: most net transfers per owner since the last change.
    order = test["net_since"].values.argsort()[::-1][:n_flag]
    rule_precision = float(test["rise"].values[order].mean()) if n_flag else 0.0
    auc = float(roc_auc_score(test["rise"], prob)) if 0 < positives < len(test) else None
    accepted = bool(n_flag >= MIN_FLAGS and precision >= MIN_PRECISION and precision - rule_precision >= MIN_MARGIN)
    result = {
        "accepted": accepted, "horizonDays": HORIZON_DAYS, "threshold": THRESHOLD,
        "trainDays": int(train["day"].nunique()), "testDays": int(test["day"].nunique()),
        "testFrom": str(cutoff.date()), "playerDays": int(len(test)), "rises": positives, "baseRate": round(positives / len(test), 4),
        "flagged": n_flag, "precision": round(precision, 3), "recall": round(recall, 3), "rulePrecision": round(rule_precision, 3),
        "auc": round(auc, 3) if auc is not None else None,
        "bar": {"minPrecision": MIN_PRECISION, "minMarginOverRule": MIN_MARGIN, "minFlags": MIN_FLAGS},
    }
    if save:
        ModelEvaluation.objects.create(name="price_forecast", version="v1", accepted=accepted, summary=result)
        publish(panel, result if accepted else None)
    return result


CACHE_KEY = "price-forecast:current:v1"


def publish(panel, record: dict | None) -> None:
    """Store today's chances for the web to read (run in the nightly job, never in a request)."""
    if record is None:
        cache.delete(CACHE_KEY)
        return
    from sklearn.linear_model import LogisticRegression

    train = panel[panel["has_future"]]
    model = LogisticRegression(max_iter=1000).fit(train[FEATURES], train["rise"])
    today = panel[panel["day"] == panel["day"].max()]
    prob = model.predict_proba(today[FEATURES])[:, 1]
    payload = {"record": record, "chances": {str(a): round(float(p), 3) for a, p in zip(today["athlete"], prob) if p >= THRESHOLD}}
    cache.set(CACHE_KEY, payload, 30 * 60 * 60)


def current() -> dict | None:
    """Today's seven-day rise chances, or None when the latest backtest didn't accept the model."""
    return cache.get(CACHE_KEY)
