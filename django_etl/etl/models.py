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
