# SofaSport Integration - Complete Documentation

## Overview

This integration enriches FPL Pulse with detailed player statistics, match lineups, and heatmap visualizations from the SofaSport API. It provides per-match performance metrics and season-level aggregates to enhance player analysis and team selection insights.

## Architecture

### Data Flow
```
SofaSport API → ETL Scripts → PostgreSQL Database → Django API → Frontend
```

### Components
1. **API Client** (`api_client.py`) - Wrapper for SofaSport API with rate limiting
2. **Mapping Files** (JSON) - Bridge between FPL and SofaSport player/team IDs
3. **Django Models** - Database schema for fixtures, lineups, stats, heatmaps
4. **ETL Scripts** - Data collection and transformation pipelines

---

## Database Schema

### Tables Created

#### 1. `sofasport_fixtures` (25 columns)
**Purpose:** Links SofaSport events to FPL fixtures with match metadata

**Key Fields:**
- `sofasport_event_id` (BigInt) - SofaSport event ID
- `fixture_id` (FK) - Link to FPL fixture
- `home_team_id`, `away_team_id` (FK) - Links to FPL teams
- `sofasport_home_team_id`, `sofasport_away_team_id` (BigInt) - SofaSport team IDs
- `home_score_current`, `away_score_current` - Final scores
- `home_score_period1`, `away_score_period1` - Half-time scores
- `home_score_period2`, `away_score_period2` - Second half scores
- `home_formation`, `away_formation` - Team formations (e.g., "4-3-3")
- `match_status` - Status type (finished, inprogress, notstarted)
- `kickoff_time` - Match kickoff datetime
- `has_xg`, `has_player_statistics`, `has_heatmap` - Data availability flags
- `lineups_confirmed` - Whether lineups are confirmed
- `raw_data` (JSON) - Complete API response

**Indexes:** fixture, home_team, away_team, match_status

**Records:** 70 fixtures (GW1-GW7)

#### 2. `sofasport_lineups` (15 columns)
**Purpose:** Player lineup data with embedded per-match statistics

**Key Fields:**
- `sofasport_player_id` (BigInt) - SofaSport player ID
- `athlete_id` (FK) - Link to FPL athlete
- `fixture_id` (FK) - Link to SofaSport fixture
- `team_id` (FK) - Link to FPL team
- `sofasport_team_id` (BigInt) - SofaSport team ID
- `position` - Player position (G, D, M, F)
- `shirt_number` - Jersey number
- `substitute` (Boolean) - Whether player started on bench
- `minutes_played` - Minutes played (extracted from statistics)
- `statistics` (JSON) - **Complete per-match statistics (20-60 fields)**
  - Rating, passes (accurate/total), shots, goals, assists
  - Duels, tackles, interceptions, clearances
  - Touches, dribbles, fouls, cards
  - xG, xA, and 40+ more metrics
- `player_name`, `player_slug` - Player identification

**Indexes:** athlete, fixture, team, sofasport_player_id

**Unique Constraint:** (athlete, fixture)

**Records:** 2,733 lineup entries with full statistics

#### 3. `sofasport_player_season_stats` (45 columns)
**Purpose:** Aggregated season-level statistics for frontend display

**Key Fields:**
- `sofasport_player_id` (BigInt) - SofaSport player ID
- `athlete_id` (FK) - Link to FPL athlete
- `team_id` (FK) - Link to FPL team
- `season_id` - Season identifier (e.g., "76986" for 2025/26)
- **Control Fields:**
  - `category` - Stat category (attacking, defensive, passing, goalkeeper)
  - `display_stats` (Boolean) - Whether to show in UI

**Aggregated Statistics (all with 2 decimal place max):**
- **General:** rating, total_rating, count_rating, minutes_played, appearances
- **Attacking:** goals, assists, expected_assists, big_chances_created, big_chances_missed, total_shots, shots_on_target
- **Passing:** accurate_passes, total_passes, accurate_passes_percentage, key_passes, accurate_long_balls, accurate_long_balls_percentage
- **Defensive:** tackles, interceptions, clearances
- **Duels:** total_duels_won, total_duels_won_percentage, aerial_duels_won, ground_duels_won
- **Discipline:** yellow_cards, red_cards, fouls, was_fouled
- **Goalkeeper:** saves, saves_percentage, clean_sheets, goals_conceded
- `statistics` (JSON) - Complete season stats (60+ fields)

