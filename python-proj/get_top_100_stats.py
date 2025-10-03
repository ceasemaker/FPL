import warnings

import pandas as pd
import numpy as np
import requests
import glob
import sys
from datetime import datetime
import warnings
import os
warnings.filterwarnings("ignore")

def top_players(league_id="314"):
    top_ids = []
    
    url="https://fantasy.premierleague.com/api/leagues-classic/{}/standings/?page_standings={}"
    for page in range(1,3):
        print(url.format(league_id,page))
        r = requests.get(url.format(league_id,page))
        json = r.json()
        for obj in json["standings"]["results"]:
            flp_id = obj["entry"]
            top_ids.append(flp_id)
            
            
    return top_ids


def get_top_100_tansfers(top_100_ids,week,df):
    transfers_df = pd.DataFrame()
    for user in top_100_ids:
        url ="https://fantasy.premierleague.com/api/entry/{}/transfers"
        api = url.format(user)

        r = requests.get(api)
        json = r.json()
        
        for obj in json:
            df_row=pd.DataFrame(pd.Series(obj)).T
            df_row["web_name_in"]=df_row.element_in.map(df.set_index("id")["web_name"])
            df_row["position_name_in"]=df_row.element_in.map(df.set_index("id")["position"])
            df_row["web_name_out"]=df_row.element_out.map(df.set_index("id")["web_name"])
            df_row["position_name_out"]=df_row.element_out.map(df.set_index("id")["position"])
            transfers_df= pd.concat([transfers_df,df_row],ignore_index=True)#transfers_df.append(df_row)
            
    return transfers_df


def get_top_100_teams(top_100_ids,week,df):
    warnings.filterwarnings('ignore')
    team_df_combined=pd.DataFrame()
    url="https://fantasy.premierleague.com/api/entry/{}/event/{}/picks/"
    for id_ in top_100_ids:
        api = url.format(id_,week)
        r = requests.get(api)
        json = r.json()
        team_df=pd.DataFrame.from_dict(json["picks"])
        team_df["web_name"]=team_df.element.map(df.set_index("id")["web_name"])
        team_df["position_name"]=team_df.element.map(df.set_index("id")["position"])
        team_df["active_chip"]=json["active_chip"]
        team_df_combined= pd.concat([team_df_combined,team_df],ignore_index=True)#team_df_combined.append(team_df)
    return team_df_combined
def ensure_folder_exists(folder_path):
    """
    Checks if a folder exists and creates it if it does not.

    Parameters:
        folder_path (str): The path of the folder to check or create.

    Returns:
        bool: True if the folder was created, False if it already existed.
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Folder created: {folder_path}")
        return True
    else:
        print(f"Folder already exists: {folder_path}")
        return False
if "__main__"==__name__:
    # ensure_folder_exists("../fpl_data/2025/overall_player_data/")
    # ensure_folder_exists("../fpl_data/2025/top_100_teams/")
    # ensure_folder_exists("../fpl_data/2025/top_100_transfers/")
    for week in range(22,39):
        print(week)
        league_id="314"
        today_date=datetime.now().date()
        # week=37
        top_100_ids=top_players(league_id)
        slim_elements_df= pd.read_csv("../fpl_data/2025/overall_player_data/overall_payer_data.csv")
        

        

        transfers_df=get_top_100_tansfers(top_100_ids,week,slim_elements_df)
        team_df_combined=get_top_100_teams(top_100_ids,week,slim_elements_df)
        transfers_df["Upload_date"] =today_date
        team_df_combined["Upload_date"]=today_date
        team_df_combined.active_chip.replace({"wildcard":"Wild Card","freehit":"Free Hit","bboost":"Bench Boost"},inplace=True)
        team_df_combined["active_chip"]=team_df_combined["active_chip"].fillna("No Chip")
        team_df_combined=team_df_combined.rename({"position":"position_selected"},axis=1)
        team_df_combined["event"]=week

        team_df_combined.to_csv(f"../fpl_data/2025/top_100_teams/public-epl-stats-top100-teams-gw-{week}.csv",index=False)
        transfers_df[transfers_df["event"]==week].to_csv(f"../fpl_data/2025/top_100_transfers/public-epl-stats-top100-transfers_gw{week}.csv",index=False)
        print("saved")
        