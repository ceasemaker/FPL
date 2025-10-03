import pandas as pd
import numpy as np
import requests
from dateutil import parser 
from datetime import datetime
import os
def get_team_names():
    url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    r = requests.get(url)
    json = r.json()
    teams_df = pd.DataFrame(json['teams'])
    return teams_df
def get_fixtures():
    url = 'https://fantasy.premierleague.com/api/fixtures/'
    r = requests.get(url)
    json = r.json()
    fixtures_df = pd.DataFrame(json)
    #map team names to team id
    teams_df = get_team_names()
    fixtures_df["HomeTeam"]=fixtures_df["team_h"].map(teams_df.set_index("id")["name"])
    fixtures_df["AwayTeam"]=fixtures_df["team_a"].map(teams_df.set_index("id")["name"])
    # convert date to to date time with uct +01:00
    fixtures_df["kickoff_time"]=fixtures_df["kickoff_time"].str.replace("Z","+01:00")
    # fixtures_df["kickoff_time"]=fixtures_df["kickoff_time"].apply(parser.parse)
    return fixtures_df
def fixture_diff_calc(df):
    #this fucntion retrieves the fdr for a teams next 5 games
    df_return= pd.DataFrame()
    fdr_dict={}
    teams = df["HomeTeam"].unique()
    for event in range(1,int(df["event"].max())):
        fdr_dict[event]={}
        
        for team in teams:
            fdr_dict[event][team]={}
            next_5_diff_rating=[]
            for week in range(event,event+5):
                df_week = df[df["event"]==week]
                df_week_team = df_week[(df_week["HomeTeam"]==team)|(df_week["AwayTeam"]==team)].reset_index(drop=True)
                if df_week_team.shape[0]==1:
                    #check if team is home or away
                    if df_week_team.iloc[0]["HomeTeam"]==team:
                        rating = df_week_team.iloc[0]["team_h_difficulty"]
                        # check if rating is not None  
                        if rating!=None:
                            next_5_diff_rating.append(rating)
                    else:
                        rating = df_week_team.iloc[0]["team_a_difficulty"]
                        if rating!=None:
                            next_5_diff_rating.append(rating)

           
            fdr_dict[event][team]["fdr_5_mean"]=np.mean(next_5_diff_rating)
            #convert next_5_diff_rating to strings
            next_5_diff_rating = [str(x) for x in next_5_diff_rating]
            fdr_dict[event][team]["fdr_5_list"]=next_5_diff_rating
        df_return_week = pd.DataFrame.from_dict(fdr_dict[event], orient='index')
        # rename index to "Team Name"
        df_return_week.index.name = "Team_Name"
        #change index to column
        df_return_week.reset_index(inplace=True)
        df_return_week["Team_Name_logo"] = df_return_week["Team_Name"].str.replace(" ", "+")
        df_return_week["event"]=event
        df_return = pd.concat([df_return,df_return_week])
    return df_return
def gw_diff(list:list,col:int):
    try: 
        list[col] 
        return list[col]
    except:
        return None
def game_schedule(df):
    df.drop(["id"],axis=1,inplace=True)
    home_df =df.copy()
    away_df =df.copy()
    away_df_rename={
        "code":"index",
        'AwayTeam':'Team_Name',
        'team_a_score':'Team_Score',
        'HomeTeam':'Opponent',
        'team_h_score':'Opponent_Score',
        'team_h_difficulty':'Opponent_Difficulty',
        'team_a_difficulty':'Team_Difficulty',
        'HomeTeam_logo':'Oppenent_logo',
        'AwayTeam_logo':'Team_Name_logo'}
    home_df_rename={
        "code":"index",
        'HomeTeam':'Team_Name',
        'team_h_score':'Team_Score',
        'AwayTeam':'Opponent',
        'team_a_score':'Opponent_Score',
        'team_a_difficulty':'Opponent_Difficulty',
        'team_h_difficulty':'Team_Difficulty',
        'HomeTeam_logo':'Team_Name_logo',
        'AwayTeam_logo':'Oppenent_logo'} 
    
    away_df.rename(columns=away_df_rename,inplace=True)
    away_df["index"]=away_df["index"]*12345
    away_df["Location"]="Away"
    home_df.rename(columns=home_df_rename,inplace=True)
    home_df["index"]=home_df["index"]*12345*10
    home_df["Location"]="Home"
    df = pd.concat([away_df,home_df])
    return df
