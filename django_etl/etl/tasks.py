"""
Celery Tasks for SofaSport ETL Pipelines

Scheduled tasks for weekly data collection and updates.
"""
import subprocess
import logging
import os
from pathlib import Path
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from io import StringIO

# api_views pulls in pandas and the whole view layer; import it lazily inside the
# tasks that need it so the Celery worker/beat processes stay small on Render.
logger = logging.getLogger(__name__)

# Base directory for ETL scripts
ETL_DIR = Path(__file__).parent.parent / 'sofa_sport' / 'scripts'
# Django project directory
DJANGO_DIR = Path(__file__).parent.parent


def run_etl_script(script_name, timeout, *script_args):
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
            ['python', str(script_path), *map(str, script_args)],
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


def run_manage(command, *args, timeout=1800):
    """Run ``python manage.py <command>`` in a child process.

    The web service, the Celery worker and its child share one 512 MB
    instance. Python doesn't hand freed memory back to the OS, so a heavy step
    run inside the worker keeps the worker big for the rest of the pipeline,
    and the next step's child process then runs out of memory (Oct 2026
    crash loop). A child process returns everything when it exits.
    """
    try:
        result = subprocess.run(
            ['python', 'manage.py', command, *map(str, args)],
            capture_output=True, text=True, timeout=timeout, cwd=str(DJANGO_DIR),
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": f"{command} exceeded {timeout} seconds"}
    output = (result.stdout + result.stderr)[-2000:]
    if result.returncode != 0:
        logger.error("❌ %s failed (exit %s): %s", command, result.returncode, output)
        return {"status": "error", "output": output}
    return {"status": "success", "output": output}


def claim_attempt(key, limit, ttl=20 * 3600):
    """True if this run may go ahead: at most ``limit`` attempts per key.

    When the instance runs out of memory mid-task, Celery beat (its schedule
    file lives in /tmp, which a restart wipes) re-sends the task, and Redis
    re-delivers the unfinished message an hour later. Without a cap, one
    out-of-memory task restarts the instance again and again until Render
    suspends the service. The count lives in Redis, which survives restarts.
    """
    cache_key = f"task-attempts:{key}"
    cache.add(cache_key, 0, ttl)
    try:
        attempts = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, ttl)
        attempts = 1
    if attempts > limit:
        logger.warning("Skipping %s: attempt %s of %s already used", key, attempts, limit)
        return False
    return True


def forecast_in_worker():
    """Training the forecast peaks well above what the shared instance has free.

    Off until the training fits; see FORECAST_MODEL.md ("Production").
    """
    return os.getenv("FORECAST_IN_WORKER", "false").lower() in ("1", "true", "yes")


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
    from .api_views import _build_price_change_predictor_payload, _build_price_predictor_history_payload, _price_change_predictor_cache_key, _price_predictor_history_cache_key  # noqa: E402 (lazy: keeps pandas out of worker/beat)
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
def sync_fixture_odds(days_ahead=21):
    """
    Fetch and update betting odds for upcoming fixtures.
    Runs: Once daily. The script also enforces a persistent daily guard and
    no more than five public API calls per minute, including in Docker.
    
    Args:
        days_ahead: Number of days ahead to fetch odds for (default: 21)
    """
    logger.info(f"Starting fixture odds sync for next {days_ahead} days...")
    
    result = run_etl_script(
        'fetch_fixture_odds.py',
        900,
        '--days',
        days_ahead,
    )
    
    if result["returncode"] == 0:
        logger.info(f"✅ Fixture odds sync completed: {result['stdout']}")
        return {"status": "success", "output": result['stdout']}
    else:
        logger.error(f"❌ Fixture odds sync failed: {result['stderr']}")
        return {"status": "error", "output": result['stderr']}


@shared_task(name='etl.tasks.sync_football_data_odds')
def sync_football_data_odds():
    """One daily CSV request for historical odds calibration/backtesting."""
    logger.info("Starting daily Football-Data historical odds sync...")
    try:
        out = StringIO()
        call_command('sync_football_data_odds', stdout=out, stderr=out)
        output = out.getvalue()
        logger.info("Football-Data odds sync completed: %s", output)
        return {"status": "success", "output": output}
    except Exception as exc:
        logger.error("Football-Data odds sync failed: %s", exc)
        return {"status": "error", "output": str(exc)}


