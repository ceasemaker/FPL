# FPL (Fantasy Premier League) API Documentation

This documentation provides details about the endpoints available in the Fantasy Premier League API.

## Endpoints

### 1. General Information
- **Endpoint**: `bootstrap-static/`
- **URL**: `https://fantasy.premierleague.com/api/bootstrap-static/`
- **Description**: Summary of previous game weeks, FPL phases, teams, players, and game settings.

### 2. Fixtures
- **Endpoint**: `fixtures/`
- **URL**: `https://fantasy.premierleague.com/api/fixtures/`
- **Description**: Returns array of fixture objects. Includes statistics for past fixtures and summary info for future fixtures.

### 3. Fixtures by GameWeek
- **Endpoint**: `fixtures/?event={event_id}`
- **URL**: `https://fantasy.premierleague.com/api/fixtures/?event={event_id}`
- **Description**: Returns fixtures for a specific gameweek.

### 4. Player Data
- **Endpoint**: `element-summary/{element_id}/`
- **URL**: `https://fantasy.premierleague.com/api/element-summary/{element_id}/`
- **Description**: Returns detailed data on a football player including current season fixtures and past season summaries.

### 5. Gameweek Data
- **Endpoint**: `event/{event_id}/live/`
- **URL**: `https://fantasy.premierleague.com/api/event/{event_id}/live/`
- **Description**: Returns statistics for all players in FPL for the specified gameweek.

### 6. Manager Summary
- **Endpoint**: `entry/{manager_id}/`
- **URL**: `https://fantasy.premierleague.com/api/entry/{manager_id}/`
- **Description**: Returns summary data for a given manager.

### 7. Manager History
- **Endpoint**: `entry/{manager_id}/history/`
- **URL**: `https://fantasy.premierleague.com/api/entry/{manager_id}/history/`
- **Description**: Returns manager's history including fixture statistics, past seasons, and chip usage.

### 8. Manager Transfers
- **Endpoint**: `entry/{manager_id}/transfers/`
- **URL**: `https://fantasy.premierleague.com/api/entry/{manager_id}/transfers/`
- **Description**: Returns all transfers made by a manager in the current season.

### 9. Current Gameweek Transfers
- **Endpoint**: `entry/{manager_id}/transfers-latest/`
- **URL**: `https://fantasy.premierleague.com/api/entry/{manager_id}/transfers-latest/`
- **Authentication Required**: Yes
- **Description**: Returns transfers for the most recently completed gameweek.

### 10. Classic League Standings
- **Endpoint**: `leagues-classic/{league_id}/standings/`
- **URL**: `https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/`
- **Optional Parameters**: `page_new_entries`, `page_standings`, `phase`

### 11. Head-to-Head League Standings
- **Endpoint**: `leagues-h2h-matches/league/{league_id}/`
- **URL**: `https://fantasy.premierleague.com/api/leagues-h2h-matches/league/{league_id}/`

### 12. Manager's Team
- **Endpoint**: `my-team/{manager_id}/`
- **URL**: `https://fantasy.premierleague.com/api/my-team/{manager_id}/`
- **Authentication Required**: Yes
- **Description**: Returns current team, chip usage, and latest transfers.

### 13. Manager's Team by Gameweek
- **Endpoint**: `entry/{manager_id}/event/{event_id}/picks/`
- **URL**: `https://fantasy.premierleague.com/api/entry/{manager_id}/event/{event_id}/picks/`
- **Description**: Returns team picks for a specific gameweek.

### 14. Event Status
- **Endpoint**: `event-status/`
- **URL**: `https://fantasy.premierleague.com/api/event-status/`
- **Description**: Returns status of bonus points and league updates for current gameweek.

### 15. Dream Team
- **Endpoint**: `dream-team/{event_id}/`
- **URL**: `https://fantasy.premierleague.com/api/dream-team/{event_id}/`
- **Description**: Returns the dream team for a specific gameweek.

### 16. Set Piece Taker Notes
- **Endpoint**: `team/set-piece-notes/`
- **URL**: `https://fantasy.premierleague.com/api/team/set-piece-notes/`
- **Description**: Returns notes on set piece takers for each team.

### 17. Manager Data
- **Endpoint**: `me/`
- **URL**: `https://fantasy.premierleague.com/api/me/`
- **Authentication Required**: Yes
- **Description**: Returns data about the authenticated manager.

### 18. League Cup Status
- **Endpoint**: `league/{league_id}/cup-status/`
- **URL**: `https://fantasy.premierleague.com/api/league/{league_id}/cup-status/`
- **Description**: Returns cup status for a specific league.

### 19. Most Valuable Teams
- **Endpoint**: `stats/most-valuable-teams/`
- **URL**: `https://fantasy.premierleague.com/api/stats/most-valuable-teams/`
- **Description**: Returns top 5 most valuable teams.

### 20. Best Leagues
- **Endpoint**: `stats/best-leagues/`
- **URL**: `https://fantasy.premierleague.com/api/stats/best-leagues/`
- **Description**: Returns best leagues based on average score of top 5 players.

## Authentication
Several endpoints require authentication. To access these endpoints:
1. Make sure the manager ID matches the authenticated user's ID
2. Follow the authentication instructions from the official FPL API documentation

## Notes
- `{manager_id}`, `{event_id}`, and `{league_id}` are placeholders that need to be replaced with actual IDs when making API requests
- Some endpoints return different data depending on whether the gameweek is past, current, or future
- The API may be rate-limited, so consider implementing appropriate caching strategies
