from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from django.test import SimpleTestCase


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "sofa_sport" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import fetch_fixture_odds as odds  # noqa: E402


class FixtureOddsParserTests(SimpleTestCase):
    def test_parses_rapidapi_envelope(self) -> None:
        payload = {
            "data": [{
                "marketGroup": "1X2",
                "marketPeriod": "Full-time",
                "choices": [
                    {"name": "1", "fractionalValue": "1.80"},
                    {"name": "X", "fractionalValue": "3.50"},
                    {"name": "2", "fractionalValue": "4.20"},
                ],
            }]
        }

        parsed = odds.parse_odds_response(payload)

        self.assertEqual(parsed["home_odds"], Decimal("1.80"))
        self.assertEqual(parsed["draw_odds"], Decimal("3.50"))
        self.assertEqual(parsed["away_odds"], Decimal("4.20"))

    def test_parses_public_markets_and_fractional_values(self) -> None:
        payload = {
            "markets": [{
                "id": 1,
                "marketName": "Full time",
                "choices": [
                    {"name": "1", "fractionalValue": "4/5"},
                    {"name": "X", "fractionalValue": "5/2"},
                    {"name": "2", "fractionalValue": "16/5"},
                ],
            }]
        }

        parsed = odds.parse_odds_response(payload)

        self.assertEqual(parsed["home_odds"], Decimal("1.8"))
        self.assertEqual(parsed["draw_odds"], Decimal("3.5"))
        self.assertEqual(parsed["away_odds"], Decimal("4.2"))

    def test_parses_totals_and_btts_markets(self) -> None:
        payload = {
            "markets": [
                {
                    "marketName": "Over/Under 2.5",
                    "choices": [
                        {"name": "Over", "decimalValue": "1.90"},
                        {"name": "Under", "decimalValue": "2.00"},
                    ],
                },
                {
                    "marketGroup": "Both teams to score",
                    "choices": [
                        {"name": "Yes", "decimalValue": "1.75"},
                        {"name": "No", "decimalValue": "2.15"},
                    ],
                },
            ]
        }

        parsed = odds.parse_odds_response(payload)

        self.assertEqual(parsed["over_under_line"], Decimal("2.5"))
        self.assertEqual(parsed["over_odds"], Decimal("1.90"))
        self.assertEqual(parsed["under_odds"], Decimal("2.00"))
        self.assertEqual(parsed["btts_yes_odds"], Decimal("1.75"))
        self.assertEqual(parsed["btts_no_odds"], Decimal("2.15"))

    def test_default_rate_is_no_more_than_five_calls_per_minute(self) -> None:
        self.assertGreaterEqual(odds.RATE_LIMIT_DELAY, 12.0)

    def test_team_name_normalization(self) -> None:
        self.assertEqual(
            odds._normalize_team_name("Brighton & Hove Albion FC"),
            "brightonandhovealbion",
        )

    @patch.object(odds.requests, "get")
    def test_public_fetch_uses_key_free_endpoint(self, get: Mock) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"markets": []}
        response.raise_for_status.return_value = None
        get.return_value = response

        self.assertEqual(odds.fetch_odds_from_api(12345, source="public"), {"markets": []})

        args, kwargs = get.call_args
        self.assertEqual(args[0], f"{odds.SOFASCORE_PUBLIC_BASE_URL}/event/12345/1/odds")
        self.assertIsNone(kwargs["params"])
        self.assertNotIn("x-rapidapi-key", {key.lower() for key in kwargs["headers"]})

    @patch.object(odds.requests, "get")
    def test_public_403_stops_without_retrying(self, get: Mock) -> None:
        get.return_value = Mock(status_code=403)

        self.assertIsNone(odds.fetch_odds_from_api(12345, source="public"))
        self.assertEqual(get.call_count, 1)

    @patch.object(odds.requests, "get")
    def test_public_fetch_updates_persistent_throttle_tally(self, get: Mock) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"markets": []}
        response.raise_for_status.return_value = None
        get.return_value = response
        throttle = Mock()
        audit = Mock(payload={"status": "started"})
        throttle.before_request.return_value = audit

        odds.fetch_odds_from_api(12345, source="public", throttle=throttle)

        throttle.before_request.assert_called_once()
        throttle.finish_request.assert_called_once_with(audit, status_code=200)

    @patch.object(odds.requests, "get")
    def test_schedule_refresh_shares_the_persistent_throttle(self, get: Mock) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"events": [{"id": 7}]}
        response.raise_for_status.return_value = None
        get.return_value = response
        throttle = Mock()
        audit = Mock(payload={"status": "started"})
        throttle.before_request.return_value = audit

        events = odds.fetch_public_upcoming_events(throttle)

        self.assertEqual(events, [{"id": 7}])
        throttle.before_request.assert_called_once()
        throttle.finish_request.assert_called_once_with(audit, status_code=200)


class ApiDojoOddsTests(SimpleTestCase):
    """The RapidAPI "Sofascore" API by API Dojo (free plan: 500 requests a month)."""

    @patch.object(odds.requests, "get")
    def test_apidojo_fetch_uses_match_odds_endpoint_and_the_budget(self, get: Mock) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {"markets": []}
        response.raise_for_status.return_value = None
        get.return_value = response
        throttle = Mock()
        throttle.before_request.return_value = Mock(payload={"status": "started"})

        self.assertEqual(odds.fetch_odds_from_api(8897222, source="apidojo", throttle=throttle), {"markets": []})

        args, kwargs = get.call_args
        self.assertTrue(args[0].endswith("/matches/get-all-odds"))
        self.assertEqual(kwargs["params"], {"matchId": "8897222"})
        throttle.before_request.assert_called_once()

    @patch.object(odds.requests, "get")
    def test_apidojo_quota_or_key_errors_stop_without_retrying(self, get: Mock) -> None:
        for status in (401, 403, 429):
            get.reset_mock()
            get.return_value = Mock(status_code=status)
            throttle = Mock()
            throttle.before_request.return_value = Mock(payload={"status": "started"})
            self.assertIsNone(odds.fetch_odds_from_api(1, source="apidojo", throttle=throttle))
            self.assertEqual(get.call_count, 1, f"HTTP {status} must not be retried")
            self.assertTrue(throttle.blocked)

    def test_monthly_cap_stops_before_the_request(self) -> None:
        throttle = odds.PublicRequestThrottle(run_date="2026-10-25")
        with patch.object(odds.PublicRequestThrottle, "calls_today", new=0), \
                patch.object(odds.PublicRequestThrottle, "calls_this_month", new=odds.MAX_CALLS_PER_MONTH):
            with self.assertRaises(odds.DailyCallLimitReached):
                throttle.before_request(1, "https://example.test")
        self.assertTrue(throttle.exhausted)
