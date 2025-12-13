from django.contrib import admin
from django.urls import path

from etl.api_views import (
    landing_snapshot,
    fixtures_by_gameweek,
    players_list,
    player_detail,
    dream_team,
    # SofaSport endpoints
    player_radar_attributes,
    player_season_stats,
    player_heatmap,
    player_match_stats,
    compare_players_radar,
    player_recent_matches,
    # Top 100 endpoints
    top100_template,
    best_value_players,
    top100_points_chart,
    top100_transfers,
    top100_differentials,
)
from etl.fpl_proxy_views import (
    proxy_manager_summary,
    proxy_manager_history,
    proxy_manager_picks,
    proxy_bootstrap_static,
    proxy_event_live,
    proxy_fixtures,
    proxy_player_summary,
)
from etl.views_wildcard import (
    wildcard_home,
    wildcard_view,
    track_wildcard_start,
    get_wildcard_team,
    save_wildcard_team,
    wildcard_stats,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/landing/", landing_snapshot, name="landing-snapshot"),
    path("api/fixtures/", fixtures_by_gameweek, name="fixtures-by-gameweek"),
    path("api/players/", players_list, name="players-list"),
    path("api/players/<int:player_id>/", player_detail, name="player-detail"),
    path("api/dream-team/", dream_team, name="dream-team"),
    
    # SofaSport API endpoints
    path("api/sofasport/player/<int:player_id>/radar/", player_radar_attributes, name="player-radar-attributes"),
    path("api/sofasport/player/<int:player_id>/season-stats/", player_season_stats, name="player-season-stats"),
    path("api/sofasport/player/<int:player_id>/heatmap/<int:gameweek>/", player_heatmap, name="player-heatmap"),
    path("api/sofasport/player/<int:player_id>/match-stats/<int:gameweek>/", player_match_stats, name="player-match-stats"),
    path("api/sofasport/player/<int:player_id>/recent-matches/", player_recent_matches, name="player-recent-matches"),
    path("api/sofasport/compare/radar/", compare_players_radar, name="compare-players-radar"),
    
    # FPL API Proxy endpoints
    path("api/fpl/entry/<int:manager_id>/", proxy_manager_summary, name="fpl-manager-summary"),
    path("api/fpl/entry/<int:manager_id>/history/", proxy_manager_history, name="fpl-manager-history"),
    path("api/fpl/entry/<int:manager_id>/event/<int:event_id>/picks/", proxy_manager_picks, name="fpl-manager-picks"),
    path("api/fpl/bootstrap-static/", proxy_bootstrap_static, name="fpl-bootstrap-static"),
    path("api/fpl/event/<int:event_id>/live/", proxy_event_live, name="fpl-event-live"),
    path("api/fpl/fixtures/", proxy_fixtures, name="fpl-fixtures"),
    path("api/fpl/element-summary/<int:player_id>/", proxy_player_summary, name="fpl-player-summary"),
    
    # Wildcard Simulator endpoints
    path("wildcard/", wildcard_home, name="wildcard-home"),
    path("wildcard/<str:code>/", wildcard_view, name="wildcard-view"),
    path("api/wildcard/track/", track_wildcard_start, name="wildcard-track-start"),
    path("api/wildcard/<str:code>/", get_wildcard_team, name="wildcard-get"),
    path("api/wildcard/<str:code>/save/", save_wildcard_team, name="wildcard-save"),
    path("api/wildcard/stats/", wildcard_stats, name="wildcard-stats"),
    
    # Top 100 Manager endpoints
    path("api/top100/template/", top100_template, name="top100-template"),
    path("api/top100/best-value/", best_value_players, name="top100-best-value"),
    path("api/top100/chart/", top100_points_chart, name="top100-chart"),
    path("api/top100/transfers/", top100_transfers, name="top100-transfers"),
    path("api/top100/differentials/", top100_differentials, name="top100-differentials"),
]