@shared_task(name='etl.tasks.run_daily_pipeline')
def run_daily_pipeline():
    """
    Coordinator task for the Daily FPL ETL Pipeline.
    Replaces the Render Cron Job.
    Sequence:
    1. run_fpl_etl (Bootstrap basic FPL data)
    2. update_fixture_mappings (SofaSport fixture mapping)
    3. update_lineups (SofaSport lineups + stats)
    4. collect_heatmaps (SofaSport player heatmaps)
    5. sync_top100
    6. clear_cache
    7. sync_fixture_odds (daily, rate-limited)
    8. populate_predictions (market-calibrated when odds exist)
    9. run_forecast (points forecast v2: train, forecast, shadow captain picks)
    10. sync_match_goals (this season's new Premier League goals, for Chart Lab's clutch goals)
    """
    from django.utils import timezone

    if not claim_attempt(f"daily-pipeline:{timezone.now():%Y-%m-%d}", limit=2):
        return {"status": "skipped", "reason": "already attempted twice today"}
    logger.info("🚀 Starting Daily ETL Pipeline...")
    results = {}

    # Step 1: Run FPL ETL (Core Data)
    try:
        logger.info("Step 1: Running FPL ETL...")
        results['run_fpl_etl'] = run_manage('run_fpl_etl')
        if results['run_fpl_etl']['status'] != 'success':
            return results
    except Exception as e:
        logger.error(f"❌ Step 1 Failed: {str(e)}")
        results['run_fpl_etl'] = f"Error: {str(e)}"
        # We might want to abort or continue depending on severity. 
        # Usually if core data fails, we shoulder stop. 
        return results

    # Step 2: Update SofaSport fixture mappings
    try:
        logger.info("Step 2: Updating fixture mappings...")
        results['update_fixture_mappings'] = update_fixture_mappings()
    except Exception as e:
        logger.error(f"❌ Step 2 Failed: {str(e)}")
        results['update_fixture_mappings'] = f"Error: {str(e)}"

    # Step 3: Update lineups and player stats
    try:
        logger.info("Step 3: Updating lineups...")
        results['update_lineups'] = update_lineups()
    except Exception as e:
        logger.error(f"❌ Step 3 Failed: {str(e)}")
        results['update_lineups'] = f"Error: {str(e)}"

    # Step 4: Collect Heatmaps (SofaSport)
    # This was originally: python manage.py load_sofasport_data --task=heatmaps
    # We have an existing task for this: collect_heatmaps
    # We call it synchronously here to ensure order
    try:
        logger.info("Step 4: Collecting Heatmaps...")
        # Since collect_heatmaps uses subprocess to run a script, we can just call it.
        start_heatmaps = collect_heatmaps() # Valid in Celery 5+ if same worker
        results['collect_heatmaps'] = start_heatmaps
    except Exception as e:
         logger.error(f"❌ Step 4 Failed: {str(e)}")
         results['collect_heatmaps'] = f"Error: {str(e)}"

    # Step 5: Sync Top 100
    try:
        logger.info("Step 5: Syncing Top 100 managers...")
        results['sync_top100'] = run_manage('sync_top100')
    except Exception as e:
        logger.error(f"❌ Step 5 Failed: {str(e)}")
        results['sync_top100'] = f"Error: {str(e)}"

    # Step 6: Clear Cache
    try:
        logger.info("Step 6: Clearing Cache...")
        results['clear_cache'] = run_manage('clear_cache')
    except Exception as e:
        logger.error(f"❌ Step 6 Failed: {str(e)}")
        results['clear_cache'] = f"Error: {str(e)}"

    # Step 7: Collect the daily odds snapshot before building projections.
    try:
        logger.info("Step 7: Collecting daily fixture odds...")
        results['sync_fixture_odds'] = sync_fixture_odds(days_ahead=8)
    except Exception as e:
        logger.error(f"❌ Step 7 Failed: {str(e)}")
        results['sync_fixture_odds'] = f"Error: {str(e)}"

    # Step 8: Populate predictions for next gameweek
    try:
        logger.info("Step 8: Populating next gameweek predictions...")
        results['populate_predictions'] = run_manage('train_prediction_model', '--skip-training')
    except Exception as e:
        logger.error(f"❌ Step 8 Failed: {str(e)}")
        results['populate_predictions'] = f"Error: {str(e)}"

    # Step 9: Points forecast v2 (also scores last week's shadow picks)
    try:
        logger.info("Step 9: Running the points forecast...")
        results['run_forecast'] = (run_manage('run_forecast') if forecast_in_worker()
                                   else {"status": "skipped", "reason": "FORECAST_IN_WORKER is off"})
    except Exception as e:
        logger.error(f"❌ Step 9 Failed: {str(e)}")
        results['run_forecast'] = f"Error: {str(e)}"

    # Step 10: New match goals (only matches not yet stored: ~10 requests a week)
    try:
        logger.info("Step 10: Syncing match goals...")
        results['sync_match_goals'] = run_manage('sync_match_goals')
    except Exception as e:
        logger.error(f"❌ Step 10 Failed: {str(e)}")
        results['sync_match_goals'] = f"Error: {str(e)}"

    logger.info("🏁 Daily ETL Pipeline Completed")
    return results


