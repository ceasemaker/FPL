# SofaSport API Structure Analysis

This document captures the actual API response structures to ensure database models match the real data.

## 1. Fixtures API (`/unique-tournament/17/season/76986/events/last`)

**Endpoint:** `get_fixtures(course='last', page=0)`

**Response Structure:**
```json
{
  "data": {
    "events": [ /* array of event objects */ ],
    "hasNextPage": true/false
  }
}
```

**Single Event Object:**
```json
{
  "id": 14025166,  // Integer, not string
  "homeTeam": {
    "name": "Liverpool",
    "id": 44
  },
  "awayTeam": {
    "name": "Everton",
    "id": 48
  },
  "homeScore": {
    "current": 2,
    "display": 2,
    "period1": 2,
    "period2": 0,
    "normaltime": 2
  },
  "awayScore": {
    "current": 1,
    "display": 1,
    "period1": 0,
    "period2": 1,
    "normaltime": 1
  },
  "status": {
    "type": "finished"  // or "inprogress", "notstarted", etc.
  },
  "startTimestamp": 1758367800,  // Unix timestamp (integer)
  "slug": "liverpool-everton",
  "hasXg": true,
  "hasEventPlayerStatistics": true,
  "hasEventPlayerHeatMap": true,
  // ... many other fields
}
```

**Key Fields:**
- `id`: BigInteger (event ID)
- `homeTeam.id` / `awayTeam.id`: BigInteger (team IDs)
- `startTimestamp`: Unix timestamp (convert to datetime)
- Scores: Nested dicts with period breakdowns
- Boolean flags: `hasXg`, `hasEventPlayerStatistics`, `hasEventPlayerHeatMap`

---

## 2. Lineups API (`/event/{event_id}/lineups`)

**Endpoint:** `get_event_lineups(event_id)`

**Response Structure:**
```json
{
  "data": {
    "confirmed": true,  // Boolean at top level
    "home": {
      "players": [ /* array of player objects */ ],
      "supportStaff": [],
      "formation": "4-3-3",
      "playerColor": {...},
      "goalkeeperColor": {...},
      "missingPlayers": []
    },
    "away": {
      // Same structure as home
    }
  }
}
```

**Single Player Object in Lineup:**
```json
{
  "player": {
    "name": "Alisson",
    "slug": "alisson",
    "shortName": "Alisson",
    "position": "G",
    "jerseyNumber": "1",
    "id": 243609,  // BigInteger
    "country": {...},
    // ... other player metadata
  },
  "teamId": 44,  // BigInteger
  "shirtNumber": 1,
  "position": "G",
  "substitute": false,  // Boolean: true if started on bench
  "statistics": {
    // ⚠️ IMPORTANT: Statistics are embedded HERE, not in a separate endpoint
    "totalPass": 42,
    "accuratePass": 33,
    "totalLongBalls": 14,
    "accurateLongBalls": 5,
    "goalAssist": 0,
    "aerialWon": 2,
    "duelWon": 2,
    "totalClearance": 3,
    "ballRecovery": 10,
    "saves": 1,
    "minutesPlayed": 90,  // Extract this for convenience
    "touches": 52,
    "rating": 6.9,
    "expectedAssists": 0.00047864,
    "ratingVersions": {
      "original": 6.9,
      "alternative": 6.7
    },
    // ... 50+ more statistics fields
  }
}
```

**Key Insights:**
- **No separate player stats table needed** - statistics are embedded in lineup
- `confirmed` field is at the data level, applies to entire lineup
- Players have `substitute: true/false` (starting bench status)
- `minutesPlayed` can be extracted from statistics for convenience
- Position comes from both player metadata and lineup entry
- Each player has a full `statistics` dict with 50+ metrics

---

## 3. Player Heatmap API (`/event/{event_id}/player/{player_id}/heatmap`)

**Endpoint:** `get_player_heatmap(player_id, event_id)`

**Response Structure:**
```json
{
  "data": [
    {"x": 4, "y": 49},
    {"x": 8, "y": 49},
    {"x": 10, "y": 48},
    {"x": 12, "y": 48},
    // ... 69 points for this example
  ]
}
```

**Key Insights:**
- Simple array of coordinate objects
- Each point has `x` and `y` (integers, typically 0-100 range)
- No intensity value - frequency is implied by point density
- Array length varies by player activity (69 points for this goalkeeper example)
- Store as JSONB array directly

---

## Database Model Design Decisions

Based on the API analysis:

### ✅ SofasportFixture
- Store event ID as `BigIntegerField` (not CharField)
- Store team IDs as `BigIntegerField`
- Break out score periods into separate columns
- Store formations from lineup data
- Add boolean flags for data availability
- Store `startTimestamp` and convert to datetime

### ✅ SofasportLineup
- **Statistics stored as JSONField** (not separate table)
- Extract `minutesPlayed` for convenience queries
- `substitute` boolean (starting bench status)
- No need for `category` or `display_stats` - lineup is confirmed or not
- Store player name/slug for debugging

### ❌ SofasportPlayerStat (REMOVED)
- Not needed - statistics are embedded in SofasportLineup
- Would create unnecessary duplication and complexity
- The `statistics` JSONField in lineup is more flexible

### ✅ SofasportHeatmap
- Store coordinates as JSONField array
- Add `point_count` for quick reference
- Link to lineup entry via OneToOneField
- Simple structure matches API response

---

## Sample Statistics Available (50+ fields)

From the lineup statistics dict:

**Passing:**
- totalPass, accuratePass
- totalLongBalls, accurateLongBalls
- accurateOwnHalfPasses, totalOwnHalfPasses
- accurateOppositionHalfPasses, totalOppositionHalfPasses

**Attacking:**
- totalShots, goalAssist
- expectedAssists, expectedGoals

**Defensive:**
- totalClearance, interceptions
- aerialWon, duelWon
- ballRecovery

**Goalkeeper:**
- saves, savedShotsFromInsideTheBox
- punches
- totalKeeperSweeper, accurateKeeperSweeper
- keeperSaveValue, goalsPrevented

**General:**
- minutesPlayed, touches
- rating (SofaScore rating)
- ratingVersions (original and alternative ratings)
- possessionLostCtrl

**Normalized Values:**
- passValueNormalized
- dribbleValueNormalized
- defensiveValueNormalized
- goalkeeperValueNormalized

---

## Migration Impact

**3 Models (not 4):**
1. SofasportFixture - Event/fixture data
2. SofasportLineup - Player lineups with embedded statistics JSONField
3. SofasportHeatmap - Player movement coordinates

**Field Type Changes:**
- IDs: CharField → BigIntegerField
- More detailed score tracking (period1, period2)
- Formation fields added
- Statistics as JSONField instead of separate table
