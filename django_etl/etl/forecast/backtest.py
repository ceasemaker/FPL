"""Walk-forward evaluation of the points forecast, and the gate.

For each test gameweek the model is trained only on weeks before it (earlier
seasons plus this season so far), exactly as it would have been run live.
Its captain pick and its lineup choices are then compared with fixed
baselines on the same weeks:

Captain baselines
    elite      the player most captained by that season's eventual top-100
               managers that week (hard, and survivorship-biased: these
               managers are in the sample *because* their picks worked)
    premium    the most expensive midfielder or forward who started last week
    form       the best points-per-match over the last six, among regular starters

Lineup baselines (on the top-100 managers' real 15-man squads)
    manager    the XI, bench order and captain the manager actually chose
    form       the XI and captain picked by last-six form

Differences are averaged per gameweek and bootstrapped by gameweek (weeks are
the independent unit; players within a week are not). The model is accepted
for captaincy only if the lower end of the 95% interval is above zero against
*every* captain baseline. Nothing about this rule is tuned after seeing results.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from . import VERSION
from .features import build_features
from .model import fit, predict
from .selection import Lineup, Player, choose_lineup, score_lineup

TEST_SEASONS = (2023, 2024, 2025)
BOOTSTRAP_DRAWS = 10_000
SEED = 20261014


def walk_forward(features: pd.DataFrame, test_seasons=TEST_SEASONS, retrain_every: int = 1, log=print) -> pd.DataFrame:
    """Predictions for every test week, each from a model trained on earlier weeks only."""
    t = features["season"] * 100 + features["gameweek"]
    played = features["total_points"].notna()
    out, model = [], None
    weeks = sorted({(s, g) for s, g in features.loc[features["season"].isin(test_seasons), ["season", "gameweek"]].itertuples(index=False)})
    started = time.time()
    for index, (season, gameweek) in enumerate(weeks):
        now = season * 100 + gameweek
        if model is None or index % retrain_every == 0:
            model = fit(features[played & (t < now)])
        week = features[(t == now) & played].copy()
        week["pred"] = predict(model, week)
        out.append(week)
        if gameweek % 10 == 0:
            log(f"  {season}/{(season + 1) % 100:02d} GW{gameweek} ({time.time() - started:.0f}s)")
    return pd.concat(out, ignore_index=True)


def _bootstrap(diffs: np.ndarray, rng: np.random.Generator) -> dict:
    diffs = np.asarray(diffs, dtype=float)
    n = len(diffs)
    draws = diffs[rng.integers(0, n, size=(BOOTSTRAP_DRAWS, n))].mean(axis=1)
    low, high = np.percentile(draws, [2.5, 97.5])
    return {"mean": round(float(diffs.mean()), 3), "low": round(float(low), 3), "high": round(float(high), 3), "weeks": n}


def captain_picks(preds: pd.DataFrame, squads: pd.DataFrame) -> pd.DataFrame:
    """One row per test week with each strategy's pick and its points (single, not doubled)."""
    elite = (
        squads[squads["is_captain"] == 1]
        .groupby(["season", "gameweek", "code"]).size().rename("n").reset_index()
        .sort_values("n", ascending=False).drop_duplicates(["season", "gameweek"])
    )
    elite = elite.set_index(["season", "gameweek"])["code"]
    rows = []
    for (season, gameweek), week in preds.groupby(["season", "gameweek"]):
        points = week.set_index("code")["total_points"]
        names = week.set_index("code")["web_name"]

        def pick(frame, column):
            frame = frame.dropna(subset=[column])
            return None if frame.empty else int(frame.loc[frame[column].idxmax(), "code"])

        attackers = week[(week["position"] >= 3) & (week["mins_l1"] >= 60)]
        regulars = week[week["mins_m3"] >= 60]
        choice = {
            "model": pick(week, "pred"),
            "premium": pick(attackers.assign(key=attackers["start_price"] + attackers["pts_m6"].fillna(0) / 100), "key"),
            "form": pick(regulars, "pts_m6"),
            "elite": int(elite.get((season, gameweek))) if (season, gameweek) in elite.index else None,
            "best": int(week.loc[week["total_points"].idxmax(), "code"]),
        }
        row = {"season": int(season), "gameweek": int(gameweek)}
        for strategy, code in choice.items():
            row[f"{strategy}_code"] = code
            row[f"{strategy}_name"] = None if code is None else names.get(code)
            # A pick with no row that week had no fixture or didn't feature: 0 points.
            row[f"{strategy}_points"] = None if code is None else float(points.get(code, 0))
        rows.append(row)
    return pd.DataFrame(rows)