**Indexes:** athlete, team, season_id, sofasport_player_id, rating (desc), goals (desc), assists (desc)

**Unique Constraint:** (athlete, season_id)

**Records:** ~500-550 (currently being populated)

#### 4. `sofasport_heatmaps` (9 columns)
**Purpose:** Player movement coordinates for pitch heatmap visualization

**Key Fields:**
- `sofasport_player_id` (BigInt) - SofaSport player ID
- `athlete_id` (FK) - Link to FPL athlete
- `fixture_id` (FK) - Link to SofaSport fixture
- `lineup_id` (FK OneToOne) - Link to lineup entry
- `coordinates` (JSON) - Array of {x, y} coordinate objects
  - Each point represents a position on the pitch (0-100 grid)
  - Example: `[{x: 45, y: 50}, {x: 48, y: 52}, ...]`
- `point_count` - Number of coordinate points

**Indexes:** athlete, fixture, sofasport_player_id

**Unique Constraint:** (athlete, fixture)

**Records:** ~1,600 heatmaps (60% of lineups - selective collection based on criteria)

#### 5. `sofasport_player_attributes` (13 columns)
**Purpose:** Player attribute ratings for radar chart visualization

**Key Fields:**
- `sofasport_player_id` (BigInt) - SofaSport player ID
- `athlete_id` (FK) - Link to FPL athlete
- **Attribute ratings (0-100 scale):**
  - `attacking` - Attacking ability
  - `technical` - Technical skills  
  - `tactical` - Tactical awareness
  - `defending` - Defensive ability
  - `creativity` - Creativity/playmaking
- `position` - Position for these attributes (F, M, D, G)
- `year_shift` - 0 = current season, negative = previous seasons
- `is_average` (Boolean) - True if career average, False if season-specific
- `raw_data` (JSON) - Complete API response

**Indexes:** athlete, sofasport_player_id, year_shift, position

**Unique Constraint:** (athlete, year_shift, is_average)

**Records:** ~500-550 players (mostly career averages, some with current season data)

**Data Priority:**
1. Current season attributes (yearShift=0) from `attributeOverviews`
2. Career average attributes from `averageAttributeOverviews`

**Note:** Most players return career averages. Younger players or those without sufficient data may have 404 responses (gracefully skipped).

---

## Mapping Files

### Location
`/app/sofa_sport/mappings/`

### 1. `team_mapping.json` (20 teams)
**Structure:**
```json
{
  "sofasport_id": {
    "sofasport_id": 42,
    "sofasport_name": "Arsenal",
    "fpl_id": 1,
    "fpl_name": "Arsenal",
    "match_score": 100
  }
}
```

**Coverage:** 20/20 Premier League teams (100%)

### 2. `player_mapping.json` (552 players)
**Structure:**
```json
{
  "sofasport_id": {
    "sofasport_id": 800717,
    "sofasport_name": "Bukayo Saka",
    "fpl_id": 123,
    "fpl_web_name": "Saka",
    "fpl_full_name": "Bukayo Saka",
    "fpl_team_id": 1,
    "sofasport_team_id": 42,
    "match_score": 95
  }
}
```

**Coverage:** 552/743 FPL players (74.3%)
- Includes all high-value players
- 11 unmapped players with only 30 total FPL points
- Manual additions: Bernardo Silva, João Gomes, Florentino Luís, Andrey Santos, Ben Doak, José Sá

### 3. `players_to_review.md`
Documentation of 11 unmapped low-value players for future review

### 4. `unmatched_fixtures.json`
Log of any SofaSport fixtures that couldn't be matched to FPL fixtures (currently empty)

---

## API Client

### File: `api_client.py`

### Configuration
- **Base URL:** `https://sofasport.p.rapidapi.com/v1`
- **Season ID:** 76986 (Premier League 2025/26)
- **Tournament ID:** 17 (Premier League)
- **Rate Limiting:** 0.5 seconds between requests
- **Authentication:** RapidAPI key from `.env` file

### Available Methods

#### Team & Player Data
- `get_teams_statistics()` - Season stats for all teams
- `get_team_players(team_id, stat_type)` - Player stats for a team
- `get_team_squad(team_id)` - Complete team roster

#### Fixtures
- `get_fixtures(course, page)` - Paginated fixture list
- `get_all_fixtures(course)` - All fixtures with auto-pagination
  - `course='last'` - Past games
  - `course='next'` - Future games

