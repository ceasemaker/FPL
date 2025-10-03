'''
This is is script that should only be run once or at least only after new tranfers
have been made into the premier league.

It will return a table of all players and a table of all teams. This is for the sole purpose of
getting the player ID's and team ID's for the advanced player stats. 

NOTE NO MEANINGFUL STATS ARE ACTUALLY COLLECTED FROM THIS SCRIPT.
'''
import datetime
import warnings
warnings.filterwarnings('ignore')
url_teams_table="https://api.sofascore.com/api/v1/unique-tournament/17/season/41886/standings/total" # url for all teams in a table
url_players="https://api.sofascore.com/api/v1/team/{}/unique-tournament/17/season/41886/top-players/overall" #for each team to get player IDs
import requests
import pandas as pd
import numpy as np

def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def get_all_teams(url_teams_table):
    r = requests.get(url_teams_table,timeout=10)
    json = r.json()
    teams_json =json["standings"][0]["rows"]

    return teams_json
def get_player_stats(url_players,team_id):
    url_players=url_players.format(team_id)
    r = requests.get(url_players,timeout=10)
    json = r.json()
    player_stats_json =json["topPlayers"]["rating"]
    
    return player_stats_json




def df_maker(list_of_dict):
    df_return = pd.DataFrame()
    for i in range(len(list_of_dict)):
        list_of_dict[i] = flatten(list_of_dict[i])
        df_return = df_return.append(list_of_dict[i], ignore_index=True)
    return df_return



teams_json = get_all_teams(url_teams_table)
save_path="../../../data/fpl_data/advanced_stats/player_keys_2022-23/all_players-{}.csv"
save_path_all_teams="../../../data/fpl_data/advanced_stats/team_keys_2022-23/teams.csv"

players_df = pd.DataFrame()
todays_date = datetime.datetime.today().strftime('%Y-%m-%d')

print("Collecting Data For All Premier leaugue Teams")
for team in teams_json:
    id= team["team"]["id"]
    team_name=team["team"]["name"]
    print(team_name)
    team_slug=team["team"]["slug"]
    df_t=get_player_stats(url_players,id)
    df_t= df_maker(df_t)
    df_t["team_id"]=id
    df_t["team_name"]=team_name
    df_t["team_slug"]=team_slug
    players_df = players_df.append(df_t, ignore_index=True)
players_df.to_csv(save_path.format(todays_date),index=False)
teams_df = df_maker(teams_json)
teams_df.to_csv(save_path_all_teams,index=False)
print("Data Collecting")
    