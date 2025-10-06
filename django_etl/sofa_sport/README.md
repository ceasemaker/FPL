# SofaSport Integration

This module integrates SofaSport API data with the existing FPL database to provide enhanced player statistics, heatmaps, and lineups.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   - Edit `.env` file with your SofaSport API key
   - Verify database connection settings

## Usage

### Step 1: Build Team Mapping

Maps SofaSport teams to existing FPL teams:

```bash
cd scripts
python build_team_mapping.py
```

This creates `mappings/team_mapping.json` with the team ID mappings.

### Step 2: Build Player Mapping

Maps SofaSport players to existing FPL players:

```bash
python build_player_mapping.py
```

This creates `mappings/player_mapping.json` with player ID mappings.

**Note:** You must run team mapping first as player mapping depends on it.

### Step 3: Run Complete ETL (Coming Soon)

```bash
python run_sofasport_etl.py
```

## Project Structure

```
sofa_sport/
├── .env                      # API keys and configuration
├── requirements.txt          # Python dependencies
├── ai_instructions.md        # Development instructions
├── README.md                # This file
├── mappings/                # JSON mapping files
│   ├── team_mapping.json
│   ├── player_mapping.json
│   └── fixture_mapping.json
└── scripts/                 # ETL scripts
    ├── api_client.py        # SofaSport API wrapper
    ├── build_team_mapping.py
    ├── build_player_mapping.py
    └── run_sofasport_etl.py
```

## API Endpoints Used

1. **Teams Statistics** - Get all Premier League teams
2. **Player Statistics** - Get players per team
3. **Season Events** - Get fixtures (past/future)
4. **Event Lineups** - Get lineup and player stats per game
5. **Player Heatmap** - Get heatmap coordinates per player per game

## Database Tables (To Be Created)

- `sofasport_fixtures` - Fixture mappings
- `sofasport_lineups` - Player lineups per game
- `sofasport_player_stats` - Enhanced player statistics per game
- `sofasport_heatmaps` - Player heatmap coordinates

All tables will have foreign key constraints to existing FPL teams and players.

## Rate Limiting

The API client includes built-in rate limiting (0.5s between requests) to avoid hitting API limits.