#### Match Details
- `get_event_lineups(event_id)` - Player lineups with embedded statistics
- `get_player_heatmap(player_id, event_id)` - Movement coordinates

#### Player Statistics
- `get_player_season_statistics(player_id)` - Aggregated season stats
- `get_player_attribute_overviews(player_id)` - Radar chart attributes (attacking, technical, tactical, defending, creativity)

---

## ETL Scripts

### Location
`/app/sofa_sport/scripts/`

### 1. `build_team_mapping.py`
**Purpose:** Create mapping between SofaSport and FPL teams

**Process:**
1. Fetch team statistics from SofaSport
2. Fuzzy match team names (80% threshold)
3. Generate `team_mapping.json`
4. Manual additions for missing teams

**Output:** 20/20 teams mapped

### 2. `build_player_mapping.py`
**Purpose:** Create mapping between SofaSport and FPL players

**Process:**
1. For each SofaSport team, fetch complete squad
2. Fuzzy match on full names (75% threshold)
3. Prioritize full name matches (+5 score boost for scores ≥85)
4. Generate `player_mapping.json`
5. Display full names for verification

**Output:** 552/743 players mapped (74.3%)

**Key Features:**
- Full name matching prevents false matches (e.g., Richarlison ≠ Son)
- Shows both web_name and full_name for user verification
- Handles multiple players with similar names

### 3. `build_fixture_mapping.py`
**Purpose:** Match SofaSport events to FPL fixtures and populate database

**Process:**
1. Fetch all past fixtures from SofaSport (with pagination)
2. For each event:
   - Extract home/away team IDs
   - Match to FPL teams using mapping
   - Find corresponding FPL fixture by teams and date
3. Create `SofasportFixture` records with:
   - Event ID, team links, scores, formations
   - Match status, kickoff time, data availability flags
   - Complete raw API response

**Output:** 70 fixtures matched (100% success rate)

**Matching Logic:**
- Primary: Home team + Away team must match
- Secondary: If multiple matches, use closest kickoff time
- Handles timezone conversions for datetime fields

### 4. `build_lineups_etl.py`
**Purpose:** Fetch and store player lineups with per-match statistics

**Process:**
1. For each `SofasportFixture`:
   - Call `get_event_lineups(event_id)`
   - Extract home and away team lineups
   - For each player:
     - Match to FPL athlete using player mapping
     - Extract position, shirt number, substitute status
     - Store complete `statistics` dict (20-60 fields)
     - Extract `minutes_played` for convenience
2. Update fixture with formations and confirmation status

**Output:** 2,733 lineup records with full statistics

**Statistics Included:**
- **Performance:** rating, minutesPlayed, touches
- **Passing:** totalPass, accuratePass, keyPasses, longBalls
- **Attacking:** goals, assists, totalShots, shotsOnTarget, expectedGoals, expectedAssists
- **Defending:** tackles, interceptions, clearances, blocks
- **Duels:** aerialDuelsWon, groundDuelsWon, totalDuelsWon
- **Discipline:** yellowCards, redCards, fouls, wasFouled
- **Goalkeeper:** saves, punches, keeperSweeper, goalsConceded
- **Advanced:** rating versions, normalized values, possession lost

### 5. `build_season_stats_etl.py`
**Purpose:** Fetch aggregated season statistics for all mapped players

**Process:**
1. For each player in `player_mapping.json`:
   - Call `get_player_season_statistics(player_id)`
   - Extract and convert statistics (handle None values)
   - Round decimals to 2 places
   - Create `SofasportPlayerSeasonStats` record with:
     - Key extracted fields (rating, goals, assists, etc.)
     - Complete statistics JSON
     - Default `display_stats=True` and `category=null`

**Output:** ~500-550 season stat records

**Data Extraction:**
- Safe type conversions (handles None, type mismatches)
- Decimal precision limited to 2 places
- Separate goalkeeper stats (saves, clean sheets)
- Team association from player mapping

**Error Handling:**
- 404 errors for players without data (gracefully skipped)
- API errors logged but don't stop processing
- Continues through all 552 players

### 6. `build_radar_attributes_etl.py`
**Purpose:** Fetch player attribute ratings for radar chart visualization

**Process:**
1. For each player in `player_mapping.json`:
   - Call `get_player_attribute_overviews(player_id)`
   - Extract attributes with priority:
     - First: `attributeOverviews` with `yearShift=0` (current season)
     - Fallback: `averageAttributeOverviews[0]` (career average)
   - Create `SofasportPlayerAttributes` record with:
     - Attribute ratings: attacking, technical, tactical, defending, creativity
     - Position, year_shift, is_average flag
     - Complete raw_data JSON