def check_if_finished(df_check,df):
    df_finished=df[df["finished"]==True]
    df_finished.drop_duplicates(subset=["event","finished"],inplace=True)
    df_finished=df_finished[["event","finished"]]
    df_finished.reset_index(drop=True,inplace=True)
    #map the finished column to the df_check column on the event column
    df_check["finished"]=df_check["event"].map(df_finished.set_index("event")["finished"])
    # replace null values in the finished column with False
    df_check["finished"].fillna(False,inplace=True)

    return df_check



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



if __name__ == "__main__":
    save_path = "../fpl_data/2024/fixtures/"
    save_path_fdr = "../fpl_data/2024/fixture_difficulty/"
    save_path_fdr_expanded = "../fpl_data/2024/fixtures_expanded/"
    ensure_folder_exists(save_path)
    ensure_folder_exists(save_path_fdr)
    ensure_folder_exists(save_path_fdr_expanded)

    schema_path="../fpl_data/schema/fpl_fixtures_schema.csv"
    fdr_schema_path="../fpl_data/schema/fpl_fdr_schema.csv"
    fdr_expanded_schema_path="../fpl_data/schema/fpl_fdr_expanded_schema.csv"

    df = get_fixtures()
    df.drop(columns=["stats","provisional_start_time","pulse_id"],inplace=True)
    # replace all spaces with a "+" in the team names
    df["HomeTeam_logo"] = df["HomeTeam"].str.replace(" ", "+")
    df["AwayTeam_logo"] = df["AwayTeam"].str.replace(" ", "+")
   
    #append todays date and time down to the minute
    today_date=datetime.now().date()
    today_time=datetime.now().time()    
    save_path = save_path + str(today_date) + "_" + str(today_time).replace(":","") + ".csv"
    print("saving to {}".format(save_path))
    df.to_csv(save_path,index=False)
    df_schedule=df.copy()
    df["kickoff_time"]=df["kickoff_time"]+"string_maker"
    df.to_csv(schema_path,index=False)

    save_path_fdr_expanded=save_path_fdr_expanded + str(today_date) + "_" + str(today_time).replace(":","") + ".csv"
    df_schedule=game_schedule(df_schedule)
    df_schedule.to_csv(save_path_fdr_expanded,index=False)
    df_schedule["kickoff_time"]=df_schedule["kickoff_time"]+"string_maker"
    df_schedule.to_csv(fdr_expanded_schema_path,index=False)

    df_return = fixture_diff_calc(df)
    
    save_path_fdr = save_path_fdr + str(today_date) + "_" + str(today_time).replace(":","") + ".csv"
    print("saving to {}".format(save_path_fdr))
    #add an ID column
    df_return.reset_index(drop=True,inplace=True)
    df_return["index"]=df_return.index+1
    df_return["+1"]=df_return["fdr_5_list"].apply(gw_diff,col=0)
    df_return["+2"]=df_return["fdr_5_list"].apply(gw_diff,col=1)
    df_return["+3"]=df_return["fdr_5_list"].apply(gw_diff,col=2)
    df_return["+4"]=df_return["fdr_5_list"].apply(gw_diff,col=3)
    df_return["+5"]=df_return["fdr_5_list"].apply(gw_diff,col=4)
    df_return=check_if_finished( df_return,df)
    df_return.to_csv(fdr_schema_path,index=False)
    df_return.to_csv(save_path_fdr,index=False)

