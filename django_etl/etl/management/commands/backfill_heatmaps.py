"""
Management command to backfill heatmaps for GW1-6 (which were never collected).
"""
import logging
from django.core.management.base import BaseCommand
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill heatmaps for gameweeks 1-6"

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-gw",
            type=int,
            default=1,
            help="Minimum gameweek to backfill (default: 1)"
        )
        parser.add_argument(
            "--max-gw",
            type=int,
            default=6,
            help="Maximum gameweek to backfill (default: 6)"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-collection of heatmaps"
        )

    def handle(self, *args, **options):
        min_gw = options.get("min_gw", 1)
        max_gw = options.get("max_gw", 6)
        force = options.get("force", False)

        self.stdout.write(
            self.style.HTTP_INFO(
                f"🗺️  Backfilling heatmaps for GW{min_gw}-{max_gw}..."
            )
        )

        # Find the build_heatmap_etl.py script
        script_path = Path(__file__).parent.parent.parent.parent / "sofa_sport" / "scripts" / "build_heatmap_etl.py"

        if not script_path.exists():
            self.stderr.write(
                self.style.ERROR(
                    f"Script not found: {script_path}"
                )
            )
            return

        # Build command
        cmd = [sys.executable, str(script_path), f"--min-gw={min_gw}", f"--max-gw={max_gw}"]
        if force:
            cmd.append("--force")

        self.stdout.write(
            self.style.HTTP_INFO(
                f"Running: {' '.join(cmd)}"
            )
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=str(script_path.parent.parent.parent),
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Heatmap backfill completed successfully"
                    )
                )
                if result.stdout:
                    self.stdout.write(result.stdout)
            else:
                self.stderr.write(
                    self.style.ERROR(
                        f"❌ Heatmap backfill failed with code {result.returncode}"
                    )
                )
                if result.stderr:
                    self.stderr.write(result.stderr)

        except subprocess.TimeoutExpired:
            self.stderr.write(
                self.style.ERROR(
                    "❌ Heatmap backfill timed out (exceeded 1 hour)"
                )
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(
                    f"❌ Error running backfill: {str(e)}"
                )
            )