**Output:** ~500-550 attribute records (mostly career averages)

**Attribute Scale:** 0-100 for each dimension
- **Attacking:** Goal scoring, shots, positioning in attack
- **Technical:** Ball control, passing accuracy, dribbling
- **Tactical:** Positioning, game reading, decision making
- **Defending:** Tackles, interceptions, defensive positioning
- **Creativity:** Key passes, assists, chance creation

**Error Handling:**
- 404 errors for young/new players without data (gracefully skipped)
- Falls back to career average if current season not available
- Most players return career averages from `averageAttributeOverviews`

**Processing Time:** ~5 minutes for 552 players (0.5s rate limit)

### 7. `build_heatmap_etl.py`
**Purpose:** Collect player movement heatmap data using selective criteria

**Process:**
1. Analyze all 2,733 SofasportLineup records
2. Apply filtering criteria to identify qualifying players (ANY met):
   - Minutes played ≥60
   - Rating ≥7.0
   - Goals + Assists ≥1
   - Player's total FPL points ≥30
   - Started the match (not substitute)
3. For each qualifying player:
   - Check if heatmap already exists (skip duplicates)
   - Call `get_player_heatmap(player_id, event_id)`
   - Store coordinate array and point count in `SofasportHeatmap` table

**Output:** ~1,600 heatmaps (60% of all lineups)

**Criteria Effectiveness:**
- Minutes ≥60: 1,450 lineups
- Rating ≥7.0: 642 lineups  
- Goals+Assists ≥1: 256 lineups
- FPL Points ≥30: 318 lineups
- Started: 1,535 lineups

**Selective Collection Benefits:**
- Reduces API calls from 2,733 → ~1,633 (40% reduction)
- Processing time: ~13-15 minutes (vs 23 minutes for full collection)
- Focuses on valuable players worth analyzing
- Skips low-minute substitutes with minimal pitch presence

**Coordinate Data:**
- Each point is `{x: int, y: int}` on 0-100 grid
- Typical heatmap: 20-80 coordinate points
- Higher point counts indicate more active players

**Error Handling:**
- 404 errors for matches without heatmap data (gracefully skipped)
- Duplicate detection prevents re-fetching existing heatmaps
- Progress tracking shows criteria met for each player

**Processing Time:** ~13-15 minutes for 1,633 qualifying players (0.5s rate limit)

---

## Usage Examples

### Query Per-Match Stats
```python
from etl.models import SofasportLineup

# Get Salah's stats for a specific match
lineup = SofasportLineup.objects.get(
    athlete__web_name='Salah',
    fixture__fixture__event=5  # GW5
)

stats = lineup.statistics
print(f"Rating: {stats['rating']}")
print(f"Goals: {stats.get('goals', 0)}")
print(f"Expected Goals: {stats.get('expectedGoals', 0)}")
print(f"Passes: {stats['accuratePass']}/{stats['totalPass']}")
```

### Query Season Aggregates
```python
from etl.models import SofasportPlayerSeasonStats

# Get top rated players
top_players = SofasportPlayerSeasonStats.objects.filter(
    display_stats=True,
    minutes_played__gte=200
).order_by('-rating')[:10]

for player in top_players:
    print(f"{player.athlete.web_name}: {player.rating}")
    print(f"  G:{player.goals} A:{player.assists} Mins:{player.minutes_played}")
```

### Query Radar Chart Attributes
```python
from etl.models import SofasportPlayerAttributes

# Get player attributes for radar chart
player_attrs = SofasportPlayerAttributes.objects.get(
    athlete__web_name='Salah',
    year_shift=0,
    is_average=False
)

# Build radar chart data
radar_data = {
    'attacking': player_attrs.attacking,
    'technical': player_attrs.technical,
    'tactical': player_attrs.tactical,
    'defending': player_attrs.defending,
    'creativity': player_attrs.creativity
}

# Or fallback to career average if current season not available
try:
    current_season = SofasportPlayerAttributes.objects.get(
        athlete__web_name='Salah',
        year_shift=0,
        is_average=False
    )
except SofasportPlayerAttributes.DoesNotExist:
    current_season = SofasportPlayerAttributes.objects.get(
        athlete__web_name='Salah',
        is_average=True
    )

# Compare players by position
forwards = SofasportPlayerAttributes.objects.filter(
    position='F',
    is_average=False
).order_by('-attacking')[:10]

for attr in forwards:
    print(f"{attr.athlete.web_name}: ATT={attr.attacking}, CRE={attr.creativity}")
```

