"""Stats Explorer payload: raw season counts the browser turns into views.

The server sends each player's raw counts per competition (Premier League,
Champions League) plus FPL context. The browser does per-90, PL + UCL
combining and position percentiles, so switching a control never round-trips.

``CATALOGUE`` is the single definition of the curated stats: plain label,
group, how it is computed from raw keys, and its provenance. Raw keys are the
classic API's snake_case names, the SDP API's camelCase xG family, or FPL
fields prefixed ``fpl_``.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.cache import cache
from django.db.models import Max

from ..models import Athlete, AthleteStat, PlayerSeasonStat, TeamSeasonStat
from . import chart_lab
from .pl_stats_client import COMPETITIONS
from .sample_size import SMALL_SAMPLE, qualifying_minutes

CACHE_TTL = 600
POSITION_LABELS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
# A club counts as a Champions League club when at least this many of its
# players have UCL minutes. A real participant fields 11+ per match; one or two
# players with UCL minutes usually played them for a previous club or on loan.
UCL_CLUB_MIN_PLAYERS = 8
PL = COMPETITIONS["premier-league"]["opta"]

# Stat sheets omit zero values, so an absent key usually means 0. For the xG
# family that is only true when the player had none of the underlying actions:
# an absent xGOT for a player with shots on target is a feed gap, not a zero.
# Gaps are sent as null so the page shows "–" instead of a plausible 0.00.
GAP_EVIDENCE = {
    "expectedGoals": ("total_scoring_att",),
    "expectedGoalsOnTarget": ("ontarget_scoring_att",),
    "expectedAssists": ("total_att_assist",),
    "expectedGoalsOnTargetConceded": ("saves", "goals_conceded"),
}
UCL = COMPETITIONS["champions-league"]["opta"]


def _count(key, label, group, raw, help_text, *, pl_only=False, source="Opta", lower_is_better=False, per90=True):
    return {
        "key": key, "label": label, "group": group, "kind": "count", "raw": raw,
        "help": help_text, "plOnly": pl_only, "source": source, "lowerIsBetter": lower_is_better,
        "per90": per90,
    }


def _rate(key, label, group, num, den, help_text, *, source="Opta"):
    return {
        "key": key, "label": label, "group": group, "kind": "rate", "num": num, "den": den,
        "help": help_text, "plOnly": False, "source": source, "lowerIsBetter": False,
    }


def _diff(key, label, group, plus, minus, help_text, *, pl_only=False, source="Opta"):
    return {
        "key": key, "label": label, "group": group, "kind": "diff", "plus": plus, "minus": minus,
        "help": help_text, "plOnly": pl_only, "source": source, "lowerIsBetter": False,
    }


def _fpl(key, label, group, raw, help_text, *, fmt="number", lower_is_better=False, shade=True):
    return {
        "key": key, "label": label, "group": group, "kind": "fpl", "raw": raw, "format": fmt,
        "help": help_text, "plOnly": True, "source": "FPL", "lowerIsBetter": lower_is_better,
        "shade": shade,
    }


# Order within a group is display order.
CATALOGUE: list[dict] = [
    # Shooting
    _count("goals", "Goals", "Shooting", ["goals"], "Goals scored."),
    _count("xg", "xG", "Shooting", ["expectedGoals"], "Expected goals: the quality of chances taken.", pl_only=True),
    _count("xgot", "xGOT", "Shooting", ["expectedGoalsOnTarget"], "Expected goals on target: shot quality after placement. Above xG means well-placed shots.", pl_only=True),
    _count("shots", "Shots", "Shooting", ["total_scoring_att"], "All shot attempts."),
    _count("shots_on_target", "Shots on target", "Shooting", ["ontarget_scoring_att"], "Shots on target, including goals."),
    _count("shots_in_box", "Shots in box", "Shooting", ["attempts_ibox"], "Shot attempts from inside the penalty area."),
    _count("big_chances", "Big chances", "Shooting", ["big_chance_scored", "big_chance_missed"], "Big chances had: scored plus missed."),
    _count("touches_in_box", "Touches in box", "Shooting", ["touches_in_opp_box"], "Touches in the opposition penalty area."),
    _count("headed_shots", "Headed shots", "Shooting", ["att_hd_total"], "Headed shot attempts."),
    _diff("finishing", "Goals − xG", "Shooting", ["goals"], ["expectedGoals"], "Positive means scoring above chance quality (may not last).", pl_only=True),
    _diff("placement", "xGOT − xG", "Shooting", ["expectedGoalsOnTarget"], ["expectedGoals"], "Positive means shots are placed better than their chances suggest.", pl_only=True),
    _rate("shot_accuracy", "Shot accuracy", "Shooting", ["ontarget_scoring_att"], ["total_scoring_att"], "Share of shots on target."),
    _rate("conversion", "Conversion", "Shooting", ["goals"], ["total_scoring_att"], "Share of shots scored."),
    # Creating
    _count("assists", "Assists", "Creating", ["goal_assist"], "Assists (Opta definition, not FPL's)."),
    _count("xa", "xA", "Creating", ["expectedAssists"], "Expected assists: the quality of chances created.", pl_only=True),
    _count("chances_created", "Chances created", "Creating", ["total_att_assist"], "Passes that led to a shot (key passes)."),
    _count("big_chances_created", "Big chances created", "Creating", ["big_chance_created"], "Passes that set up a big chance."),
    _count("crosses", "Crosses", "Creating", ["total_cross"], "Crosses attempted."),
    _count("through_balls", "Through balls", "Creating", ["total_through_ball"], "Through balls attempted."),
    _count("final_third_passes", "Final-third passes", "Creating", ["successful_final_third_passes"], "Completed passes into or within the final third."),
    _count("box_entries", "Box entries", "Creating", ["successful_pen_area_entries"], "Successful entries into the penalty area."),
    _count("progressive_carries", "Progressive carries", "Creating", ["progressive_carries"], "Carries that move the ball substantially upfield."),
    _count("dribbles", "Dribbles completed", "Creating", ["won_contest"], "Take-ons won."),
    _diff("assists_vs_xa", "Assists − xA", "Creating", ["goal_assist"], ["expectedAssists"], "Positive means teammates finished above chance quality.", pl_only=True),
    _rate("cross_accuracy", "Cross accuracy", "Creating", ["accurate_cross"], ["total_cross"], "Share of crosses completed."),
    _rate("dribble_success", "Dribble success", "Creating", ["won_contest"], ["total_contest"], "Share of take-ons won."),
    # Defending (FPL defensive contribution: CBIT for defenders, CBIRT for others)
    _count("cbit", "CBIT", "Defending", ["total_clearance", "outfielder_block", "interception", "total_tackle"], "Clearances, blocks, interceptions and tackles: FPL's defensive-contribution actions for defenders."),
    _count("cbirt", "CBIRT", "Defending", ["total_clearance", "outfielder_block", "interception", "total_tackle", "ball_recovery"], "CBIT plus recoveries: FPL's defensive-contribution actions for midfielders and forwards."),
    _count("tackles", "Tackles", "Defending", ["total_tackle"], "Tackles attempted."),
    _count("interceptions", "Interceptions", "Defending", ["interception"], "Interceptions."),
    _count("clearances", "Clearances", "Defending", ["total_clearance"], "Clearances."),
    _count("blocks", "Blocks", "Defending", ["outfielder_block"], "Shots blocked by an outfield player."),
    _count("recoveries", "Recoveries", "Defending", ["ball_recovery"], "Loose balls won back."),
    _count("aerials_won", "Aerials won", "Defending", ["aerial_won"], "Aerial duels won."),
    _rate("duel_success", "Duel success", "Defending", ["duel_won"], ["duel_won", "duel_lost"], "Share of duels won."),
    _count("clean_sheets", "Clean sheets", "Defending", ["clean_sheet"], "Clean sheets while playing."),
    _count("xcs", "xCS", "Defending", ["fpl_xcs"], "Estimated clean sheets from expected goals conceded (60+ minute appearances). An AeroFPL estimate, not an official stat.", pl_only=True, source="Estimate"),
    _count("goals_conceded", "Goals conceded", "Defending", ["goals_conceded"], "Goals conceded while on the pitch.", lower_is_better=True),
    # Goalkeeping
    _count("saves", "Saves", "Goalkeeping", ["saves"], "Saves made."),
    _rate("save_pct", "Save %", "Goalkeeping", ["saves"], ["saves", "goals_conceded"], "Saves as a share of shots on target faced."),
    _count("xgot_faced", "xGOT faced", "Goalkeeping", ["expectedGoalsOnTargetConceded"], "Expected goals on target faced.", pl_only=True),
    _diff("goals_prevented", "Goals prevented", "Goalkeeping", ["expectedGoalsOnTargetConceded"], ["goals_conceded"], "xGOT faced minus goals conceded. Positive means saving more than expected.", pl_only=True),
    _count("high_claims", "High claims", "Goalkeeping", ["total_high_claim"], "Crosses claimed."),
    _count("sweeper_actions", "Sweeper actions", "Goalkeeping", ["total_keeper_sweeper"], "Actions off the line as a sweeper."),
    # Involvement & discipline
    _count("touches", "Touches", "Involvement", ["touches"], "All touches of the ball."),
    _count("passes", "Passes", "Involvement", ["total_pass"], "Passes attempted."),
    _rate("pass_accuracy", "Pass accuracy", "Involvement", ["accurate_pass"], ["total_pass"], "Share of passes completed."),
    _count("dispossessed", "Dispossessed", "Involvement", ["dispossessed"], "Times losing the ball to a tackle.", lower_is_better=True),
    _count("yellow_cards", "Yellow cards", "Involvement", ["yellow_card"], "Yellow cards.", lower_is_better=True),
    _count("errors_to_shot", "Errors → shot", "Involvement", ["error_lead_to_shot", "error_lead_to_goal"], "Errors leading to an opposition shot or goal.", lower_is_better=True),
    # Market & rotation (FPL)
    _fpl("price", "Price", "Market", "fpl_price", "Current FPL price.", fmt="price", shade=False),
    _fpl("ownership", "Owned by", "Market", "fpl_ownership", "Share of FPL managers who own the player. Low ownership means a differential.", fmt="percent", shade=False),
    _fpl("points", "FPL points", "Market", "fpl_points", "Total FPL points this season."),
    _fpl("points_per_m", "Points per £m", "Market", "fpl_points_per_m", "FPL points per £1m of price."),
    _count("starts", "Starts", "Market", ["game_started"], "Starts (as opposed to sub appearances). Always a season count, never per 90.", per90=False),
    _fpl("minutes_share", "Minutes share", "Market", "fpl_minutes_share", "Share of the club's league minutes the player has played.", fmt="percent"),
]

LENSES = {
    "attacking": {"label": "Attacking threat", "columns": ["xg", "xgot", "shots", "shots_on_target", "big_chances", "touches_in_box", "goals", "finishing", "placement"]},
    "creativity": {"label": "Creativity", "columns": ["xa", "chances_created", "big_chances_created", "assists", "assists_vs_xa", "box_entries", "final_third_passes", "progressive_carries", "dribbles"]},
    "defence": {"label": "Defence & keepers", "columns": ["cbit", "cbirt", "tackles", "interceptions", "clearances", "recoveries", "xcs", "clean_sheets", "goals_conceded"], "keeperColumns": ["saves", "save_pct", "xgot_faced", "goals_prevented", "high_claims", "clean_sheets", "xcs", "goals_conceded"]},
    "market": {"label": "Market & rotation", "columns": ["ownership", "points", "points_per_m", "starts", "minutes_share", "xg", "xa"]},
}

TEAM_CATALOGUE = [
    {"key": "gamesPlayed", "label": "Played", "group": "Results", "help": "League matches played.", "perMatch": False},
    {"key": "goals", "label": "Goals", "group": "Attack", "help": "Goals scored.", "perMatch": True},
    {"key": "expectedGoals", "label": "xG", "group": "Attack", "help": "Expected goals for.", "perMatch": True},
    {"key": "expectedGoalsOnTarget", "label": "xGOT", "group": "Attack", "help": "Expected goals on target for.", "perMatch": True},
    {"key": "totalShots", "label": "Shots", "group": "Attack", "help": "Shots taken.", "perMatch": True},
    {"key": "shotsOnTargetIncGoals", "label": "On target", "group": "Attack", "help": "Shots on target.", "perMatch": True},
    {"key": "touchesInOppBox", "label": "Touches in box", "group": "Attack", "help": "Touches in the opposition box.", "perMatch": True},
    {"key": "possessionPercentage", "label": "Possession", "group": "Attack", "help": "Average possession.", "perMatch": False, "format": "percent"},
    {"key": "goalsConceded", "label": "Conceded", "group": "Defence", "help": "Goals conceded.", "perMatch": True, "lowerIsBetter": True},
    {"key": "expectedGoalsOnTargetConceded", "label": "xGOT against", "group": "Defence", "help": "Expected goals on target conceded.", "perMatch": True, "lowerIsBetter": True},
    {"key": "totalShotsConceded", "label": "Shots against", "group": "Defence", "help": "Shots conceded.", "perMatch": True, "lowerIsBetter": True},
    {"key": "shotsOnConcededInsideBox", "label": "Box shots against", "group": "Defence", "help": "Shots on target conceded from inside the box.", "perMatch": True, "lowerIsBetter": True},
    {"key": "cleanSheets", "label": "Clean sheets", "group": "Defence", "help": "Clean sheets.", "perMatch": False},
    {"key": "recoveries", "label": "Recoveries", "group": "Defence", "help": "Loose balls won back.", "perMatch": True},
]


def _raw_keys() -> set[str]:
    keys: set[str] = set()
    for stat in CATALOGUE:
        for field in ("raw", "num", "den", "plus", "minus"):
            value = stat.get(field)
            if isinstance(value, list):
                keys.update(value)
    return {k for k in keys if not k.startswith("fpl_")}


def build_payload(season: int) -> dict:
    latest = AthleteStat.objects.aggregate(gw=Max("game_week"))["gw"] or 0
    cache_key = f"stats_explorer:{season}:gw{latest}:v4"
    cached = cache.get(cache_key)
    if cached:
        return cached

    wanted = _raw_keys()
    rows = PlayerSeasonStat.objects.filter(season=season, athlete__isnull=False).values(
        "athlete_id", "source", "competition_id", "stats"
    )
    per_player: dict[int, dict[str, dict[str, float]]] = defaultdict(lambda: {"pl": {}, "ucl": {}})
    for row in rows:
        scope = "pl" if row["competition_id"] == PL else "ucl" if row["competition_id"] == UCL else None
        if scope is None:
            continue
        bucket = per_player[row["athlete_id"]][scope]
        for key, value in (row["stats"] or {}).items():
            if key in wanted or key == "mins_played":
                bucket[key] = float(value or 0)

    athletes = {
        a.id: a for a in Athlete.objects.filter(id__in=per_player, removed=False).select_related("team")
    }
    xcs = chart_lab.expected_clean_sheets(athletes)
    team_minutes = _team_league_minutes()
    ucl_players_by_team: dict[int, int] = defaultdict(int)
    for pid, scopes in per_player.items():
        if pid in athletes and scopes["ucl"].get("mins_played"):
            ucl_players_by_team[athletes[pid].team_id] += 1
    ucl_team_ids = {team for team, n in ucl_players_by_team.items() if n >= UCL_CLUB_MIN_PLAYERS}

    players = []
    for pid, scopes in per_player.items():
        athlete = athletes.get(pid)
        if athlete is None or not scopes["pl"].get("mins_played"):
            continue
        _mark_feed_gaps(scopes["pl"])
        price = (athlete.now_cost or 0) / 10
        points = athlete.total_points or 0
        fpl_minutes = athlete.minutes or 0
        scopes["pl"]["fpl_points"] = float(points)
        scopes["pl"]["fpl_xcs"] = round(xcs.get(pid, 0.0), 3)
        players.append({
            "id": pid,
            "name": athlete.web_name,
            "team": athlete.team.short_name if athlete.team else None,
            "teamId": athlete.team_id,
            "position": POSITION_LABELS.get(athlete.element_type, "—"),
            "status": athlete.status,
            "news": athlete.news or "",
            "fpl": {
                "fpl_price": price,
                "fpl_ownership": float(athlete.selected_by_percent or 0),
                "fpl_points": points,
                "fpl_points_per_m": round(points / price, 2) if price else None,
                "fpl_minutes_share": round(fpl_minutes / team_minutes[athlete.team_id], 3)
                if team_minutes.get(athlete.team_id) else None,
            },
            "pl": scopes["pl"],
            "ucl": scopes["ucl"] or None,
        })

    teams = []
    for row in TeamSeasonStat.objects.filter(season=season, competition_id=PL, team__isnull=False).select_related("team"):
        teams.append({
            "id": row.team_id,
            "name": row.team.name,
            "short": row.team.short_name,
            "inUcl": row.team_id in ucl_team_ids,
            "stats": {item["key"]: row.stats.get(item["key"]) for item in TEAM_CATALOGUE},
        })

    payload = {
        "season": season,
        "seasonLabel": f"{season}/{(season + 1) % 100:02d}",
        "latestGameweek": latest,
        # The ranking bar (see services/sample_size.py): grows with the season.
        "minMinutes": qualifying_minutes(latest),
        "smallSample": SMALL_SAMPLE,
        "catalogue": CATALOGUE,
        "lenses": LENSES,
        "teamCatalogue": TEAM_CATALOGUE,
        "uclTeamIds": sorted(t for t in ucl_team_ids if t is not None),
        "uclClubRule": f"{UCL_CLUB_MIN_PLAYERS}+ squad players with Champions League minutes this season",
        "players": sorted(players, key=lambda p: p["name"]),
        "teams": sorted(teams, key=lambda t: t["name"]),
    }
    cache.set(cache_key, payload, CACHE_TTL)
    return payload


def _mark_feed_gaps(counts: dict) -> None:
    """Make absent xG-family keys explicit: 0.0 when truly zero, None when a gap."""
    for key, evidence in GAP_EVIDENCE.items():
        if key in counts:
            continue
        had_actions = any((counts.get(e) or 0) > 0 for e in evidence)
        counts[key] = None if had_actions else 0.0


def _team_league_minutes() -> dict[int, int]:
    """Minutes each club has played in the league so far (matches × 90)."""
    played: dict[int, set[int]] = defaultdict(set)
    for team_id, game_week, minutes in AthleteStat.objects.filter(minutes__gt=0).values_list(
        "athlete__team_id", "game_week", "minutes"
    ):
        played[team_id].add(game_week)
    return {team_id: len(gws) * 90 for team_id, gws in played.items()}
