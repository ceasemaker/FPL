import warnings
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import numpy as np
import requests
import time
from datetime import date
from pathlib import Path
warnings.filterwarnings("ignore")


REPO_ROOT = Path(__file__).resolve().parents[1]
SEASON = "2025"
START_GAMEWEEK = 1
END_GAMEWEEK = 38
SEASON_DATA_DIR = REPO_ROOT / "fpl_data" / SEASON


def get_json(url):
    for attempt in range(1, 6):
        try:
            response = requests.get(url, timeout=(10, 90))
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            if attempt == 5:
                raise
            wait_seconds = attempt * 3
            print(f"request failed; retrying in {wait_seconds}s: {url}")
            time.sleep(wait_seconds)

def top_players(league_id="314"):
    top_ids = []
    
    url="https://fantasy.premierleague.com/api/leagues-classic/{}/standings/?page_standings={}"
    for page in range(1,3):
        print(url.format(league_id,page))
        json = get_json(url.format(league_id,page))
        for obj in json["standings"]["results"]:
            flp_id = obj["entry"]
            top_ids.append(flp_id)
            
            
    return top_ids


def get_manager_transfers(user, player_lookup):
    api = f"https://fantasy.premierleague.com/api/entry/{user}/transfers"
    json = get_json(api)
    rows = []
    for obj in json:
        row = pd.DataFrame(pd.Series(obj)).T
        row["web_name_in"] = row["element_in"].map(player_lookup["web_name"])
        row["position_name_in"] = row["element_in"].map(player_lookup["position"])
        row["web_name_out"] = row["element_out"].map(player_lookup["web_name"])
        row["position_name_out"] = row["element_out"].map(player_lookup["position"])
        rows.append(row)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def get_top_100_tansfers(top_100_ids,week,df):
    player_lookup = df.drop_duplicates("id", keep="last").set_index("id").to_dict()
    with ThreadPoolExecutor(max_workers=8) as executor:
        frames = list(executor.map(
            lambda user: get_manager_transfers(user, player_lookup), top_100_ids
        ))
    return pd.concat([frame for frame in frames if not frame.empty], ignore_index=True)


def get_manager_team(user, week, player_lookup):
    api = f"https://fantasy.premierleague.com/api/entry/{user}/event/{week}/picks/"
    json = get_json(api)
    team_df = pd.DataFrame.from_dict(json["picks"])
    team_df["web_name"] = team_df["element"].map(player_lookup["web_name"])
    team_df["position_name"] = team_df["element"].map(player_lookup["position"])
    team_df["active_chip"] = json["active_chip"]
    return team_df


def get_top_100_teams(top_100_ids,week,df):
    player_lookup = df.drop_duplicates("id", keep="last").set_index("id").to_dict()
    with ThreadPoolExecutor(max_workers=8) as executor:
        frames = list(executor.map(
            lambda user: get_manager_team(user, week, player_lookup), top_100_ids
        ))
    return pd.concat(frames, ignore_index=True)

if "__main__"==__name__:
    overall_path = SEASON_DATA_DIR / "overall_player_data" / "overall_payer_data.csv"
    teams_dir = SEASON_DATA_DIR / "top_100_teams"
    transfers_dir = SEASON_DATA_DIR / "top_100_transfers"
    if not overall_path.exists():
        raise FileNotFoundError(
            f"Missing {overall_path}; run player_stats.sh first."
        )
    teams_dir.mkdir(parents=True, exist_ok=True)
    transfers_dir.mkdir(parents=True, exist_ok=True)

    league_id="314"
    top_100_ids=top_players(league_id)
    slim_elements_df= pd.read_csv(overall_path)
    print(f"Fetched {len(top_100_ids)} managers from league {league_id}")

    print("Fetching transfer histories for the top 100 managers")
    transfers_df = get_top_100_tansfers(top_100_ids, None, slim_elements_df)

    for week in range(START_GAMEWEEK, END_GAMEWEEK + 1):
        teams_path = teams_dir / f"public-epl-stats-top100-teams-gw-{week}.csv"
        transfers_path = transfers_dir / f"public-epl-stats-top100-transfers_gw{week}.csv"
        if teams_path.exists() and transfers_path.exists():
            print(f"{week} already complete; skipping")
            continue

        print(week)
        team_df_combined=get_top_100_teams(top_100_ids,week,slim_elements_df)
        transfers_df["Upload_date"] = date.today()
        team_df_combined["Upload_date"] = date.today()
        team_df_combined.active_chip.replace({"wildcard":"Wild Card","freehit":"Free Hit","bboost":"Bench Boost"},inplace=True)
        team_df_combined["active_chip"]=team_df_combined["active_chip"].fillna("No Chip")
        team_df_combined=team_df_combined.rename({"position":"position_selected"},axis=1)
        team_df_combined["event"]=week

        team_df_combined.to_csv(teams_path, index=False)
        transfers_df[transfers_df["event"]==week].to_csv(
            transfers_path, index=False
        )
        print("saved")
        