### Filter by Category
```python
# Get all goalkeeper stats
gk_stats = SofasportPlayerSeasonStats.objects.filter(
    category='goalkeeper',
    display_stats=True
).select_related('athlete', 'team')

for stat in gk_stats:
    print(f"{stat.athlete.web_name}: {stat.saves} saves, {stat.clean_sheets} CS")
```

### Query Fixture Details
```python
from etl.models import SofasportFixture

# Get a specific match
fixture = SofasportFixture.objects.get(
    home_team__name='Arsenal',
    away_team__name='Liverpool',
    fixture__event=3
)

print(f"Score: {fixture.home_score_current}-{fixture.away_score_current}")
print(f"Formations: {fixture.home_formation} vs {fixture.away_formation}")
print(f"Has xG data: {fixture.has_xg}")
```

### Query Player Heatmaps
```python
from etl.models import SofasportHeatmap

# Get heatmap for a specific player in a specific match
heatmap = SofasportHeatmap.objects.get(
    athlete__web_name='Salah',
    fixture__fixture__event=3
)

# Access coordinate data
coordinates = heatmap.coordinates  # List of {x, y} dicts
point_count = heatmap.point_count

# Render heatmap visualization
for point in coordinates:
    x = point['x']  # 0-100 scale (left to right)
    y = point['y']  # 0-100 scale (top to bottom)
    # Map to pitch dimensions and draw

# Get all heatmaps for a player across season
player_heatmaps = SofasportHeatmap.objects.filter(
    athlete__web_name='Salah'
).select_related('fixture__fixture').order_by('fixture__fixture__event')

for hm in player_heatmaps:
    gw = hm.fixture.fixture.event
    print(f"GW{gw}: {hm.point_count} coordinate points")

# Find most active players (highest point counts)
most_active = SofasportHeatmap.objects.select_related(
    'athlete', 'fixture__fixture'
).order_by('-point_count')[:10]

for hm in most_active:
    print(f"{hm.athlete.web_name} - GW{hm.fixture.fixture.event}: {hm.point_count} points")
```

### Filter by Category
```python
# Get all goalkeeper stats
gk_stats = SofasportPlayerSeasonStats.objects.filter(
    category='goalkeeper',
    display_stats=True
).select_related('athlete', 'team')

for stat in gk_stats:
    print(f"{stat.athlete.web_name}: {stat.saves} saves, {stat.clean_sheets} CS")
```

### Query Fixture Details
```python
from etl.models import SofasportFixture

# Get a specific match
fixture = SofasportFixture.objects.get(
    home_team__name='Arsenal',
    away_team__name='Liverpool',
    fixture__event=3
)

print(f"Score: {fixture.home_score_current}-{fixture.away_score_current}")
print(f"Formations: {fixture.home_formation} vs {fixture.away_formation}")
print(f"Has xG data: {fixture.has_xg}")
print(f"Lineups confirmed: {fixture.lineups_confirmed}")
```

---

## Data Refresh Strategy

### Initial Load (Completed)
1. ✅ Build team mapping (one-time)
2. ✅ Build player mapping (update when new players join)
3. ✅ Map fixtures (run after each gameweek)
4. ✅ Collect lineups (run after each gameweek)
5. 🔄 Collect season stats (run weekly/monthly)
6. ⏳ Collect heatmaps (run after each gameweek)

### Ongoing Updates
- **Fixtures:** Run after each gameweek to add new matches
- **Lineups:** Run after matches are completed
- **Season Stats:** Run weekly to update aggregates
- **Heatmaps:** Run after each gameweek (optional, high API usage)
- **Player Mapping:** Update when new players are registered

### Automation Recommendations
1. Schedule `build_fixture_mapping.py` to run Monday mornings
2. Schedule `build_lineups_etl.py` to run Tuesday mornings (after matches complete)
3. Schedule `build_season_stats_etl.py` to run weekly on Wednesdays
4. Schedule `build_heatmap_etl.py` based on frontend demand

---

## API Rate Limits

