import pandas as pd
import numpy as np
import requests
import time
from pathlib import Path


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

def overall_data():
    #Accessing the premier league API
    url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    json = get_json(url)
    elements_df = pd.DataFrame(json['elements'])
    elements_types_df = pd.DataFrame(json['element_types'])
    teams_df = pd.DataFrame(json['teams'])
    slim_elements_df= elements_df.copy()
    slim_elements_df['position'] = slim_elements_df.element_type.map(elements_types_df.set_index('id').singular_name)
    slim_elements_df['team'] = slim_elements_df.team.map(teams_df.set_index('id').name)
    return slim_elements_df

def get_week_data(game_week,slim_elements_df):
    print("reading game week {}".format(game_week))
    id_details=slim_elements_df[["id","web_name","team","position","first_name","second_name"]]
    url = "https://fantasy.premierleague.com/api/event/{}/live".format(game_week)
    json = get_json(url)
    elements_df_2 = pd.DataFrame(json['elements'])
    att_to_append=["web_name","team","position","first_name","second_name"]
    for att in att_to_append:
        elements_df_2[att]=elements_df_2.id.map(id_details.set_index("id")[att])
        
    json_file= elements_df_2["stats"]
    Stats_df=pd.DataFrame(list(json_file))
    week_df=pd.merge(elements_df_2,Stats_df,left_index=True,right_index=True)
    week_df["event"]=game_week
    return week_df.drop(columns="explain")

if "__main__"==__name__:
    overall_dir = SEASON_DATA_DIR / "overall_player_data"
    player_dir = SEASON_DATA_DIR / "player_data"
    overall_dir.mkdir(parents=True, exist_ok=True)
    player_dir.mkdir(parents=True, exist_ok=True)

    slim_elements_df=overall_data()
    overall_path = overall_dir / "overall_payer_data.csv"
    slim_elements_df.to_csv(overall_path, index=False)
    print(f"saved {overall_path}")

    for week in range(START_GAMEWEEK, END_GAMEWEEK + 1):
        week_df=get_week_data(week,slim_elements_df)
        save_path_player_data = player_dir / f"public-epl-stats-players-week-{week}.csv"
        week_df.set_index("id").to_csv(save_path_player_data)
        print(f"saved {save_path_player_data}")


