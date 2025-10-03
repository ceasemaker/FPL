from django.contrib import admin

from . import models


@admin.register(models.Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "short_name", "points", "position")
    search_fields = ("name", "short_name")
    list_filter = ("unavailable",)


@admin.register(models.Athlete)
class AthleteAdmin(admin.ModelAdmin):
    list_display = ("id", "web_name", "team", "now_cost", "total_points")
    search_fields = ("web_name", "first_name", "second_name")
    list_filter = ("team", "status")


@admin.register(models.AthleteStat)
class AthleteStatAdmin(admin.ModelAdmin):
    list_display = ("athlete", "game_week", "minutes", "total_points")
    search_fields = ("athlete__web_name",)
    list_filter = ("game_week", "in_dreamteam")


@admin.register(models.Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "kickoff_time", "team_h", "team_a")
    search_fields = ("team_h__name", "team_a__name")
    list_filter = ("event", "finished")


@admin.register(models.ElementSummary)
class ElementSummaryAdmin(admin.ModelAdmin):
    list_display = ("athlete", "updated_at")
    search_fields = ("athlete__web_name",)


@admin.register(models.EventStatus)
class EventStatusAdmin(admin.ModelAdmin):
    list_display = ("event", "status", "bonus_added", "date")
    list_filter = ("status", "bonus_added")


@admin.register(models.SetPieceNote)
class SetPieceNoteAdmin(admin.ModelAdmin):
    list_display = ("team", "last_updated")
    search_fields = ("team__name", "note")


@admin.register(models.RawEndpointSnapshot)
class RawEndpointSnapshotAdmin(admin.ModelAdmin):
    list_display = ("endpoint", "identifier", "created_at")
    search_fields = ("endpoint", "identifier")
    list_filter = ("endpoint",)
