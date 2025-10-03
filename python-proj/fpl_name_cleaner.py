import pandas as pd
import numpy as np
import fuzzywuzzy
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
import time
import warnings
warnings.filterwarnings('ignore')
#import Levenshtein as fuzzy_match
def rename_leagues(df):
    renaming_dict={"E0": "Premier League",
                     "E1": "Championship",
                        "E2": "League One",
                        "E3": "League Two",
                        "EC": "Conference"}
    df["Div"]=df["Div"].map(renaming_dict)
    return df
def remove_team_not_renamed(df,renaming_dict):
    df=df[df["HomeTeam"].isin(renaming_dict.keys())]
    df=df[df["AwayTeam"].isin(renaming_dict.keys())]
    return df

def remove_team_not_renamed(df,renaming_dict):
    print("removing teams not in current season")
    df=df[df["HomeTeam"].isin(renaming_dict.keys())]
    df=df[df["AwayTeam"].isin(renaming_dict.keys())]
    return df

def rename_teams(df):
    df["HomeTeam"]=df["HomeTeam"].map(renaming_dict)
    df["AwayTeam"]=df["AwayTeam"].map(renaming_dict)
    return df
def get_kickoff_time(df):
    df["kickoff_time"]=df["Date"].str.replace("/","-") +"Z"+df["Time"] + ":00+01:00"
    return df

def get_season_data(num_seasons):
    df_all = pd.DataFrame()
    start=24
    end=25
    for count, _ in enumerate(range(num_seasons)):

        print("Reading the {}{} season: {}/{}".format(start,end,count+1,num_seasons))
        for j in range(0,2):
            if len(str(start))==1:
                start="0"+str(start)
            if len(str(end))==1:
                end="0"+str(end)
            url="https://www.football-data.co.uk/mmz4281/{}{}/E{}.csv".format(start,end,j)
            df = pd.read_csv(url)
            #save df to csv
            df.to_csv(f"../../../data/fpl_data/past_games_raw/E{j}-{start}{end}.csv",index=False)
            df_all= pd.concat([df_all,df])
            time.sleep(2)
        start=int(start)-1
        end=int(end)-1
        
        
    return df_all

    

df_past_games=get_season_data(1)
df_names = pd.read_csv("../fpl_data/schema/fpl_fixtures_schema.csv")
team_names_to_check=df_past_games["HomeTeam"].unique()
true_team_names=df_names["HomeTeam"].unique()

#using fuzzy matching to find the closest match to the team name as well as the ratio of the match
renaming_dict={"Tottenham":"Spurs"}
for count, team in  enumerate(true_team_names,start=1):
    closest_match=process.extractOne(team,team_names_to_check)
    if closest_match[1] > 80:
        renaming_dict[closest_match[0]]=team
        if closest_match[1] !=100:
            print("{}:{}".format(team,closest_match))

    else:
        print("{} not good match found-> closets match is {} ".format(team,closest_match))
        print("This does not affect the code if this team in not in the current season")
        continue

df_training=get_kickoff_time(df_past_games)
df_training=rename_leagues(df_training)
df_training=rename_teams(df_training)
df_training=remove_team_not_renamed(df_training,renaming_dict)
df_training.to_csv("../fpl_data/training_data/fixtures_training.csv",index=False)

