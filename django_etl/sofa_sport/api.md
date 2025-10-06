# List of api's and what they do in order



## List of all unique competitions (UCL, EUROPA, Premier League, Championship)
This is for if I want to add other competions such as europa league etc

{"category_id":"1465"} EUROPE
{"category_id":"1"} ENGLAND

import requests

url = "https://sofasport.p.rapidapi.com/v1/unique-tournaments"

querystring = {"category_id":"1465"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())





## List of all premier league seasons (season of interest 76986)
- seasons of interests
 - 76953 UCL 25/26
 - 76986 Prem 25/26

{"tournament_id":"1"} PREM
{"unique_tournament_id":"7"} UCL

import requests

url = "https://sofasport.p.rapidapi.com/v1/unique-tournaments/seasons"

querystring = {"unique_tournament_id":"7"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())



# List of fixtures

-  "course_events":"last" = past games
-  "course_events":"next"= future events

"unique_tournament_id":"7" UCL

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



## Individual player stats for an event example is Semenyo

import requests

url = "https://sofasport.p.rapidapi.com/v1/events/player-statistics"

querystring = {"event_id":"14025211","player_id":"934354"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())


# Player Heat Map

import requests

url = "https://sofasport.p.rapidapi.com/v1/events/player-heatmap"

querystring = {"player_id":"934354","event_id":"14025211"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())


## Away and home team form getting into an event

import requests

url = "https://sofasport.p.rapidapi.com/v1/events/form"

querystring = {"event_id":"14025211"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())



# Lineups  (This also contains player stats so it might not be worth hitting the stats api)

import requests

url = "https://sofasport.p.rapidapi.com/v1/events/lineups"

querystring = {"event_id":"14025211"}

headers = {
	"x-rapidapi-key": "3c905ecbe2msh6769374a4f5c167p1a88e8jsnd6befc6c65bd",
	"x-rapidapi-host": "sofasport.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())