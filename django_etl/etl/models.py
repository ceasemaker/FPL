"""Database models for the Django ETL pipeline."""

from __future__ import annotations

from decimal import Decimal

from django.db import models


class TimestampedModel(models.Model):
    """Abstract base class with automatic created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Team(TimestampedModel):
    id = models.IntegerField(primary_key=True)
    code = models.IntegerField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=10, null=True, blank=True)
    strength = models.IntegerField(null=True, blank=True)
    played = models.IntegerField(default=0)
    win = models.IntegerField(default=0)
    draw = models.IntegerField(default=0)
    loss = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    position = models.IntegerField(null=True, blank=True)
    form = models.CharField(max_length=50, null=True, blank=True)
    unavailable = models.BooleanField(default=False)
    strength_overall_home = models.IntegerField(null=True, blank=True)
    strength_overall_away = models.IntegerField(null=True, blank=True)
    strength_attack_home = models.IntegerField(null=True, blank=True)
    strength_attack_away = models.IntegerField(null=True, blank=True)
    strength_defence_home = models.IntegerField(null=True, blank=True)
    strength_defence_away = models.IntegerField(null=True, blank=True)
    team_division = models.IntegerField(null=True, blank=True)
    pulse_id = models.IntegerField(null=True, blank=True)

    class Meta(TimestampedModel.Meta):
        db_table = "teams"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name


class Athlete(TimestampedModel):
    id = models.IntegerField(primary_key=True)
    can_transact = models.BooleanField(null=True, blank=True)
    can_select = models.BooleanField(null=True, blank=True)
    chance_of_playing_next_round = models.IntegerField(null=True, blank=True)
    chance_of_playing_this_round = models.IntegerField(null=True, blank=True)
    code = models.IntegerField(unique=True)
    cost_change_event = models.IntegerField(default=0)
    cost_change_event_fall = models.IntegerField(default=0)
    cost_change_start = models.IntegerField(default=0)
    cost_change_start_fall = models.IntegerField(default=0)
    dreamteam_count = models.IntegerField(default=0)
    element_type = models.IntegerField(null=True, blank=True)
    ep_next = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    ep_this = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    event_points = models.IntegerField(default=0)
    first_name = models.CharField(max_length=255)
    form = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    in_dreamteam = models.BooleanField(default=False)
    news = models.TextField(null=True, blank=True)
    news_added = models.DateTimeField(null=True, blank=True)
    now_cost = models.IntegerField(default=0)
    photo = models.CharField(max_length=255, null=True, blank=True)
    points_per_game = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    removed = models.BooleanField(default=False)
    second_name = models.CharField(max_length=255)
    selected_by_percent = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    special = models.BooleanField(default=False)
    squad_number = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    team = models.ForeignKey(
        Team,
        related_name="athletes",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="team",
    )
    team_code = models.IntegerField(null=True, blank=True)
    total_points = models.IntegerField(default=0)
    transfers_in = models.IntegerField(default=0)
    transfers_in_event = models.IntegerField(default=0)
    transfers_out = models.IntegerField(default=0)
    transfers_out_event = models.IntegerField(default=0)
    value_form = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    value_season = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    web_name = models.CharField(max_length=255)
    region = models.IntegerField(null=True, blank=True)
    team_join_date = models.DateField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    has_temporary_code = models.BooleanField(default=False)
    opta_code = models.CharField(max_length=50, null=True, blank=True)
    minutes = models.IntegerField(default=0)
    goals_scored = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)
    clean_sheets = models.IntegerField(default=0)
    goals_conceded = models.IntegerField(default=0)
    own_goals = models.IntegerField(default=0)
    penalties_saved = models.IntegerField(default=0)
    penalties_missed = models.IntegerField(default=0)
    yellow_cards = models.IntegerField(default=0)
    red_cards = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)
    bonus = models.IntegerField(default=0)
    bps = models.IntegerField(default=0)
    influence = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    creativity = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    threat = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ict_index = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    starts = models.IntegerField(default=0)
    expected_goals = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    expected_assists = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    expected_goal_involvements = models.DecimalField(
        max_digits=13,
        decimal_places=3,
        null=True,
        blank=True,
    )
    expected_goals_conceded = models.DecimalField(
        max_digits=13, decimal_places=3, null=True, blank=True
    )
    mng_win = models.IntegerField(default=0)
    mng_draw = models.IntegerField(default=0)
    mng_loss = models.IntegerField(default=0)
    mng_underdog_win = models.IntegerField(default=0)
    mng_underdog_draw = models.IntegerField(default=0)
    mng_clean_sheets = models.IntegerField(default=0)
    mng_goals_scored = models.IntegerField(default=0)
    influence_rank = models.IntegerField(null=True, blank=True)
    influence_rank_type = models.IntegerField(null=True, blank=True)
    creativity_rank = models.IntegerField(null=True, blank=True)
    creativity_rank_type = models.IntegerField(null=True, blank=True)
    threat_rank = models.IntegerField(null=True, blank=True)
    threat_rank_type = models.IntegerField(null=True, blank=True)
    ict_index_rank = models.IntegerField(null=True, blank=True)
    ict_index_rank_type = models.IntegerField(null=True, blank=True)
    corners_and_indirect_freekicks_order = models.IntegerField(null=True, blank=True)
    corners_and_indirect_freekicks_text = models.TextField(null=True, blank=True)
    direct_freekicks_order = models.IntegerField(null=True, blank=True)
    direct_freekicks_text = models.TextField(null=True, blank=True)
    penalties_order = models.IntegerField(null=True, blank=True)
    penalties_text = models.TextField(null=True, blank=True)
    expected_goals_per_90 = models.DecimalField(
        max_digits=13, decimal_places=3, null=True, blank=True
    )
    saves_per_90 = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    expected_assists_per_90 = models.DecimalField(
        max_digits=13, decimal_places=3, null=True, blank=True
    )
    expected_goal_involvements_per_90 = models.DecimalField(
        max_digits=13, decimal_places=3, null=True, blank=True
    )
    expected_goals_conceded_per_90 = models.DecimalField(
        max_digits=13, decimal_places=3, null=True, blank=True
    )
    goals_conceded_per_90 = models.DecimalField(
        max_digits=13, decimal_places=3, null=True, blank=True
    )
    now_cost_rank = models.IntegerField(null=True, blank=True)
    now_cost_rank_type = models.IntegerField(null=True, blank=True)
    form_rank = models.IntegerField(null=True, blank=True)
    form_rank_type = models.IntegerField(null=True, blank=True)
    points_per_game_rank = models.IntegerField(null=True, blank=True)
    points_per_game_rank_type = models.IntegerField(null=True, blank=True)
    selected_rank = models.IntegerField(null=True, blank=True)
    selected_rank_type = models.IntegerField(null=True, blank=True)
    starts_per_90 = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    clean_sheets_per_90 = models.DecimalField(
        max_digits=13, decimal_places=3, null=True, blank=True
    )

    class Meta(TimestampedModel.Meta):
        db_table = "athletes"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["-total_points"]),  # For sorting by points (descending)
            models.Index(fields=["element_type"]),  # For filtering by position
            models.Index(fields=["team"]),  # For filtering by team (already has FK index, but explicit)
            models.Index(fields=["element_type", "-total_points"]),  # Composite for Dream Team calculation
        ]

    def __str__(self) -> str:
        team_code = self.team.short_name if self.team and self.team.short_name else "FA"
        return f"{self.web_name} ({team_code})"


class AthleteStat(TimestampedModel):
    athlete = models.ForeignKey(
        Athlete,
        related_name="stats",
        on_delete=models.CASCADE,
        db_column="athlete_id",
    )
    game_week = models.PositiveIntegerField()
    minutes = models.IntegerField(default=0)
    goals_scored = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)
    clean_sheets = models.IntegerField(default=0)
    goals_conceded = models.IntegerField(default=0)
    own_goals = models.IntegerField(default=0)
    penalties_saved = models.IntegerField(default=0)
    penalties_missed = models.IntegerField(default=0)
    yellow_cards = models.IntegerField(default=0)
    red_cards = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)
    bonus = models.IntegerField(default=0)
    bps = models.IntegerField(default=0)
    influence = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    creativity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    threat = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    ict_index = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    starts = models.IntegerField(default=0)
    expected_goals = models.DecimalField(max_digits=13, decimal_places=3, default=Decimal("0"))
    expected_assists = models.DecimalField(max_digits=13, decimal_places=3, default=Decimal("0"))
    expected_goal_involvements = models.DecimalField(max_digits=13, decimal_places=3, default=Decimal("0"))
    expected_goals_conceded = models.DecimalField(max_digits=13, decimal_places=3, default=Decimal("0"))
    mng_win = models.IntegerField(default=0)
    mng_draw = models.IntegerField(default=0)
    mng_loss = models.IntegerField(default=0)
    mng_underdog_win = models.IntegerField(default=0)
    mng_underdog_draw = models.IntegerField(default=0)
    mng_clean_sheets = models.IntegerField(default=0)
    mng_goals_scored = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    in_dreamteam = models.BooleanField(default=False)

    class Meta(TimestampedModel.Meta):
        db_table = "athlete_stats"
        constraints = [
            models.UniqueConstraint(
                fields=["athlete", "game_week"],
                name="unique_athlete_gameweek",
            )
        ]
        indexes = [
            models.Index(fields=["game_week"]),
        ]

    def __str__(self) -> str:
        return f"{self.athlete.web_name} - GW{self.game_week}"


class Fixture(TimestampedModel):
    id = models.IntegerField(primary_key=True)
    code = models.IntegerField(null=True, blank=True)
    event = models.IntegerField(null=True, blank=True)
    finished = models.BooleanField(default=False)
    finished_provisional = models.BooleanField(default=False)
    kickoff_time = models.DateTimeField(null=True, blank=True)
    minutes = models.IntegerField(default=0)
    provisional_start_time = models.BooleanField(default=False)
    started = models.BooleanField(default=False)
    team_a = models.ForeignKey(
        Team,
        related_name="away_fixtures",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="team_a",
    )
    team_h = models.ForeignKey(
        Team,
        related_name="home_fixtures",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="team_h",
    )
    team_a_score = models.IntegerField(null=True, blank=True)
    team_h_score = models.IntegerField(null=True, blank=True)
    stats = models.JSONField(default=dict)
    team_a_difficulty = models.IntegerField(null=True, blank=True)
    team_h_difficulty = models.IntegerField(null=True, blank=True)
    pulse_id = models.IntegerField(null=True, blank=True)

    class Meta(TimestampedModel.Meta):
        db_table = "fixtures"
        ordering = ["kickoff_time"]
        indexes = [
            models.Index(fields=["event"]),  # For filtering by gameweek
            models.Index(fields=["team_h", "event"]),  # For home team fixtures by gameweek
            models.Index(fields=["team_a", "event"]),  # For away team fixtures by gameweek
        ]

    def __str__(self) -> str:
        return f"GW{self.event}: {self.team_h} vs {self.team_a}"


class ElementSummary(TimestampedModel):
    athlete = models.OneToOneField(
        Athlete,
        related_name="summary",
        on_delete=models.CASCADE,
    )
    fixtures = models.JSONField(default=list)
    history = models.JSONField(default=list)
    history_past = models.JSONField(default=list)

    class Meta(TimestampedModel.Meta):
        db_table = "athlete_element_summaries"

    def __str__(self) -> str:
        return f"Summary for {self.athlete.web_name}"


class EventStatus(TimestampedModel):
    event = models.IntegerField(null=True, blank=True)
    bonus_added = models.BooleanField(default=False)
    status = models.CharField(max_length=50)
    date = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, null=True, blank=True)

    class Meta(TimestampedModel.Meta):
        db_table = "event_statuses"
        constraints = [
            models.UniqueConstraint(fields=["event", "status"], name="unique_event_status"),
        ]

    def __str__(self) -> str:
        return f"Event {self.event} - {self.status}"


class SetPieceNote(TimestampedModel):
    team = models.OneToOneField(
        Team,
        related_name="set_piece_note",
        on_delete=models.CASCADE,
    )
    last_updated = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta(TimestampedModel.Meta):
        db_table = "team_set_piece_notes"

    def __str__(self) -> str:
        return f"Set piece note for {self.team}"


class RawEndpointSnapshot(TimestampedModel):
    """Store raw payloads for debugging and auditing."""

    endpoint = models.CharField(max_length=255)
    identifier = models.CharField(max_length=255, null=True, blank=True)
    payload = models.JSONField()

    class Meta(TimestampedModel.Meta):
        db_table = "raw_endpoint_snapshots"
        indexes = [
            models.Index(fields=["endpoint"]),
        ]

    def __str__(self) -> str:
        return f"{self.endpoint} @ {self.created_at.isoformat()}"


# ============================================================================
# SofaSport Integration Models
# ============================================================================


class SofasportFixture(TimestampedModel):
    """
    Store SofaSport fixture data mapped to FPL fixtures.
    Links SofaSport events to FPL fixtures for enhanced statistics.
    
    API Response: event object with id (int), homeTeam/awayTeam (dict), 
    homeScore/awayScore (dict with 'current', 'display', 'period1', 'period2'),
    status (dict with 'type'), startTimestamp (Unix timestamp)
    """
    sofasport_event_id = models.BigIntegerField(unique=True, db_index=True, help_text="SofaSport event ID")
    fixture = models.ForeignKey(
        Fixture,
        related_name="sofasport_fixtures",
        on_delete=models.CASCADE,
        help_text="Link to FPL fixture"
    )
    home_team = models.ForeignKey(
        Team,
        related_name="sofasport_home_fixtures",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="FPL home team"
    )
    away_team = models.ForeignKey(
        Team,
        related_name="sofasport_away_fixtures",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="FPL away team"
    )
    sofasport_home_team_id = models.BigIntegerField(help_text="SofaSport home team ID")
    sofasport_away_team_id = models.BigIntegerField(help_text="SofaSport away team ID")
    start_timestamp = models.BigIntegerField(null=True, blank=True, help_text="Unix timestamp from API")
    kickoff_time = models.DateTimeField(null=True, blank=True, help_text="Converted datetime")
    match_status = models.CharField(max_length=50, null=True, blank=True, help_text="Status type (finished, inprogress, etc)")
    home_score_current = models.IntegerField(null=True, blank=True)
    away_score_current = models.IntegerField(null=True, blank=True)
    home_score_period1 = models.IntegerField(null=True, blank=True)
    away_score_period1 = models.IntegerField(null=True, blank=True)
    home_score_period2 = models.IntegerField(null=True, blank=True)
    away_score_period2 = models.IntegerField(null=True, blank=True)
    home_formation = models.CharField(max_length=20, null=True, blank=True, help_text="Team formation (e.g., '4-3-3')")
    away_formation = models.CharField(max_length=20, null=True, blank=True, help_text="Team formation (e.g., '4-3-3')")
    has_xg = models.BooleanField(default=False, help_text="Whether xG data is available")
    has_player_statistics = models.BooleanField(default=False, help_text="Whether player stats are available")
    has_heatmap = models.BooleanField(default=False, help_text="Whether heatmap data is available")
    lineups_confirmed = models.BooleanField(default=False, help_text="Whether lineups are confirmed")
    raw_data = models.JSONField(default=dict, help_text="Full SofaSport fixture data")

    class Meta(TimestampedModel.Meta):
        db_table = "sofasport_fixtures"
        ordering = ["-kickoff_time"]
        indexes = [
            models.Index(fields=["fixture"]),
            models.Index(fields=["home_team"]),
            models.Index(fields=["away_team"]),
            models.Index(fields=["match_status"]),
        ]

    def __str__(self) -> str:
        return f"SofaSport Event {self.sofasport_event_id}: {self.home_team} vs {self.away_team}"


class SofasportLineup(TimestampedModel):
    """
    Store player lineup information from SofaSport.
    Links to FPL athletes and fixtures.
    
    API Response: Player object nested in lineup with player details, 
    position, substitute (bool), shirtNumber, jerseyNumber, statistics (dict)
    Statistics are embedded directly in each player object in the lineup.
    """
    sofasport_player_id = models.BigIntegerField(db_index=True, help_text="SofaSport player ID")
    athlete = models.ForeignKey(
        Athlete,
        related_name="sofasport_lineups",
        on_delete=models.CASCADE,
        help_text="Link to FPL athlete"
    )
    fixture = models.ForeignKey(
        SofasportFixture,
        related_name="lineups",
        on_delete=models.CASCADE,
        help_text="Link to SofaSport fixture"
    )
    team = models.ForeignKey(
        Team,
        related_name="sofasport_lineups",
        on_delete=models.CASCADE,
        help_text="FPL team"
    )
    sofasport_team_id = models.BigIntegerField(help_text="SofaSport team ID from lineup")
    position = models.CharField(max_length=10, null=True, blank=True, help_text="Player position (G, D, M, F)")
    shirt_number = models.IntegerField(null=True, blank=True)
    substitute = models.BooleanField(default=False, help_text="Whether player started on the bench")
    minutes_played = models.IntegerField(null=True, blank=True, help_text="Minutes played from statistics")
    # Store the full statistics dict from the API
    statistics = models.JSONField(
        default=dict, 
        help_text="Full player statistics dict from lineup API (rating, passes, shots, etc.)"
    )
    player_name = models.CharField(max_length=200, help_text="Player name from SofaSport")
    player_slug = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta(TimestampedModel.Meta):
        db_table = "sofasport_lineups"
        ordering = ["fixture", "team", "-substitute", "shirt_number"]
        indexes = [
            models.Index(fields=["athlete"]),
            models.Index(fields=["fixture"]),
            models.Index(fields=["team"]),
            models.Index(fields=["sofasport_player_id"]),
        ]
        unique_together = [["athlete", "fixture"]]

    def __str__(self) -> str:
        return f"{self.player_name} - {self.fixture}"


class SofasportHeatmap(TimestampedModel):
    """
    Store player heatmap coordinates from SofaSport.
    Used for visualizing player movement and positioning.
    
    API Response: Array of {x, y} coordinate objects.
    Each point represents a location on the pitch where the player was active.
    Coordinates are typically on a 100x100 grid.
    """
    sofasport_player_id = models.BigIntegerField(db_index=True, help_text="SofaSport player ID")
    athlete = models.ForeignKey(
        Athlete,
        related_name="sofasport_heatmaps",
        on_delete=models.CASCADE,
        help_text="Link to FPL athlete"
    )
    fixture = models.ForeignKey(
        SofasportFixture,
        related_name="heatmaps",
        on_delete=models.CASCADE,
        help_text="Link to SofaSport fixture"
    )
    lineup = models.OneToOneField(
        SofasportLineup,
        related_name="heatmap",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Link to lineup entry"
    )
    coordinates = models.JSONField(
        default=list,
        help_text="Array of heatmap coordinates [{x: int, y: int}, ...] from API"
    )
    point_count = models.IntegerField(default=0, help_text="Number of coordinate points")

    class Meta(TimestampedModel.Meta):
        db_table = "sofasport_heatmaps"
        ordering = ["fixture", "athlete"]
        indexes = [
            models.Index(fields=["athlete"]),
            models.Index(fields=["fixture"]),
            models.Index(fields=["sofasport_player_id"]),
        ]
        unique_together = [["athlete", "fixture"]]

    def __str__(self) -> str:
        return f"Heatmap: {self.athlete.web_name} - {self.fixture} ({self.point_count} points)"


class SofasportPlayerSeasonStats(TimestampedModel):
    """
    Store aggregated season statistics for players from SofaSport.
    Updated periodically to cache season-level performance metrics.
    
    API Response: /players/statistics/result endpoint returns season totals
    and averages including rating, goals, assists, passes, duels, etc.
    """
    sofasport_player_id = models.BigIntegerField(db_index=True, help_text="SofaSport player ID")
    athlete = models.ForeignKey(
        Athlete,
        related_name="sofasport_season_stats",
        on_delete=models.CASCADE,
        help_text="Link to FPL athlete"
    )
    team = models.ForeignKey(
        Team,
        related_name="sofasport_player_season_stats",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="FPL team"
    )
    sofasport_team_id = models.BigIntegerField(help_text="SofaSport team ID")
    season_id = models.CharField(max_length=50, default="76986", help_text="Season ID (e.g., '76986' for 2025/26)")
    
    # Control fields for display and categorization
    category = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Stat category (e.g., 'attacking', 'defensive', 'passing', 'goalkeeper')"
    )
    display_stats = models.BooleanField(
        default=True,
        help_text="Whether to display these stats in the frontend"
    )
    
    # Key aggregated statistics - extracted for easy querying
    rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, help_text="Average rating")
    total_rating = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Sum of ratings")
    count_rating = models.IntegerField(null=True, blank=True, help_text="Number of rated appearances")
    minutes_played = models.IntegerField(null=True, blank=True, help_text="Total minutes played")
    appearances = models.IntegerField(null=True, blank=True, help_text="Number of appearances")
    
    # Attacking stats
    goals = models.IntegerField(null=True, blank=True)
    assists = models.IntegerField(null=True, blank=True)
    expected_assists = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="xA limited to 2 decimals")
    big_chances_created = models.IntegerField(null=True, blank=True)
    big_chances_missed = models.IntegerField(null=True, blank=True)
    total_shots = models.IntegerField(null=True, blank=True)
    shots_on_target = models.IntegerField(null=True, blank=True)
    
    # Passing stats
    accurate_passes = models.IntegerField(null=True, blank=True)
    total_passes = models.IntegerField(null=True, blank=True)
    accurate_passes_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    key_passes = models.IntegerField(null=True, blank=True)
    accurate_long_balls = models.IntegerField(null=True, blank=True)
    accurate_long_balls_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Defensive stats
    tackles = models.IntegerField(null=True, blank=True)
    interceptions = models.IntegerField(null=True, blank=True)
    clearances = models.IntegerField(null=True, blank=True)
    
    # Duel stats
    total_duels_won = models.IntegerField(null=True, blank=True)
    total_duels_won_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    aerial_duels_won = models.IntegerField(null=True, blank=True)
    ground_duels_won = models.IntegerField(null=True, blank=True)
    
    # Discipline
    yellow_cards = models.IntegerField(null=True, blank=True)
    red_cards = models.IntegerField(null=True, blank=True)
    fouls = models.IntegerField(null=True, blank=True)
    was_fouled = models.IntegerField(null=True, blank=True)
    
    # Goalkeeper stats (null for outfield players)
    saves = models.IntegerField(null=True, blank=True)
    saves_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    clean_sheets = models.IntegerField(null=True, blank=True)
    goals_conceded = models.IntegerField(null=True, blank=True)
    
    # Store full statistics JSON for all other metrics
    statistics = models.JSONField(
        default=dict,
        help_text="Complete season statistics from API (60+ fields)"
    )
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True, help_text="When stats were last fetched")
    
    class Meta(TimestampedModel.Meta):
        db_table = "sofasport_player_season_stats"
        ordering = ["-rating", "athlete"]
        indexes = [
            models.Index(fields=["athlete"]),
            models.Index(fields=["team"]),
            models.Index(fields=["season_id"]),
            models.Index(fields=["sofasport_player_id"]),
            models.Index(fields=["-rating"]),
            models.Index(fields=["-goals"]),
            models.Index(fields=["-assists"]),
        ]
        unique_together = [["athlete", "season_id"]]

    def __str__(self) -> str:
        return f"{self.athlete.web_name} - Season {self.season_id} (Rating: {self.rating})"


class SofasportPlayerAttributes(TimestampedModel):
    """
    Player attribute ratings for radar chart visualization.
    
    Stores multi-dimensional player ratings used for creating radar charts showing
    player strengths across attacking, technical, tactical, defending, and creativity.
    """
    # Primary identifiers
    sofasport_player_id = models.BigIntegerField(
        help_text="SofaSport player ID from API"
    )
    athlete = models.ForeignKey(
        Athlete,
        related_name="sofasport_attributes",
        on_delete=models.CASCADE,
        help_text="Link to FPL athlete"
    )
    
    # Attribute ratings (0-100 scale)
    attacking = models.IntegerField(
        null=True, blank=True,
        help_text="Attacking ability rating (0-100)"
    )
    technical = models.IntegerField(
        null=True, blank=True,
        help_text="Technical skill rating (0-100)"
    )
    tactical = models.IntegerField(
        null=True, blank=True,
        help_text="Tactical awareness rating (0-100)"
    )
    defending = models.IntegerField(
        null=True, blank=True,
        help_text="Defensive ability rating (0-100)"
    )
    creativity = models.IntegerField(
        null=True, blank=True,
        help_text="Creativity/playmaking rating (0-100)"
    )
    
    # Metadata
    position = models.CharField(
        max_length=10,
        null=True, blank=True,
        help_text="Position for these attributes (F, M, D, G)"
    )
    year_shift = models.IntegerField(
        default=0,
        help_text="0 = current season, negative = previous seasons"
    )
    is_average = models.BooleanField(
        default=False,
        help_text="True if from averageAttributeOverviews (career average)"
    )
    
    # Store full API response for reference
    raw_data = models.JSONField(
        default=dict,
        help_text="Complete API response"
    )
    
    # Metadata
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="When attributes were last fetched"
    )
    
    class Meta(TimestampedModel.Meta):
        db_table = "sofasport_player_attributes"
        ordering = ["athlete", "-year_shift"]
        indexes = [
            models.Index(fields=["athlete"]),
            models.Index(fields=["sofasport_player_id"]),
            models.Index(fields=["year_shift"]),
            models.Index(fields=["position"]),
        ]
        unique_together = [["athlete", "year_shift", "is_average"]]
    
    def __str__(self) -> str:
        avg_str = " (avg)" if self.is_average else ""
        return f"{self.athlete.web_name} - YearShift {self.year_shift}{avg_str}"


class WildcardSimulation(TimestampedModel):
    """
    Wildcard team simulator - tracks user-created wildcard drafts.
    Uses hybrid storage: minimal DB entry for tracking, localStorage for editing.
    """
    code = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        help_text="Unique shareable code (e.g., WC-ABC123)"
    )
    
    # Team data
    squad_data = models.JSONField(
        default=dict,
        help_text="Player selections, formation, captain choices"
    )
    
    # Cached calculations
    total_cost = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('0.0'),
        help_text="Total squad cost in millions"
    )
    predicted_points = models.IntegerField(
        default=0,
        help_text="Predicted total points for next gameweek"
    )
    
    # Metadata
    gameweek = models.IntegerField(
        null=True,
        blank=True,
        help_text="Target gameweek for this wildcard"
    )
    team_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional user-provided team name"
    )
    
    # Tracking
    is_saved = models.BooleanField(
        default=False,
        help_text="True if user clicked 'Save & Share', False if just drafting"
    )
    view_count = models.IntegerField(
        default=1,
        help_text="Number of times this team has been viewed"
    )
    
    class Meta(TimestampedModel.Meta):
        db_table = "wildcard_simulations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_saved"]),
        ]
    
    def __str__(self) -> str:
        status = "Saved" if self.is_saved else "Draft"
        return f"{self.code} - {status} ({self.created_at.strftime('%Y-%m-%d')})"
    
    @staticmethod
    def generate_code():
        """Generate a unique wildcard code."""
        import uuid
        return f"WC-{uuid.uuid4().hex[:6].upper()}"

