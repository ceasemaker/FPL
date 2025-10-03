import requests
import json
import redis
import os
from dotenv import load_dotenv
import time
import logging
import yaml
import psycopg2 

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


# --- Redis Configuration ---
# Load Redis connection details from environment variables
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")

#--- Postgres Configuration ---
POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB")

pg_config = {
    "host": POSTGRES_HOST,
    "port": POSTGRES_PORT,
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
    "dbname": POSTGRES_DB
}

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
   
# a function that reads from a redis key
def read_from_redis(key):
    if redis_client:
        return redis_client.get(key)
    else:
        return None

#write a function that writes to PG and also take in the table name, and the confilict ID's as a list, It also needs to take a list of dict to write

def bulk_write_to_pg(table_name, conflict_id_list, list_of_dict, pg_config):
    # establish a connection to Postgres
    conn = None
    try:
        # read connection parameters
        params = pg_config
        # connect to the PostgreSQL server
        logger.info('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)
        # create a cursor
        cur = conn.cursor()
        
        # Get the first item to determine the columns
        first_item = list_of_dict[0]
        columns = first_item.keys()
        
        # Create the SQL statement
        sql = """INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) DO NOTHING""".format(
            table_name,
            ','.join(columns),
            ','.join(['%s'] * len(columns)),
            ','.join(conflict_id_list)
        )
        
        # Convert any JSON/dict values to strings
        def convert_value(value):
            if isinstance(value, dict):
                return json.dumps(value)
            return value
        
        # Prepare the values for insertion
        values = []
        for item in list_of_dict:
            converted_values = [convert_value(v) for v in item.values()]
            values.append(tuple(converted_values))
        
        # bulk insert
        cur.executemany(sql, values)
        # commit the changes
        conn.commit()
        # close the cursor and connection
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
    finally:
        if conn is not None:
            conn.close()
            logger.info('Database connection closed.')



if __name__ == "__main__":
    while True: 
        generic_data_dict = json.loads(read_from_redis("general_info"))
        team_data_dict = generic_data_dict["teams"]
        bulk_write_to_pg("teams",["id"],team_data_dict,pg_config)
        player_data = generic_data_dict["elements"]
        bulk_write_to_pg("athletes",["id"],player_data,pg_config)
        player_data_list=[]
        for game_week in range(1,39):
            game_week_data = read_from_redis("game_week_data_{}".format(game_week))
            game_week_data_dict = json.loads(game_week_data)["elements"]
            for player in game_week_data_dict:
                # add a key game_week to the player dictionary
                player["game_week"] = game_week
                #take all the stats from the key 'stats' and add them to the player dictionary then remove the stats key
                player.update(player.pop("stats"))
                #remove the key 'explain'
                player.pop("explain", None)
                player.pop("modified", None)
                player_data_list.append(player)
        bulk_write_to_pg("athlete_stats",["id","game_week"],player_data_list,pg_config)
        logger.info("Data written to Postgres successfully.")
        logger.info("Sleeping for 5 minutes...")
        time.sleep(300)
        


        

    


