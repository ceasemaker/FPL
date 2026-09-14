from django.contrib import admin
from django.urls import path, re_path

from fpl_platform.views import spa_index

from etl.api_views import (
    landing_snapshot,
    fixtures_by_gameweek,
    fixtures_ticker,
    price_change_predictor,
    price_predictor_history,
    image_proxy,
    players_list,
    player_detail,
    player_gameweeks,
    decision_dashboard,
    decision_research_report,
    player_analysis,
    player_analysis_catalogue,
    player_analysis_report,
    optimize_team,
    # SofaSport endpoints
    player_radar_attributes,
    player_season_stats,
    player_heatmap,
    player_match_stats,
    compare_players_radar,
    player_recent_matches,
    upcoming_fixtures_with_odds,
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


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/landing/", landing_snapshot, name="landing-snapshot"),
    path("api/fixtures/", fixtures_by_gameweek, name="fixtures-by-gameweek"),
    path("api/fixtures/ticker/", fixtures_ticker, name="fixtures-ticker"),
    path("api/price-predictor/", price_change_predictor, name="price-change-predictor"),
    path("api/price-predictor/history/", price_predictor_history, name="price-predictor-history"),
    path("api/image-proxy/", image_proxy, name="image-proxy"),
    path("api/players/", players_list, name="players-list"),
    path("api/players/<int:player_id>/", player_detail, name="player-detail"),
    path("api/players/<int:player_id>/gameweeks/", player_gameweeks, name="player-gameweeks"),
    path("api/decision-dashboard/", decision_dashboard, name="decision-dashboard"),
    path("api/decision-dashboard/research-report/", decision_research_report, name="decision-research-report"),
    path("api/decision-dashboard/players/", player_analysis_catalogue, name="player-analysis-catalogue"),
    path("api/decision-dashboard/player-analysis/", player_analysis, name="player-analysis"),
    path("api/decision-dashboard/player-report/", player_analysis_report, name="player-analysis-report"),
    path("api/optimize-team/", optimize_team, name="optimize-team"),
    
    # SofaSport API endpoints
    path("api/sofasport/player/<int:player_id>/radar/", player_radar_attributes, name="player-radar-attributes"),
    path("api/sofasport/player/<int:player_id>/season-stats/", player_season_stats, name="player-season-stats"),
    path("api/sofasport/player/<int:player_id>/heatmap/<int:gameweek>/", player_heatmap, name="player-heatmap"),
    path("api/sofasport/player/<int:player_id>/match-stats/<int:gameweek>/", player_match_stats, name="player-match-stats"),
    path("api/sofasport/player/<int:player_id>/recent-matches/", player_recent_matches, name="player-recent-matches"),
    path("api/sofasport/compare/radar/", compare_players_radar, name="compare-players-radar"),
    path("api/fixtures/upcoming/", upcoming_fixtures_with_odds, name="upcoming-fixtures-odds"),
    
    # FPL API Proxy endpoints
    path("api/fpl/entry/<int:manager_id>/", proxy_manager_summary, name="fpl-manager-summary"),
    path("api/fpl/entry/<int:manager_id>/history/", proxy_manager_history, name="fpl-manager-history"),
    path("api/fpl/entry/<int:manager_id>/event/<int:event_id>/picks/", proxy_manager_picks, name="fpl-manager-picks"),
    path("api/fpl/bootstrap-static/", proxy_bootstrap_static, name="fpl-bootstrap-static"),
    path("api/fpl/event/<int:event_id>/live/", proxy_event_live, name="fpl-event-live"),
    path("api/fpl/fixtures/", proxy_fixtures, name="fpl-fixtures"),
    path("api/fpl/element-summary/<int:player_id>/", proxy_player_summary, name="fpl-player-summary"),
    

    # Top 100 Manager endpoints
    path("api/top100/template/", top100_template, name="top100-template"),
    path("api/top100/best-value/", best_value_players, name="top100-best-value"),
    path("api/top100/chart/", top100_points_chart, name="top100-chart"),
    path("api/top100/transfers/", top100_transfers, name="top100-transfers"),
    path("api/top100/differentials/", top100_differentials, name="top100-differentials"),
]

# Everything that is not an API, admin or static path is the React app.
urlpatterns += [
    re_path(r"^(?!api/|admin/|static/|assets/).*$", spa_index, name="spa-index"),
]
