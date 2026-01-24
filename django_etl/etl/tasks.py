"""
Celery Tasks for SofaSport ETL Pipelines

Scheduled tasks for weekly data collection and updates.
"""
import subprocess
import logging
import os
from pathlib import Path
from celery import shared_task
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from io import StringIO

from .api_views import (
    _build_price_change_predictor_payload,
    _build_price_predictor_history_payload,
    _price_change_predictor_cache_key,
    _price_predictor_history_cache_key,
)
logger = logging.getLogger(__name__)

# Base directory for ETL scripts
ETL_DIR = Path(__file__).parent.parent / 'sofa_sport' / 'scripts'
# Django project directory
DJANGO_DIR = Path(__file__).parent.parent


def run_etl_script(script_name, timeout):
    """
    Helper function to run ETL scripts with Django context.
    
    Args:
        script_name: Name of the script file
        timeout: Timeout in seconds
    
    Returns:
        dict: Status and output of the script execution
    """
    script_path = ETL_DIR / script_name
    
    try:
        # Run the script from Django root directory so imports work correctly
        # Add Django root to PYTHONPATH so scripts can import fpl_platform
        env = os.environ.copy()
        env['PYTHONPATH'] = str(DJANGO_DIR)
        
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(DJANGO_DIR),  # Run from Django root, not scripts dir
            env=env
        )
        
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Task exceeded {timeout} seconds"
        }
    except Exception as e:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e)
        }


@shared_task(name='etl.tasks.update_fixture_mappings')
def update_fixture_mappings():
    """
    Update fixture mappings between FPL and SofaSport.
    Runs: Monday 2:00 AM
    """
    logger.info("Starting fixture mapping update...")
    
    result = run_etl_script('build_fixture_mapping.py', timeout=600)
    
    if result["returncode"] == 0:
        logger.info(f"✅ Fixture mapping completed: {result['stdout']}")
        return {"status": "success", "output": result['stdout']}
    else:
        logger.error(f"❌ Fixture mapping failed: {result['stderr']}")
        return {"status": "error", "output": result['stderr']}


@shared_task(name='etl.tasks.update_lineups')
def update_lineups():
    """
    Update player lineups for recent gameweeks.
    Runs: Tuesday 3:00 AM
    """
    logger.info("Starting lineups update...")
    
    result = run_etl_script('build_lineups_etl.py', timeout=900)
    
    if result["returncode"] == 0:
        logger.info(f"✅ Lineups update completed: {result['stdout']}")
        return {"status": "success", "output": result['stdout']}
    else:
        logger.error(f"❌ Lineups update failed: {result['stderr']}")
        return {"status": "error", "output": result['stderr']}


@shared_task(name='etl.tasks.collect_heatmaps')
def collect_heatmaps():
    """
    Collect player heatmaps for recent matches.
    Runs: Tuesday 4:00 AM (after lineups complete)
    """
    logger.info("Starting heatmap collection...")
    
    # Increased timeout to 3600s (60 minutes) to allow long API runs
    result = run_etl_script('build_heatmap_etl.py', timeout=3600)
    
    if result["returncode"] == 0:
        logger.info(f"✅ Heatmap collection completed: {result['stdout']}")
        return {"status": "success", "output": result['stdout']}
    else:
        logger.error(f"❌ Heatmap collection failed: {result['stderr']}")
        return {"status": "error", "output": result['stderr']}


@shared_task(name='etl.tasks.update_season_stats')
def update_season_stats():
    """
    Update player season statistics.
    Runs: Wednesday 2:00 AM
    """
    logger.info("Starting season stats update...")
    
    result = run_etl_script('build_season_stats_etl.py', timeout=1200)
    
    if result["returncode"] == 0:
        logger.info(f"✅ Season stats update completed: {result['stdout']}")
        return {"status": "success", "output": result['stdout']}
    else:
        logger.error(f"❌ Season stats update failed: {result['stderr']}")
        return {"status": "error", "output": result['stderr']}


@shared_task(name='etl.tasks.update_radar_attributes')
def update_radar_attributes():
    """
    Update player radar chart attributes.
    Runs: Wednesday 3:00 AM (after season stats complete)
    """
    logger.info("Starting radar attributes update...")
    
    # Increased timeout to 3600s (60 minutes) to allow long API runs
    result = run_etl_script('build_radar_attributes_etl.py', timeout=3600)
    
    if result["returncode"] == 0:
        logger.info(f"✅ Radar attributes update completed: {result['stdout']}")
        return {"status": "success", "output": result['stdout']}
    else:
        logger.error(f"❌ Radar attributes update failed: {result['stderr']}")
        return {"status": "error", "output": result['stderr']}


# Celery Beat Schedule Configuration


@shared_task(name='etl.tasks.warm_price_predictor_cache')
def warm_price_predictor_cache():
    logger.info("Warming price predictor cache...")
    results = {}

    try:
        limit = 10
        payload = _build_price_change_predictor_payload(limit)
        cache.set(_price_change_predictor_cache_key(limit), payload, 1800)
        results["price_predictor"] = "ok"
    except Exception as exc:
        logger.exception("Price predictor warm failed")
        results["price_predictor"] = f"error: {exc}"

    history_specs = [
        {"top": 5, "limit": 30, "metric": "transfers", "direction_filter": None},
        {"top": 5, "limit": 30, "metric": "transfers", "direction_filter": "in"},
        {"top": 5, "limit": 30, "metric": "transfers", "direction_filter": "out"},
    ]

    for spec in history_specs:
        label = spec["direction_filter"] or "all"
        try:
            cache_key = _price_predictor_history_cache_key(
                spec["limit"],
                spec["top"],
                spec["metric"],
                spec["direction_filter"],
                "",
                "",
            )
            payload = _build_price_predictor_history_payload(
                limit=spec["limit"],
                top=spec["top"],
                metric=spec["metric"],
                player_ids_param="",
                directions_param="",
                direction_filter=spec["direction_filter"],
            )
            cache.set(cache_key, payload, 1800)
            results[f"history:{label}"] = "ok"
        except LookupError as exc:
            logger.warning("Price predictor history warm skipped: %s", exc)
            results[f"history:{label}"] = f"empty: {exc}"
        except Exception as exc:
            logger.exception("Price predictor history warm failed")
            results[f"history:{label}"] = f"error: {exc}"

    return results


