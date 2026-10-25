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
        self.assertNotIn("run_forecast", commands, "outside a job, forecast training stays off")

    def test_backtest_task_no_longer_runs_in_the_worker(self):
        with mock.patch.object(tasks, "run_manage") as manage:
            self.assertEqual(tasks.backtest_forecast()["status"], "skipped")
        manage.assert_not_called()


@override_settings(CACHES=LOCMEM)
class RenderJobTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_on_render_heavy_tasks_start_a_job_instead_of_running(self):
        env = {"RENDER_API_KEY": "test", "RENDER_SERVICE_ID": "srv-test"}
        with mock.patch.dict("os.environ", env), \
                mock.patch.object(tasks, "start_render_job", return_value={"status": "started", "job": "job-1"}) as start, \
                mock.patch.object(tasks, "run_manage") as manage:
            self.assertEqual(tasks.run_daily_pipeline()["status"], "started")
            tasks.run_daily_pipeline()
            self.assertEqual(tasks.run_daily_pipeline()["status"], "skipped", "two jobs a day at most")
        self.assertEqual([c.args[0] for c in start.call_args_list], ["run_daily_pipeline", "run_daily_pipeline"])
        manage.assert_not_called()

    def test_inside_a_job_the_steps_run_and_the_forecast_gets_its_own_job(self):
        env = {"RENDER_API_KEY": "test", "RENDER_SERVICE_ID": "srv-test", tasks.IN_JOB_ENV: "1"}
        with mock.patch.dict("os.environ", env), \
                mock.patch.object(tasks, "start_render_job", return_value={"status": "started"}) as start, \
                mock.patch.object(tasks, "run_manage", return_value={"status": "success", "output": ""}) as manage, \
                mock.patch.object(tasks, "run_etl_script", return_value={"returncode": 0, "stdout": "", "stderr": ""}):
            tasks.JOBS["run_daily_pipeline"]()
        self.assertIn("run_fpl_etl", [c.args[0] for c in manage.call_args_list])
        self.assertNotIn("run_forecast", [c.args[0] for c in manage.call_args_list])
        start.assert_called_once_with("run_forecast", tasks.FORECAST_COMMAND)

    def test_on_render_without_a_key_heavy_tasks_skip_instead_of_running_in_the_web_instance(self):
        with mock.patch.dict("os.environ", {"RENDER": "true"}), \
                mock.patch.object(tasks, "run_manage") as manage, mock.patch.object(tasks, "run_etl_script") as script:
            os_env = __import__("os").environ
            os_env.pop("RENDER_API_KEY", None)
            self.assertEqual(tasks.run_daily_pipeline()["status"], "skipped")
            self.assertEqual(tasks.run_forecast_task()["status"], "skipped")
        manage.assert_not_called()
        script.assert_not_called()


@override_settings(CACHES=LOCMEM)
class SofaSportSwitchTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_sofasport_tasks_skip_without_starting_a_job_while_switched_off(self):
        env = {"RENDER_API_KEY": "test", "RENDER_SERVICE_ID": "srv-test", "SOFASPORT_ENABLED": "false"}
        with mock.patch.dict("os.environ", env), \
                mock.patch.object(tasks, "start_render_job") as start, \
                mock.patch.object(tasks, "run_etl_script") as script:
            for task in (tasks.update_fixture_mappings, tasks.update_lineups, tasks.collect_heatmaps,
                         tasks.update_season_stats, tasks.update_radar_attributes):
                self.assertEqual(task()["status"], "skipped")
        start.assert_not_called()
        script.assert_not_called()

    def test_pipeline_skips_sofasport_steps_while_switched_off(self):
        env = {tasks.IN_JOB_ENV: "1", "SOFASPORT_ENABLED": "false", "SOFASCORE_ODDS_ENABLED": "false"}
        with mock.patch.dict("os.environ", env), \
                mock.patch.object(tasks, "run_manage", return_value={"status": "success", "output": ""}), \
                mock.patch.object(tasks, "run_etl_script") as script, \
                mock.patch.object(tasks, "start_render_job", return_value={"status": "started"}):
            results = tasks.JOBS["run_daily_pipeline"]()
        script.assert_not_called()
        self.assertEqual(results["update_lineups"]["status"], "skipped")
        self.assertEqual(results["sync_fixture_odds"]["status"], "skipped")


@override_settings(CACHES=LOCMEM)
class OddsSwitchTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_odds_have_their_own_switch(self):
        env = {"RENDER_API_KEY": "test", "RENDER_SERVICE_ID": "srv-test", "SOFASPORT_ENABLED": "false"}
        with mock.patch.dict("os.environ", {**env, "SOFASCORE_ODDS_ENABLED": "false"}), \
                mock.patch.object(tasks, "start_render_job") as start:
            self.assertEqual(tasks.sync_fixture_odds()["status"], "skipped")
        start.assert_not_called()
        with mock.patch.dict("os.environ", {**env, "SOFASCORE_ODDS_ENABLED": "true"}), \
                mock.patch.object(tasks, "start_render_job", return_value={"status": "started"}) as start:
            self.assertEqual(tasks.sync_fixture_odds()["status"], "started", "odds run even with the rest of SofaSport off")
        start.assert_called_once_with("sync_fixture_odds")
