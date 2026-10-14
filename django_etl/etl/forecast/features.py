"""Deadline-safe features for the next-gameweek points forecast.

Every feature for a (season, gameweek, player) row is built only from weeks
strictly before that gameweek. Player state is computed after each week the
player's club had a fixture, and each target row takes the latest state from
an *earlier* week (``merge_asof`` with exact matches disallowed). Rows carry
the stable player ``code``, so form runs across season boundaries, and last
season's rates act as the prior while this season's sample is small.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STAT_COLUMNS = [
    "minutes", "starts", "total_points", "expected_goals", "expected_assists", "bonus", "bps", "saves",
    "expected_goals_conceded",
]

FEATURES = [
    "position", "start_price", "gameweek", "dc_era", "n_fix", "home_frac",
    "team_xgf", "team_xga", "opp_xgf", "opp_xga",
    "mins_l1", "mins_m3", "mins_m6", "start_r6", "pts_m3", "pts_m6",
    "xg90_6", "xa90_6", "bonus90_6", "bps90_6", "saves90_6",
    "xg90_s", "xa90_s", "pts90_s", "min_share_s", "fix_s",
    "prev_xg90", "prev_xa90", "pts90_prev", "min_share_prev",
    "appearances", "weeks_since",
]

TEAM_WINDOW = 8  # gameweeks of club form (≈ 7–8 matches)


def _time(season, gameweek):
    return season * 100 + gameweek


def team_weeks(players: pd.DataFrame, fixtures: pd.DataFrame) -> pd.DataFrame:
    """One row per club per gameweek: fixtures, home games, and rolling xG for/against."""
    long = pd.concat([
        pd.DataFrame({"season": fixtures.season, "gameweek": fixtures.gameweek, "team_code": fixtures.team_h_code,
                      "opp_code": fixtures.team_a_code, "home": 1}),
        pd.DataFrame({"season": fixtures.season, "gameweek": fixtures.gameweek, "team_code": fixtures.team_a_code,
                      "opp_code": fixtures.team_h_code, "home": 0}),
    ], ignore_index=True)
    long["gameweek"] = long["gameweek"].astype(int)
    weeks = long.groupby(["season", "gameweek", "team_code"]).agg(n_fix=("home", "size"), home_n=("home", "sum")).reset_index()

    played = players.dropna(subset=["minutes"])
    xg = played.groupby(["season", "gameweek", "team_code"])["expected_goals"].sum().rename("xg_for").reset_index()
    weeks = weeks.merge(xg, on=["season", "gameweek", "team_code"], how="left")
    weeks["played"] = weeks["xg_for"].notna()
    # xG against: each opponent's xG that week, per match it played.
    opp = long.merge(weeks[["season", "gameweek", "team_code", "xg_for", "n_fix"]].rename(
        columns={"team_code": "opp_code", "xg_for": "opp_xg", "n_fix": "opp_n"}), on=["season", "gameweek", "opp_code"])
    opp["opp_xg_per"] = opp["opp_xg"] / opp["opp_n"]
    against = opp.groupby(["season", "gameweek", "team_code"])["opp_xg_per"].sum(min_count=1).rename("xg_against").reset_index()
    weeks = weeks.merge(against, on=["season", "gameweek", "team_code"], how="left")

    weeks = weeks.sort_values(["team_code", "season", "gameweek"])
    contrib = weeks["played"].astype(float)
    weeks["_fix"] = weeks["n_fix"] * contrib
    weeks["_xgf"] = weeks["xg_for"].fillna(0) * contrib
    weeks["_xga"] = weeks["xg_against"].fillna(0) * contrib
    grouped = weeks.groupby("team_code")
    for name, column in (("roll_xgf", "_xgf"), ("roll_xga", "_xga")):
        total = grouped[column].transform(lambda s: s.rolling(TEAM_WINDOW, min_periods=1).sum().shift(1))
        fixtures_seen = grouped["_fix"].transform(lambda s: s.rolling(TEAM_WINDOW, min_periods=1).sum().shift(1))
        weeks[name] = total / fixtures_seen.replace(0, np.nan)
    # Unplayed future weeks carry the latest known strength forward.
    weeks[["roll_xgf", "roll_xga"]] = grouped[["roll_xgf", "roll_xga"]].ffill()
    weeks = weeks.drop(columns=["_fix", "_xgf", "_xga"])

    opp_strength = long.merge(
        weeks[["season", "gameweek", "team_code", "roll_xgf", "roll_xga"]].rename(
            columns={"team_code": "opp_code", "roll_xgf": "o_xgf", "roll_xga": "o_xga"}),
        on=["season", "gameweek", "opp_code"], how="left",
    ).groupby(["season", "gameweek", "team_code"])[["o_xgf", "o_xga"]].mean().reset_index()
    weeks = weeks.merge(opp_strength, on=["season", "gameweek", "team_code"], how="left")
    return weeks


def _player_state(panel: pd.DataFrame) -> pd.DataFrame:
    """State after each week a player's club played (including that week)."""
    q = panel[(panel["n_fix"] > 0) & panel["minutes"].notna()].copy()
    q = q.sort_values(["code", "season", "gameweek"])
    per = q[["minutes", "starts", "total_points"]].div(q["n_fix"], axis=0)
    g = q.groupby("code")
    state = q[["code", "season", "gameweek"]].copy()
    state["mins_l1"] = per["minutes"]

    def roll(series, window):
        return series.groupby(q["code"]).transform(lambda s: s.rolling(window, min_periods=1).mean())

    def roll_sum(series, window):
        return series.groupby(q["code"]).transform(lambda s: s.rolling(window, min_periods=1).sum())

    state["mins_m3"] = roll(per["minutes"], 3)
    state["mins_m6"] = roll(per["minutes"], 6)
    state["start_r6"] = roll(per["starts"], 6)
    state["pts_m3"] = roll(per["total_points"], 3)
    state["pts_m6"] = roll(per["total_points"], 6)
    minutes6 = roll_sum(q["minutes"], 6).clip(lower=90)
    for name, column in (("xg90_6", "expected_goals"), ("xa90_6", "expected_assists"), ("bonus90_6", "bonus"),
                         ("bps90_6", "bps"), ("saves90_6", "saves")):
        state[name] = roll_sum(q[column], 6) / minutes6 * 90

    season_group = q.groupby(["code", "season"])
    cum = {c: season_group[c].cumsum() for c in ("minutes", "expected_goals", "expected_assists", "total_points", "n_fix")}
    minutes_s = cum["minutes"].clip(lower=90)
    state["xg90_s"] = cum["expected_goals"] / minutes_s * 90
    state["xa90_s"] = cum["expected_assists"] / minutes_s * 90
    state["pts90_s"] = cum["total_points"] / minutes_s * 90
    state["min_share_s"] = cum["minutes"] / (90 * cum["n_fix"])
    state["fix_s"] = cum["n_fix"]
    state["appearances"] = g["minutes"].transform(lambda s: (s > 0).cumsum())
    state["state_t"] = _time(state["season"], state["gameweek"])
    state["state_season"] = state["season"]
    state["state_gw"] = state["gameweek"]
    return state.drop(columns=["season", "gameweek"])


