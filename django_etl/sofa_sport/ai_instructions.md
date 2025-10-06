
Hi AI, here's a list of instructions

all mapping files shall be in json format, if you think otherwise please justify your thinking. 

the api key shall be read from a .env file please so design the code that way.

Please start off by attacking the first 2 tasks mapping. When we save new table into the db, it's important we use the exisiting team id's and exisiting player id's with fk constraints. if you want to also store the sofasport id's for later debugging thats also fine. 

Once the mappings are done, we can move on to building out the tables. and the rest of the tasks


# List of all premier league teams for this season 25/26 for various stats, but we will only be using it to get the team id's for the season

An example of getting the team id for 1 team is 
obj['data']['avgRating'][0]['team']['id']
and team name 
obj['data']['avgRating'][0]['team']['name']

This team name will either be fuzzy matched or you can print them out and match them as an AI, so we create a mapping file to our exisiting teams from the FPL data source. This will help us identify the correct teams in future. And it will help use when we are looking at player stats and attributing the right player stats to the right player.


import requests

url = "https://sofasport.p.rapidapi.com/v1/seasons/teams-statistics/result"

querystring = {"seasons_id":"76986","seasons_statistics_type":"overall","unique_tournament_id":"17"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())


## From the above you will get the list of team id's and we already have the season ID, now the next step is to get the list of players using the next api call. Please now use this to map each and every single player, using the methods I explained above. I want it in a json format as well so that it's just a mapping dict that we can pull from

import requests

url = "https://sofasport.p.rapidapi.com/v1/teams/players"

querystring = {"team_id":"41"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())


# List of fixtures
To start off we will only be looking at past games as the main purpose of this is just attribute certain stats to a player for the right game. You can store this mapping in a file as well because I think it will be faster than reading from a db unless you think otherwise

-  "course_events":"last" = past games
-  "course_events":"next"= future events

"unique_tournament_id":"17" Prem

the json dict top structure is data->['events','hasNextPage']
loop until hasNextPage is False

all the events are in the 'events' list and the event id we use looks is under obj['data']['events'][0]['id'] given we save the initial request repsonce in obj 

import requests

url = "https://sofasport.p.rapidapi.com/v1/seasons/events"

querystring = {"seasons_id":"76986","unique_tournament_id":"17","course_events":"last","page":"0"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())


# Lineups  (This also contains player stats) for that game, therefore we will collect all all the player stats per game, I want this to be in its own table (One table for line ups and one table for sofasport player stats) Please leave allowance for use to classify if an action is defensive/ attacking..etc basically have a column for category which is null by default, and have a colum for display_stats incase we need to hide certain stats. 

import requests

url = "https://sofasport.p.rapidapi.com/v1/events/lineups"

querystring = {"event_id":"14025211"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())

# Player Heat Map

This is very important and I want these coordinates stored in a its own table.

import requests

url = "https://sofasport.p.rapidapi.com/v1/events/player-heatmap"

querystring = {"player_id":"934354","event_id":"14025211"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())