@shared_task(name='etl.tasks.retrain_prediction_model')
def retrain_prediction_model():
    """
    Retrain ML prediction models.
    Runs: Every Tuesday at 4:00 AM (after lineups update)
    """
    from django.utils import timezone

    if not claim_attempt(f"retrain-prediction-model:{timezone.now():%Y-%m-%d}", limit=1):
        return {"status": "skipped", "reason": "already attempted today"}
    logger.info("Starting ML model retraining...")
    return run_manage('train_prediction_model', timeout=3600)


@shared_task(name='etl.tasks.populate_predictions')
def populate_predictions():
    """
    Populate predictions for next gameweek (skip training).
    Called after daily ETL pipeline.
    """
    logger.info("Populating predictions for next gameweek...")
    return run_manage('train_prediction_model', '--skip-training')


@shared_task(name='etl.tasks.run_forecast')
def run_forecast_task():
    """Train the points forecast, write forecasts, log and score shadow captain picks."""
    if not forecast_in_worker():
        return {"status": "skipped", "reason": "FORECAST_IN_WORKER is off"}
    return run_manage('run_forecast')


@shared_task(name='etl.tasks.refresh_before_deadline')
def refresh_before_deadline():
    """Re-read team news and FPL's expected points close to a deadline.

    The daily pipeline runs at 03:30; team news often lands later on deadline
    day. Within 36 hours of a deadline this refreshes player availability, the
    deadline snapshot and the shadow picks, so the logged picks reflect what a
    manager could have known at the deadline.
    """
    from datetime import timedelta

    from django.utils import timezone

    from etl.services.etl_runner import _sync_athletes
    from etl.services.forecast_sync import next_deadline, sync_forecast_tables
    from etl.services.fpl_client import FPLClient

    with FPLClient() as client:
        bootstrap = client.get_bootstrap_static()
    upcoming = next_deadline(bootstrap.get("events", []))
    if upcoming is None or upcoming[1] - timezone.now() > timedelta(hours=36):
        return {"status": "skipped", "reason": "no deadline within 36 hours"}
    if not claim_attempt(f"refresh-before-deadline:{timezone.now():%Y-%m-%d-%H}", limit=1, ttl=3 * 3600):
        return {"status": "skipped", "reason": "already attempted this slot"}
    _sync_athletes(bootstrap.get("elements", []))
    sync_forecast_tables(bootstrap.get("events", []), bootstrap.get("elements", []))
    return run_forecast_task()


@shared_task(name='etl.tasks.backtest_forecast')
def backtest_forecast():
    """Retired: the backtest needs more memory than the web instance has.

    Kept registered so a queued or re-delivered message is consumed harmlessly
    instead of crashing the worker. Run it as a one-off Render job:
    ``cd django_etl && python manage.py backtest_forecast``.
    """
    logger.warning("backtest_forecast no longer runs in the worker; run it as a one-off job")
    return {"status": "skipped", "reason": "run as a one-off job"}
