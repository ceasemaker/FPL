"""
Celery Tasks for SofaSport ETL Pipelines

Scheduled tasks for weekly data collection and updates.
"""
import subprocess
import logging
from pathlib import Path
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# Base directory for ETL scripts
ETL_DIR = Path(__file__).parent.parent / 'sofa_sport' / 'scripts'


@shared_task(name='etl.tasks.update_fixture_mappings')
def update_fixture_mappings():
    """
    Update fixture mappings between FPL and SofaSport.
    Runs: Monday 2:00 AM
    """
    logger.info("Starting fixture mapping update...")
    script_path = ETL_DIR / 'build_fixture_mapping.py'
    
    try:
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes
            cwd=str(ETL_DIR)
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Fixture mapping completed: {result.stdout}")
            return {"status": "success", "output": result.stdout}
        else:
            logger.error(f"❌ Fixture mapping failed: {result.stderr}")
            return {"status": "error", "output": result.stderr}
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Fixture mapping timed out")
        return {"status": "timeout", "output": "Task exceeded 10 minutes"}
    except Exception as e:
        logger.error(f"❌ Fixture mapping error: {str(e)}")
        return {"status": "error", "output": str(e)}


@shared_task(name='etl.tasks.update_lineups')
def update_lineups():
    """
    Update player lineups for recent gameweeks.
    Runs: Tuesday 3:00 AM
    """
    logger.info("Starting lineups update...")
    script_path = ETL_DIR / 'build_lineups_etl.py'
    
    try:
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=900,  # 15 minutes
            cwd=str(ETL_DIR)
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Lineups update completed: {result.stdout}")
            return {"status": "success", "output": result.stdout}
        else:
            logger.error(f"❌ Lineups update failed: {result.stderr}")
            return {"status": "error", "output": result.stderr}
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Lineups update timed out")
        return {"status": "timeout", "output": "Task exceeded 15 minutes"}
    except Exception as e:
        logger.error(f"❌ Lineups update error: {str(e)}")
        return {"status": "error", "output": str(e)}


@shared_task(name='etl.tasks.collect_heatmaps')
def collect_heatmaps():
    """
    Collect player heatmaps for recent matches.
    Runs: Tuesday 4:00 AM (after lineups complete)
    """
    logger.info("Starting heatmap collection...")
    script_path = ETL_DIR / 'build_heatmap_etl.py'
    
    try:
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minutes
            cwd=str(ETL_DIR)
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Heatmap collection completed: {result.stdout}")
            return {"status": "success", "output": result.stdout}
        else:
            logger.error(f"❌ Heatmap collection failed: {result.stderr}")
            return {"status": "error", "output": result.stderr}
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Heatmap collection timed out")
        return {"status": "timeout", "output": "Task exceeded 30 minutes"}
    except Exception as e:
        logger.error(f"❌ Heatmap collection error: {str(e)}")
        return {"status": "error", "output": str(e)}


@shared_task(name='etl.tasks.update_season_stats')
def update_season_stats():
    """
    Update player season statistics.
    Runs: Wednesday 2:00 AM
    """
    logger.info("Starting season stats update...")
    script_path = ETL_DIR / 'build_season_stats_etl.py'
    
    try:
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=1200,  # 20 minutes
            cwd=str(ETL_DIR)
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Season stats update completed: {result.stdout}")
            return {"status": "success", "output": result.stdout}
        else:
            logger.error(f"❌ Season stats update failed: {result.stderr}")
            return {"status": "error", "output": result.stderr}
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Season stats update timed out")
        return {"status": "timeout", "output": "Task exceeded 20 minutes"}
    except Exception as e:
        logger.error(f"❌ Season stats update error: {str(e)}")
        return {"status": "error", "output": str(e)}


@shared_task(name='etl.tasks.update_radar_attributes')
def update_radar_attributes():
    """
    Update player radar chart attributes.
    Runs: Wednesday 3:00 AM (after season stats complete)
    """
    logger.info("Starting radar attributes update...")
    script_path = ETL_DIR / 'build_radar_attributes_etl.py'
    
    try:
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=900,  # 15 minutes
            cwd=str(ETL_DIR)
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Radar attributes update completed: {result.stdout}")
            return {"status": "success", "output": result.stdout}
        else:
            logger.error(f"❌ Radar attributes update failed: {result.stderr}")
            return {"status": "error", "output": result.stderr}
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Radar attributes update timed out")
        return {"status": "timeout", "output": "Task exceeded 15 minutes"}
    except Exception as e:
        logger.error(f"❌ Radar attributes update error: {str(e)}")
        return {"status": "error", "output": str(e)}


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
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour max
            cwd=str(ETL_DIR)
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
