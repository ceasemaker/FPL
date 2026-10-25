from __future__ import annotations

from django.core.cache import cache
from django.test import TestCase

from ..models import Athlete, Team
from ..services.price_changes import label, refresh_price_changes

BOOTSTRAP = {
    "game_config": {"settings": {"price_change_deadlines": ["2026-10-26T00:00:00Z", "2026-10-27T00:00:00Z"]},
                    "status": {"price_change_last_updated": "2026-10-25T08:50:13Z"}},
    "elements": [
        {"id": 1, "price_change_percent": "106.1", "price_change_hourly_rate": 1587, "price_change_locked_until": None,
         "price_change_calibrating": False,
         "price_change_projections": [{"offset": 0, "projected_percent": "123.9", "likelihood": 5}]},
        {"id": 2, "price_change_percent": "-93.8", "price_change_hourly_rate": -4,
         "price_change_locked_until": "2026-10-29T06:30:07Z", "price_change_calibrating": False,
         "price_change_projections": [{"offset": 0, "projected_percent": "-94.9", "likelihood": -3}]},
    ],
}


class FakeClient:
    def get_bootstrap_static(self):
        return BOOTSTRAP


class PriceChangeTests(TestCase):
    def setUp(self):
        cache.clear()
        team = Team.objects.create(id=1, code=3, name="Arsenal", short_name="ARS")
        for i, name in ((1, "Konsa"), (2, "Meunier")):
            Athlete.objects.create(id=i, code=100 + i, first_name=name, second_name=name, web_name=name,
                                   now_cost=46, element_type=2, team=team, team_code=3)

    def test_labels_follow_fpl_likelihood(self):
        self.assertEqual([label(x) for x in (5, 4, 3, 0, -3, -4, -5, None)],
                         ["Very likely to rise", "Likely to rise", "Unlikely to change", "Unlikely to change",
                          "Unlikely to change", "Likely to drop", "Very likely to drop", "Unlikely to change"])

    def test_refresh_updates_players_and_serves_the_countdown(self):
        self.assertEqual(refresh_price_changes(FakeClient())["updated"], 2)
        payload = self.client.get("/api/price-changes/").json()
        self.assertEqual(payload["meta"]["deadlines"][0], "2026-10-26T00:00:00Z")
        rows = {r["name"]: r for r in payload["players"]}
        self.assertEqual((rows["Konsa"]["progress"], rows["Konsa"]["predicted"], rows["Konsa"]["label"], rows["Konsa"]["trend"]),
                         (106.1, 123.9, "Very likely to rise", "up"))
        self.assertEqual(rows["Meunier"]["label"], "Unlikely to change")
        self.assertTrue(rows["Meunier"]["lockedUntil"].startswith("2026-10-29"))
        self.assertEqual([r["name"] for r in payload["players"]], ["Konsa", "Meunier"], "biggest movers first")
