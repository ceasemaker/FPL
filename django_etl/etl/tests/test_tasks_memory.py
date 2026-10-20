from __future__ import annotations

from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings

from .. import tasks

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCMEM)
class CrashLoopGuardTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_attempts_are_capped_per_key(self):
        self.assertTrue(tasks.claim_attempt("daily:2026-10-20", limit=2))
        self.assertTrue(tasks.claim_attempt("daily:2026-10-20", limit=2))
        self.assertFalse(tasks.claim_attempt("daily:2026-10-20", limit=2))
        self.assertTrue(tasks.claim_attempt("daily:2026-10-21", limit=2))

    def test_pipeline_skips_after_two_attempts_and_runs_steps_in_child_processes(self):
        with mock.patch.object(tasks, "run_manage", return_value={"status": "success", "output": ""}) as manage, \
                mock.patch.object(tasks, "run_etl_script", return_value={"returncode": 0, "stdout": "", "stderr": ""}):
            tasks.run_daily_pipeline()
            tasks.run_daily_pipeline()
            third = tasks.run_daily_pipeline()
        self.assertEqual(third["status"], "skipped")
        commands = [call.args[0] for call in manage.call_args_list]
        self.assertIn("run_fpl_etl", commands)
        self.assertNotIn("run_forecast", commands, "forecast training stays off unless FORECAST_IN_WORKER is set")

    def test_backtest_task_no_longer_runs_in_the_worker(self):
        with mock.patch.object(tasks, "run_manage") as manage:
            self.assertEqual(tasks.backtest_forecast()["status"], "skipped")
        manage.assert_not_called()
