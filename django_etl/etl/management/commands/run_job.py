"""Run one scheduled task's work in this process (used by Render one-off jobs).

    python manage.py run_job run_daily_pipeline
    python manage.py run_job --list

The Celery worker shares a 512 MB instance with the website, so heavy
scheduled tasks start a Render one-off job running this command instead of
running in the worker (see etl/tasks.py, "Render jobs").
"""
from __future__ import annotations

import json
import os

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run a scheduled task's work directly (inside a Render one-off job)"

    def add_arguments(self, parser):
        parser.add_argument("name", nargs="?")
        parser.add_argument("--list", action="store_true")

    def handle(self, *args, **options):
        from etl import tasks

        if options["list"] or not options["name"]:
            self.stdout.write("\n".join(sorted(tasks.JOBS)))
            return
        work = tasks.JOBS.get(options["name"])
        if work is None:
            raise CommandError(f"Unknown job {options['name']!r}; choose from {sorted(tasks.JOBS)}")
        # Child processes (manage.py steps) inherit this, so nothing re-offloads.
        os.environ[tasks.IN_JOB_ENV] = "1"
        result = work()
        self.stdout.write("RESULT_JSON " + json.dumps(result, default=str)[:4000])
        if isinstance(result, dict) and result.get("status") == "error":
            raise CommandError(f"{options['name']} failed")