def _previous_season(panel: pd.DataFrame) -> pd.DataFrame:
    played = panel[(panel["n_fix"] > 0) & panel["minutes"].notna()]
    agg = played.groupby(["code", "season"]).agg(
        minutes=("minutes", "sum"), xg=("expected_goals", "sum"), xa=("expected_assists", "sum"),
        pts=("total_points", "sum"), fix=("n_fix", "sum"),
    ).reset_index()
    minutes = agg["minutes"].clip(lower=90)
    return pd.DataFrame({
        "code": agg["code"],
        "season": agg["season"] + 1,
        "prev_xg90": agg["xg"] / minutes * 90,
        "prev_xa90": agg["xa"] / minutes * 90,
        "pts90_prev": agg["pts"] / minutes * 90,
        "min_share_prev": agg["minutes"] / (90 * 38),
    })


def build_features(players: pd.DataFrame, fixtures: pd.DataFrame) -> pd.DataFrame:
    """Feature rows for every player-week whose club has a fixture.

    ``players`` may include future rows (stats NaN) for the weeks to forecast.
    Returns the features plus ``total_points`` (NaN for future rows).
    """
    weeks = team_weeks(players, fixtures)
    panel = players.merge(
        weeks[["season", "gameweek", "team_code", "n_fix", "home_n", "roll_xgf", "roll_xga", "o_xgf", "o_xga"]],
        on=["season", "gameweek", "team_code"], how="left",
    )
    panel["n_fix"] = panel["n_fix"].fillna(0).astype(int)
    state = _player_state(panel)

    targets = panel[panel["n_fix"] > 0].copy()
    targets["t"] = _time(targets["season"], targets["gameweek"])
    targets = pd.merge_asof(
        targets.sort_values("t"), state.sort_values("state_t"),
        left_on="t", right_on="state_t", by="code", allow_exact_matches=False, direction="backward",
    )
    targets = targets.merge(_previous_season(panel), on=["code", "season"], how="left")

    # Season-to-date values only count within the same season.
    other_season = targets["state_season"] != targets["season"]
    for column in ("xg90_s", "xa90_s", "pts90_s", "min_share_s", "fix_s"):
        targets.loc[other_season, column] = np.nan
    targets.loc[other_season, "fix_s"] = 0
    targets["weeks_since"] = (targets["season"] * 38 + targets["gameweek"]) - (
        targets["state_season"] * 38 + targets["state_gw"])
    targets["home_frac"] = targets["home_n"] / targets["n_fix"]
    targets["dc_era"] = (targets["season"] >= 2025).astype(int)
    targets = targets.rename(columns={"roll_xgf": "team_xgf", "roll_xga": "team_xga", "o_xgf": "opp_xgf", "o_xga": "opp_xga"})
    keep = ["season", "gameweek", "code", "element", "web_name", "team_code", "minutes", "total_points", *FEATURES]
    out = targets[list(dict.fromkeys(keep))].sort_values(["season", "gameweek", "code"]).reset_index(drop=True)
    return out


def future_rows(players: pd.DataFrame, season: int, gameweeks: list[int]) -> pd.DataFrame:
    """Rows to forecast: every player in the season's latest week, for each target gameweek."""
    current = players[players["season"] == season]
    if current.empty:
        return current
    latest = current.sort_values("gameweek").groupby("code").tail(1)
    rows = []
    for gameweek in gameweeks:
        frame = latest[["season", "code", "element", "web_name", "team_code", "position", "start_price"]].copy()
        frame["gameweek"] = gameweek
        rows.append(frame)
    future = pd.concat(rows, ignore_index=True)
    for column in players.columns:
        if column not in future:
            future[column] = np.nan
    return future[players.columns]