@shared_task(name='etl.tasks.run_manual_update')
def run_manual_update(script_name: str):
    """
    Manually trigger any ETL script.
    
    Args:
        script_name: Name of the ETL script (e.g., 'build_fixture_mapping.py')
    """
    logger.info(f"Starting manual update: {script_name}")
    script_path = ETL_DIR / script_name
    
    if not script_path.exists():
        logger.error(f"❌ Script not found: {script_name}")
        return {"status": "error", "output": f"Script {script_name} not found"}
    
    try:
        # Align manual runner with run_etl_script
        env = os.environ.copy()
        env['PYTHONPATH'] = str(DJANGO_DIR)
        
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour max
            cwd=str(DJANGO_DIR),  # Run from Django root
            env=env
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Manual update completed: {script_name}")
            return {"status": "success", "output": result.stdout}
        else:
            logger.error(f"❌ Manual update failed: {script_name}")
            return {"status": "error", "output": result.stderr}
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Manual update timed out: {script_name}")
        return {"status": "timeout", "output": "Task exceeded 1 hour"}
    except Exception as e:
        logger.error(f"❌ Manual update error: {str(e)}")
        return {"status": "error", "output": str(e)}


@shared_task(name='etl.tasks.sync_fixture_odds')
def sync_fixture_odds(days_ahead=7):
    """
    Fetch and update betting odds for upcoming fixtures.
    Runs: Every 10 minutes during season
    
    Args:
        days_ahead: Number of days ahead to fetch odds for (default: 7)
    """
    logger.info(f"Starting fixture odds sync for next {days_ahead} days...")
    
    result = run_etl_script('fetch_fixture_odds.py', timeout=600)
    
    if result["returncode"] == 0:
        logger.info(f"✅ Fixture odds sync completed: {result['stdout']}")
        return {"status": "success", "output": result['stdout']}
    else:
        logger.error(f"❌ Fixture odds sync failed: {result['stderr']}")
        return {"status": "error", "output": result['stderr']}


@shared_task(name='etl.tasks.run_daily_pipeline')
def run_daily_pipeline():
    """
    Coordinator task for the Daily FPL ETL Pipeline.
    Replaces the Render Cron Job.
    Sequence:
    1. run_fpl_etl (Bootstrap basic FPL data)
    2. run_fpl_etl commands (detailed sync) - actually run_fpl_etl does the main work
    3. load_sofasport_data type=heatmaps (via collect_heatmaps task)
    4. sync_top100
    5. clear_cache
    """
    logger.info("🚀 Starting Daily ETL Pipeline...")
    results = {}

    # Step 1: Run FPL ETL (Core Data)
    try:
        logger.info("Step 1: Running FPL ETL...")
        out = StringIO()
        call_command('run_fpl_etl', stdout=out, stderr=out)
        results['run_fpl_etl'] = "✅ " + out.getvalue()
    except Exception as e:
        logger.error(f"❌ Step 1 Failed: {str(e)}")
        results['run_fpl_etl'] = f"Error: {str(e)}"
        # We might want to abort or continue depending on severity. 
        # Usually if core data fails, we shoulder stop. 
        return results

    # Step 2: Collect Heatmaps (SofaSport)
    # This was originally: python manage.py load_sofasport_data --task=heatmaps
    # We have an existing task for this: collect_heatmaps
    # We call it synchronously here to ensure order
    try:
        logger.info("Step 2: Collecting Heatmaps...")
        # We can call the task function directly since it's just a function decorated with @shared_task
        # But to be safe with Celery context, we often just run the logic. 
        # Since collect_heatmaps uses subprocess to run a script, we can just call it.
        start_heatmaps = collect_heatmaps() # Valid in Celery 5+ if same worker
        results['collect_heatmaps'] = start_heatmaps
    except Exception as e:
         logger.error(f"❌ Step 2 Failed: {str(e)}")
         results['collect_heatmaps'] = f"Error: {str(e)}"

    # Step 3: Sync Top 100
    try:
        logger.info("Step 3: Syncing Top 100 managers...")
        out = StringIO()
        call_command('sync_top100', stdout=out, stderr=out)
        results['sync_top100'] = "✅ " + out.getvalue()
    except Exception as e:
        logger.error(f"❌ Step 3 Failed: {str(e)}")
        results['sync_top100'] = f"Error: {str(e)}"

    # Step 4: Clear Cache
    try:
        logger.info("Step 4: Clearing Cache...")
        out = StringIO()
        call_command('clear_cache', stdout=out, stderr=out)
        results['clear_cache'] = "✅ " + out.getvalue()
    except Exception as e:
        logger.error(f"❌ Step 4 Failed: {str(e)}")
        results['clear_cache'] = f"Error: {str(e)}"

    logger.info("🏁 Daily ETL Pipeline Completed")
    return results
