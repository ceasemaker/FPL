from django.contrib import admin
from django.urls import path

from etl.api_views import landing_snapshot, fixtures_by_gameweek, players_list, player_detail, dream_team
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
    path("api/players/", players_list, name="players-list"),
    path("api/players/<int:player_id>/", player_detail, name="player-detail"),
    path("api/dream-team/", dream_team, name="dream-team"),
    # FPL API Proxy endpoints
    path("api/fpl/entry/<int:manager_id>/", proxy_manager_summary, name="fpl-manager-summary"),
    path("api/fpl/entry/<int:manager_id>/history/", proxy_manager_history, name="fpl-manager-history"),
    path("api/fpl/entry/<int:manager_id>/event/<int:event_id>/picks/", proxy_manager_picks, name="fpl-manager-picks"),
    path("api/fpl/bootstrap-static/", proxy_bootstrap_static, name="fpl-bootstrap-static"),
    path("api/fpl/event/<int:event_id>/live/", proxy_event_live, name="fpl-event-live"),
    path("api/fpl/fixtures/", proxy_fixtures, name="fpl-fixtures"),
    path("api/fpl/element-summary/<int:player_id>/", proxy_player_summary, name="fpl-player-summary"),
]