### Current Implementation
- **Rate Limit:** 0.5 seconds between requests
- **Total Requests for Full Sync:**
  - Fixtures: ~10-20 (with pagination)
  - Lineups: 70 (one per fixture)
  - Season Stats: 552 (one per player) → **~5 minutes**
  - Heatmaps: 2,733 (one per lineup entry) → **~23 minutes**

### Optimization Strategies
1. **Batch Processing:** Process in chunks with progress tracking
2. **Incremental Updates:** Only fetch new fixtures/matches
3. **Caching:** Store raw responses to avoid re-fetching
4. **Selective Heatmaps:** Only collect for starters or high-value players

---

## Frontend Integration

### Available Data

#### Player Profile Page
- **Season Stats:** Display aggregated performance metrics
  - Filter by `display_stats=True`
  - Group by `category` (attacking, defensive, etc.)
  - Show rating, goals, assists, pass accuracy, etc.

#### Match Detail Page
- **Per-Match Stats:** Show individual match performance
  - Query `SofasportLineup` for specific fixture
  - Display rating, goals, shots, passes, duels
  - Compare with FPL points earned

#### Player Heatmap Visualization
- **Movement Data:** Render pitch heatmap
  - Query `SofasportHeatmap` coordinates
  - Plot on 100x100 grid representing pitch
  - Color by density/intensity

#### Fixture Analysis
- **Match Overview:** Formations, scores, lineups
  - Display team formations
  - Show starting XI vs substitutes
  - Half-time and full-time scores

---

## Configuration

### Environment Variables (`.env`)
```bash
RAPIDAPI_KEY=your_api_key_here
SOFASPORT_SEASON_ID=76986
SOFASPORT_TOURNAMENT_ID=17
```

### Django Settings
- Models in `etl/models.py`
- All tables use `sofasport_` prefix
- Foreign keys with CASCADE or SET_NULL appropriately
- Indexes on all frequently queried fields

---

## Troubleshooting

### Common Issues

**404 Errors for Player Stats:**
- Some players don't have statistics in SofaSport
- Script handles gracefully and continues
- Check player has appearances in the season

**Unmapped Players:**
- 67 players in lineups not in our mapping (74.3% coverage)
- Most are low-value or recently transferred
- Review `players_to_review.md` to add important players

**Timezone Warnings:**
- Django expects timezone-aware datetimes
- Current: Using naive datetimes from Unix timestamps
- Fix: Convert with `timezone.make_aware()` if needed

**Memory Usage:**
- Large JSON fields (statistics, coordinates)
- Consider PostgreSQL JSONB indexing for queries
- Archive old season data if database grows large

---

## Next Steps

1. ✅ **Complete Season Stats ETL** - Currently running
2. 📋 **Implement Heatmap Collection** - See plan below
3. 🎨 **Frontend Integration** - Build API endpoints and UI components
4. 📊 **Add Season Stats Categories** - Classify stats as attacking/defensive/etc.
5. 🔄 **Automate Data Refresh** - Set up scheduled tasks
6. 📈 **Add Analytics** - Correlate SofaSport stats with FPL points
7. 🔍 **Advanced Queries** - Build comparison and ranking features

---

## Files Summary

```
sofa_sport/
├── scripts/
│   ├── api_client.py              # SofaSport API wrapper
│   ├── build_team_mapping.py      # Team mapping ETL
│   ├── build_player_mapping.py    # Player mapping ETL
│   ├── build_fixture_mapping.py   # Fixture matching ETL
│   ├── build_lineups_etl.py       # Lineups + per-match stats ETL
│   ├── build_season_stats_etl.py  # Season aggregates ETL
│   └── build_heatmap_etl.py       # (Planned) Heatmap collection
├── mappings/
│   ├── team_mapping.json          # 20 teams
│   ├── player_mapping.json        # 552 players
│   ├── players_to_review.md       # 11 unmapped players
│   └── unmatched_fixtures.json    # (Empty)
├── .env                           # API credentials
├── requirements.txt               # Python dependencies
├── README.md                      # Project overview
└── API_STRUCTURE_ANALYSIS.md     # API response documentation
```

---

## Contact & Support

For issues or questions:
1. Check API response structure in `API_STRUCTURE_ANALYSIS.md`
2. Review mapping files for coverage
3. Check Django model definitions in `etl/models.py`
4. Verify environment variables in `.env`

---

**Last Updated:** October 6, 2025  
**Version:** 1.0  
**Status:** Production-ready (pending heatmap collection)
