import pandas as pd
import numpy as np
import requests
import glob
import sys
from datetime import datetime

def overall_data():
    #Accessing the premier league API
    url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    r = requests.get(url)
    json = r.json()
    elements_df = pd.DataFrame(json['elements'])
    elements_types_df = pd.DataFrame(json['element_types'])
    teams_df = pd.DataFrame(json['teams'])
    slim_elements_df= elements_df.copy()
    slim_elements_df['position'] = slim_elements_df.element_type.map(elements_types_df.set_index('id').singular_name)
    slim_elements_df.loc[:,'team'] = slim_elements_df.team.map(teams_df.set_index('id').name)
    return slim_elements_df

def get_week_data(game_week,slim_elements_df):
    print("reading game week {}".format(game_week))
    id_details=slim_elements_df[["id","web_name","team","position","first_name","second_name"]]
    url = "https://fantasy.premierleague.com/api/event/{}/live".format(game_week)
    r = requests.get(url)
    json = r.json()
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
    slim_elements_df=overall_data()
    for week in range(30,39):
        today_date=datetime.now().date()
        slim_elements_df.to_csv(f"../fpl_data/2025/overall_player_data/overall_payer_data.csv",index=False)
        save_path_player_data=f"../fpl_data/2025/player_data/public-epl-stats-players-week-{week}.csv"
        week_df=get_week_data(week,slim_elements_df)
        week_df.set_index("id").to_csv(save_path_player_data)
        print("saved")





