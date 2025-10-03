import requests
import json
import redis
import os
from dotenv import load_dotenv
import time
import logging
import yaml

load_dotenv()

logger = logging.getLogger(__name__)
# set logging level
logger.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


#Wite a function to load yaml file
def yaml_loader(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

load_urls = yaml_loader("config/urls.yaml")["URLS"]
BASE_URL = load_urls["BASE_URL"]
GENERAL_INFO = load_urls["GENERAL_INFO"]
FIXTURES = load_urls["FIXTURES"]
FIXTURES_BY_GAMEWEEK = load_urls["FIXTURES_BY_GAMEWEEK"]
PLAYER_DATA = load_urls["PLAYER_DATA"]
GAMEWEEK_DATA = load_urls["GAMEWEEK_DATA"]
MANAGER_SUMMARY = load_urls["MANAGER_SUMMARY"]
MANAGER_HISTORY = load_urls["MANAGER_HISTORY"]
MANAGER_TRANSFERS = load_urls["MANAGER_TRANSFERS"]
CURRENT_GAMEWEEK_TRANSFERS = load_urls["CURRENT_GAMEWEEK_TRANSFERS"]
CLASSIC_LEAGUE_STANDINGS = load_urls["CLASSIC_LEAGUE_STANDINGS"]
HEAD_TO_HEAD_LEAGUE_STANDINGS = load_urls["HEAD_TO_HEAD_LEAGUE_STANDINGS"]
MANAGER_TEAM = load_urls["MANAGER_TEAM"]
MANAGER_TEAM_BY_GAMEWEEK = load_urls["MANAGER_TEAM_BY_GAMEWEEK"]
EVENT_STATUS = load_urls["EVENT_STATUS"]
DREAM_TEAM = load_urls["DREAM_TEAM"]
SET_PIECE_NOTES = load_urls["SET_PIECE_NOTES"]
MANAGER_DATA = load_urls["MANAGER_DATA"]


# Redis lock timeout (in seconds)
LOCK_TIMEOUT = 10 
LOCK_ACQUIRE_TIMEOUT = 5  # How long to wait trying to acquire lock

# --- Redis Configuration ---
# Load Redis connection details from environment variables
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
# --- Initialize Redis Client ---
redis_client = None # Initialize as None
if not REDIS_HOST:
    logger.error("REDIS_HOST environment variable not set. Cannot connect to Redis.")
else:
    try:
        # Use redis.from_url() to connect using the full URL string
        # decode_responses=True decodes keys/values from bytes to strings automatically
        redis_client = redis.from_url( f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
        redis_client.ping() # Test the connection
        logger.info("Connected to Redis successfully using URL.")
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Error connecting to Redis using URL: {e}")
        redis_client = None # Ensure client is None if connection fails
    except Exception as e:
        logger.error(f"An unexpected error occurred during Redis connection: {e}")
        redis_client = None

class RedisLockManager:
    def __init__(self, redis_client, lock_key, timeout=LOCK_TIMEOUT):
        self.redis_client = redis_client
        self.lock = redis_client.lock(
            lock_key,
            timeout=timeout,
            blocking=True,
            blocking_timeout=LOCK_ACQUIRE_TIMEOUT
        )
        self.lock_acquired = False
        
    def __enter__(self):
        self.lock_acquired = self.lock.acquire()
        if not self.lock_acquired:
            logger.warning(f"Could not acquire lock: {self.lock.name}")
        return self.lock_acquired

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.lock_acquired:
                self.lock.release()
                logger.debug(f"🔓 Released lock: {self.lock.name}")
            else:
                logger.debug(f"Lock {self.lock.name} was never acquired")
        except redis.exceptions.LockError as e:
            logger.warning(f"Lock {self.lock.name} already expired: {e}")
        except Exception as e:
            logger.error(f"Error releasing lock {self.lock.name}: {e}")
        # Don't suppress exceptions
        return False

# lets write a polling function that polls every x seconds
def poll_api(url, redis_client, lock_key, timeout=LOCK_TIMEOUT):
    with RedisLockManager(redis_client, lock_key, timeout) as lock:
        if lock:
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                current_data = redis_client.get(lock_key)
                if current_data is None or current_data != json.dumps(data):
                    redis_client.set(lock_key, json.dumps(data), ex=3600)
                return data
            except requests.exceptions.RequestException as e:
                logger.error(f"Error polling API: {e}")
                return None
        else:
            logger.warning(f"Lock not acquired for {lock_key}")
            return None
    

#Let's poll GENERAL_INFO endpoint every 5 mins
while True:
    poll_api(BASE_URL + GENERAL_INFO, redis_client, "general_info")
    logger.info("Polled GENERAL_INFO endpoint successfully.")
    poll_api(BASE_URL + FIXTURES, redis_client, "fixtures")
    logger.info("Polled FIXTURES endpoint successfully.")
    for game_week in range(1,39):
        poll_api(BASE_URL + GAMEWEEK_DATA.format(event_id=game_week), redis_client, "game_week_data_{}".format(game_week))
        logger.info("Polled GAMEWEEK_DATA endpoint successfully.")   
    logger.info("Sleeping for 5 minutes...")
    time.sleep(300)


