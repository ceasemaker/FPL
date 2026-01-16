from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import timezone

from ..services.etl_runner import PipelineConfig, _parse_date, _parse_datetime, _to_decimal


class ParserHelpersTests(SimpleTestCase):
    def test_to_decimal(self) -> None:
        self.assertEqual(_to_decimal("1.23"), Decimal("1.23"))
        self.assertIsNone(_to_decimal(None))
        self.assertEqual(_to_decimal(0), Decimal("0"))

    def test_parse_datetime(self) -> None:
        dt = _parse_datetime("2024-08-12T12:30:00Z")
        assert dt is not None
        self.assertTrue(timezone.is_aware(dt))
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_parse_date(self) -> None:
        parsed = _parse_date("2024-08-12")
        assert parsed is not None
        self.assertIsInstance(parsed, date)
        self.assertEqual(parsed.isoformat(), "2024-08-12")


class PipelineConfigTests(SimpleTestCase):
    def test_defaults(self) -> None:
        config = PipelineConfig()
        self.assertFalse(config.loop)
        self.assertEqual(config.sleep_seconds, 300)
        self.assertTrue(config.snapshot_payloads)
