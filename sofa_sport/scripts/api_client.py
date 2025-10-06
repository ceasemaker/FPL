"""
SofaSport API Client

Handles all API calls to SofaSport API with proper error handling and rate limiting.
"""
import os
import requests
import time
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SofaSportClient:
    """Client for interacting with SofaSport API."""
    
    def __init__(self):
        self.api_key = os.getenv('SOFASPORT_API_KEY')
        self.api_host = os.getenv('SOFASPORT_API_HOST')
        self.season_id = os.getenv('SEASON_ID', '76986')
        self.tournament_id = os.getenv('UNIQUE_TOURNAMENT_ID', '17')
        
        if not self.api_key or not self.api_host:
            raise ValueError("SOFASPORT_API_KEY and SOFASPORT_API_HOST must be set in .env file")
        
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }
        self.base_url = f"https://{self.api_host}/v1"
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request with error handling."""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {endpoint}: {e}")
            return {}
    
    def get_teams_statistics(self) -> Dict[str, Any]:
        """Get all Premier League teams for the season."""
        endpoint = "seasons/teams-statistics/result"
        params = {
            "seasons_id": self.season_id,
            "seasons_statistics_type": "overall",
            "unique_tournament_id": self.tournament_id
        }
        return self._make_request(endpoint, params)
    
    def get_team_players(self, team_id: str) -> Dict[str, Any]:
        """Get player statistics for a specific team."""
        endpoint = "teams/player-statistics/result"
        params = {
            "season_id": self.season_id,
            "team_id": team_id,
            "unique_tournament_id": self.tournament_id,
            "player_stat_type": "overall"
        }
        time.sleep(0.5)  # Rate limiting
        return self._make_request(endpoint, params)
    
    def get_team_squad(self, team_id: str) -> Dict[str, Any]:
        """Get complete squad list for a specific team."""
        endpoint = "teams/players"
        params = {"team_id": team_id}
        time.sleep(0.5)  # Rate limiting
        return self._make_request(endpoint, params)
    
    def get_fixtures(self, course: str = "last", page: int = 0) -> Dict[str, Any]:
        """
        Get fixtures for the season.
        
        Args:
            course: "last" for past games, "next" for future games
            page: Page number for pagination
        """
        endpoint = "seasons/events"
        params = {
            "seasons_id": self.season_id,
            "unique_tournament_id": self.tournament_id,
            "course_events": course,
            "page": str(page)
        }
        return self._make_request(endpoint, params)
    
    def get_all_fixtures(self, course: str = "last") -> List[Dict[str, Any]]:
        """Get all fixtures with pagination."""
        all_events = []
        page = 0
        
        while True:
            response = self.get_fixtures(course, page)
            
            if not response or 'data' not in response:
                break
            
            events = response['data'].get('events', [])
            all_events.extend(events)
            
            has_next = response['data'].get('hasNextPage', False)
            if not has_next:
                break
            
            page += 1
            time.sleep(0.5)  # Rate limiting
        
        return all_events
    
    def get_event_lineups(self, event_id: str) -> Dict[str, Any]:
        """Get lineups and player stats for a specific event."""
        endpoint = "events/lineups"
        params = {"event_id": event_id}
        time.sleep(0.5)  # Rate limiting
        return self._make_request(endpoint, params)
    
    def get_player_heatmap(self, player_id: str, event_id: str) -> Dict[str, Any]:
        """Get heatmap data for a player in a specific event."""
        endpoint = "events/player-heatmap"
        params = {
            "player_id": player_id,
            "event_id": event_id
        }
        time.sleep(0.5)  # Rate limiting
        return self._make_request(endpoint, params)
    
    def get_player_season_statistics(self, player_id: str, season_id: Optional[str] = None, 
                                     unique_tournament_id: Optional[str] = None, 
                                     player_stat_type: str = "overall") -> Dict[str, Any]:
        """
        Get aggregated season statistics for a specific player.
        
        Args:
            player_id: SofaSport player ID
            season_id: Season ID (default: uses client's season_id)
            unique_tournament_id: Tournament ID (default: uses client's tournament_id)
            player_stat_type: Type of stats (default: "overall")
            
        Returns:
            dict with season-aggregated statistics
        """
        endpoint = "players/statistics/result"
        params = {
            "seasons_id": season_id or self.season_id,
            "player_stat_type": player_stat_type,
            "player_id": player_id,
            "unique_tournament_id": unique_tournament_id or self.tournament_id
        }
        time.sleep(0.5)  # Rate limiting
        return self._make_request(endpoint, params)
    
    def get_player_attribute_overviews(self, player_id: str) -> Dict[str, Any]:
        """
        Get player attribute ratings for radar chart visualization.
        
        Returns attributes like attacking, technical, tactical, defending, creativity.
        Data includes both current season (yearShift=0) and historical averages.
        
        Args:
            player_id: SofaSport player ID
            
        Returns:
            dict with attribute overviews and averageAttributeOverviews
        """
        endpoint = "players/attribute-overviews"
        params = {"player_id": player_id}
        time.sleep(0.5)  # Rate limiting
        return self._make_request(endpoint, params)


if __name__ == "__main__":
    # Test the client
    client = SofaSportClient()
    print("✅ SofaSport Client initialized successfully")
    print(f"Season ID: {client.season_id}")
    print(f"Tournament ID: {client.tournament_id}")