def lineup_scores(preds: pd.DataFrame, squads: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    """Score the model's, the manager's and form's lineups on each real top-100 squad."""
    lookup = preds.set_index(["season", "gameweek", "code"])[["pred", "pts_m6"]]
    actual = players.set_index(["season", "gameweek", "code"])[["minutes", "total_points"]]
    squads = squads[squads["season"].isin(preds["season"].unique())]
    squads = squads.join(lookup, on=["season", "gameweek", "code"]).join(actual, on=["season", "gameweek", "code"])
    squads[["minutes", "total_points"]] = squads[["minutes", "total_points"]].fillna(0)
    squads[["pred", "pts_m6"]] = squads[["pred", "pts_m6"]].fillna(0)
    rows = []
    for (season, gameweek, manager), squad in squads.groupby(["season", "gameweek", "manager"]):
        squad = squad.sort_values("slot")

        def players_by(column):
            return [Player(int(r.code), int(r.position), float(getattr(r, column)), float(r.minutes), float(r.total_points))
                    for r in squad.itertuples(index=False)]

        manual = players_by("pred")
        starters, bench = manual[:11], manual[11:]
        captain = next(p for p, r in zip(manual, squad.itertuples(index=False)) if r.is_captain)
        vice = next(p for p, r in zip(manual, squad.itertuples(index=False)) if r.is_vice_captain)
        rows.append({
            "season": season, "gameweek": gameweek, "manager": manager,
            "manager_points": score_lineup(Lineup(starters, bench, captain, vice)),
            "model_points": score_lineup(choose_lineup(players_by("pred"))),
            "form_points": score_lineup(choose_lineup(players_by("pts_m6"))),
        })
    return pd.DataFrame(rows)


def evaluate(players: pd.DataFrame, fixtures: pd.DataFrame, squads: pd.DataFrame,
             test_seasons=TEST_SEASONS, retrain_every: int = 1, log=print) -> dict:
    rng = np.random.default_rng(SEED)
    log("Building features")
    features = build_features(players, fixtures)
    log(f"  {len(features):,} player-weeks with a fixture")
    log("Walk-forward predictions")
    preds = walk_forward(features, test_seasons, retrain_every, log)

    scored = preds.dropna(subset=["pred"])
    form = scored["pts_m6"].fillna(scored["pts90_prev"].fillna(0) * scored["min_share_prev"].fillna(0))
    accuracy = {
        "player_weeks": int(len(scored)),
        "model_mae": round(float((scored["pred"] - scored["total_points"]).abs().mean()), 3),
        "form_mae": round(float((form - scored["total_points"]).abs().mean()), 3),
        "model_corr": round(float(scored["pred"].corr(scored["total_points"])), 3),
        "form_corr": round(float(form.corr(scored["total_points"])), 3),
    }

    log("Captain comparison")
    picks = captain_picks(preds, squads)
    captain = {"weeks": int(len(picks)), "points_per_week": {}, "versus": {}}
    for strategy in ("model", "elite", "premium", "form", "best"):
        values = picks[f"{strategy}_points"].dropna()
        captain["points_per_week"][strategy] = round(float(values.mean()), 3)
    for baseline in ("elite", "premium", "form"):
        paired = picks.dropna(subset=[f"{baseline}_points", "model_points"])
        captain["versus"][baseline] = _bootstrap(paired["model_points"] - paired[f"{baseline}_points"], rng)
    captain["regret"] = round(float((picks["best_points"] - picks["model_points"]).mean()), 3)
    captain["by_season"] = {
        str(season): {s: round(float(g[f"{s}_points"].mean()), 3) for s in ("model", "elite", "premium", "form")}
        for season, g in picks.groupby("season")
    }
    accepted_captain = all(v["low"] > 0 for v in captain["versus"].values())

    log("Lineup comparison on top-100 squads")
    lineups = lineup_scores(preds, squads, players)
    weekly = lineups.groupby(["season", "gameweek"])[["model_points", "manager_points", "form_points"]].mean()
    lineup = {
        "squad_weeks": int(len(lineups)),
        "points_per_week": {k.replace("_points", ""): round(float(v), 3) for k, v in weekly.mean().items()},
        "versus": {
            "manager": _bootstrap(weekly["model_points"] - weekly["manager_points"], rng),
            "form": _bootstrap(weekly["model_points"] - weekly["form_points"], rng),
        },
    }
    accepted_lineup = all(v["low"] > 0 for v in lineup["versus"].values())

    return {
        "version": VERSION,
        "test_seasons": [f"{s}/{(s + 1) % 100:02d}" for s in test_seasons],
        "retrain_every": retrain_every,
        "accuracy": accuracy,
        "captain": captain,
        "lineup": lineup,
        "accepted": {"captain": accepted_captain, "lineup": accepted_lineup},
        "recent_picks": picks.tail(38).replace({np.nan: None}).to_dict("records"),
    }
