# Heatmap Collection Strategy

## Overview

Collect player movement coordinates from SofaSport API to enable pitch heatmap visualizations showing where players were active during matches.

---

## Challenge: API Volume

### The Problem
- **Total lineup entries:** 2,733 players across 70 fixtures
- **API calls needed:** 2,733 (one per player per match)
- **With 0.5s rate limit:** ~23 minutes for full collection
- **RapidAPI monthly quota:** May be limited

### Solution Options

#### Option 1: Full Collection (Comprehensive)
**Pros:**
- Complete heatmap data for all players
- No filtering decisions needed
- Historical data preserved

**Cons:**
- 2,733 API calls (~23 minutes)
- High API quota usage
- Many heatmaps may never be viewed

#### Option 2: Selective Collection (Recommended)
**Pros:**
- Faster processing (5-10 minutes)
- Lower API usage
- Focuses on valuable players

**Cons:**
- Need filtering criteria
- May miss some interesting players
- Requires manual review of filters

#### Option 3: On-Demand Collection (Future Enhancement)
**Pros:**
- Zero upfront API usage
- Only fetch when user requests
- Most efficient long-term

**Cons:**
- User waits for data
- Requires caching strategy
- More complex implementation

---

## Recommended Approach: **Option 2 - Selective Collection**

### Filtering Criteria

Collect heatmaps ONLY for players meeting ANY of these conditions:

1. **High Minutes:** Played ≥ 60 minutes in the match
   - Rationale: Starters and key subs have meaningful heatmaps
   
2. **High Rating:** SofaScore rating ≥ 7.0 in the match
   - Rationale: Good performances worth analyzing
   
3. **Goal Contributors:** Goals + Assists ≥ 1 in the match
   - Rationale: Impactful players users want to see
   
4. **Top FPL Value:** Player total_points ≥ 30 (from FPL database)
   - Rationale: Popular FPL picks regardless of single match performance
   
5. **Not a Substitute:** started the match (substitute=False)
   - Rationale: Prioritize starters over late subs

### Expected Reduction
Estimated filters will reduce from **2,733 → ~800-1,200 players** (~60% reduction)
- Processing time: ~7-10 minutes
- API calls saved: ~1,500

---

## Implementation Plan

### Script: `build_heatmap_etl.py`

### Process Flow

```python
1. Query all SofasportLineup records
2. Apply filters to identify target players:
   - Extract from lineup.statistics: minutesPlayed, rating, goals, goalAssist
   - Check athlete.total_points from FPL data
   - Check lineup.substitute flag
3. For each qualifying player:
   - Call get_player_heatmap(sofasport_player_id, sofasport_event_id)
   - Parse coordinates array
   - Create SofasportHeatmap record with:
     - coordinates JSONField
     - point_count
     - Links to athlete, fixture, lineup
4. Track stats: collected, skipped, errors
5. Log skipped players for review
```

### Code Structure

```python
def should_collect_heatmap(lineup: SofasportLineup) -> bool:
    """
    Determine if heatmap should be collected for this player.
    Returns True if ANY criteria met.
    """
    stats = lineup.statistics or {}
    
    # Criteria 1: High minutes
    if stats.get('minutesPlayed', 0) >= 60:
        return True
    
    # Criteria 2: High rating
    if stats.get('rating', 0) >= 7.0:
        return True
    
    # Criteria 3: Goal contributor
    goals = stats.get('goals', 0) or 0
    assists = stats.get('goalAssist', 0) or 0
    if (goals + assists) >= 1:
        return True
    
    # Criteria 4: Top FPL value
    if lineup.athlete.total_points >= 30:
        return True
    
    # Criteria 5: Started (not sub)
    if not lineup.substitute:
        return True
    
    return False


def process_heatmap(lineup: SofasportLineup, client: SofaSportClient):
    """
    Fetch and store heatmap for a single player.
    """
    # Check if already exists
    if SofasportHeatmap.objects.filter(
        athlete=lineup.athlete,
        fixture=lineup.fixture
    ).exists():
        return 'skipped_exists'
    
    # Fetch from API
    heatmap_data = client.get_player_heatmap(
        lineup.sofasport_player_id,
        lineup.fixture.sofasport_event_id
    )
    
    if not heatmap_data or 'data' not in heatmap_data:
        return 'no_data'
    
    coordinates = heatmap_data['data']
    
    # Create record
    SofasportHeatmap.objects.create(
        sofasport_player_id=lineup.sofasport_player_id,
        athlete=lineup.athlete,
        fixture=lineup.fixture,
        lineup=lineup,
        coordinates=coordinates,
        point_count=len(coordinates) if isinstance(coordinates, list) else 0
    )
    
    return 'created'
```

### Progress Tracking

```python
# Print detailed progress
for i, lineup in enumerate(qualifying_lineups, 1):
    print(f"[{i}/{total}] {lineup.player_name} - GW{gw}")
    print(f"  Criteria: {get_criteria_met(lineup)}")
    result = process_heatmap(lineup, client)
    print(f"  Result: {result}")
```

---

## Alternative: Phased Collection

### Phase 1: High-Priority Players (~400 players)
**Criteria:** Top FPL picks + Goal contributors
- Estimated time: ~3-4 minutes
- Most valuable heatmaps first

### Phase 2: Starters (~600 more players)
**Criteria:** All starters (substitute=False)
- Estimated time: ~5 minutes
- Complete coverage of starting XIs

### Phase 3: Remaining High-Minute Players (~200 players)
**Criteria:** Played ≥ 60 minutes (subs who played significant time)
- Estimated time: ~2 minutes
- Catch important substitutes

**Benefits:**
- Can stop after Phase 1 if API limits approaching
- Prioritizes most valuable data
- Easy to resume later

---

## Data Storage Optimization

### Coordinate Compression (Optional Enhancement)

**Current:** Store full array
```json
{
  "coordinates": [
    {"x": 45, "y": 50},
    {"x": 46, "y": 50},
    {"x": 45, "y": 51},
    ...
  ]
}
```

**Compressed:** Group by density buckets (5x5 grid)
```json
{
  "heatmap_grid": {
    "45-50": 15,  // 15 points in this 5x5 cell
    "50-50": 8,
    ...
  }
}
```

**Benefits:**
- Smaller JSON size
- Faster rendering
- Same visual result

**Trade-offs:**
- Loses precise coordinate data
- Can't recreate exact movement path
- Implement later if storage/performance becomes issue

---

## Frontend Visualization

### Rendering Strategy

1. **Query heatmap:**
```python
heatmap = SofasportHeatmap.objects.get(
    athlete_id=player_id,
    fixture__fixture__event=gameweek
)
coordinates = heatmap.coordinates
```

2. **Create pitch overlay:**
```javascript
// coordinates are on 0-100 grid
// Map to actual pitch dimensions (105m x 68m standard)
coordinates.forEach(point => {
  const x = (point.x / 100) * pitchWidth;
  const y = (point.y / 100) * pitchHeight;
  
  // Draw heatpoint or increment density grid
  drawHeatPoint(x, y);
});
```

3. **Apply heatmap coloring:**
- Red = High density (player spent lot of time here)
- Yellow = Medium density
- Green/Blue = Low density

### Libraries
- **Canvas-based:** Heatmap.js
- **SVG-based:** D3.js with gradient fills
- **WebGL:** Three.js for 3D effects

---

## Error Handling

### Expected Errors

**404 Not Found:**
- Some matches may not have heatmap data
- Gracefully skip and log
- Don't count as critical error

**Rate Limit Exceeded:**
- Pause for longer period
- Resume from last successful fetch
- Save progress checkpoint

**Network Timeout:**
- Retry with exponential backoff
- Max 3 retries per player
- Log and continue

---

## Performance Estimates

### Selective Collection (Recommended)
- **Players:** ~1,000 (36% of total)
- **Time:** ~8 minutes
- **API calls:** 1,000
- **Storage:** ~5-10 MB (100 points avg per player)

### Full Collection
- **Players:** 2,733 (100%)
- **Time:** ~23 minutes
- **API calls:** 2,733
- **Storage:** ~15-30 MB

### Phased Collection
- **Phase 1:** ~400 players (~3 min)
- **Phase 2:** +600 players (~5 min)
- **Phase 3:** +200 players (~2 min)
- **Total:** ~1,200 players (~10 min)

---

## Testing Strategy

### Test with Small Sample First

1. **Single Player Test:**
```python
# Test API call and data structure
lineup = SofasportLineup.objects.first()
heatmap = client.get_player_heatmap(
    lineup.sofasport_player_id,
    lineup.fixture.sofasport_event_id
)
print(json.dumps(heatmap, indent=2))
```

2. **Ten Players Test:**
```python
# Test filtering and storage
test_lineups = SofasportLineup.objects.filter(
    minutes_played__gte=60
)[:10]
# Run collection script
```

3. **Full Collection:**
```python
# Run on all qualifying players
# Monitor for errors and performance
```

---

## Maintenance & Updates

### When to Refresh

**After Each Gameweek:**
- Collect heatmaps for new fixtures
- Only fetch for new lineup entries
- Skip existing heatmap records

**Incremental Query:**
```python
# Only lineups without heatmaps
new_lineups = SofasportLineup.objects.filter(
    heatmap__isnull=True,
    fixture__fixture__event=current_gameweek
)
```

### Cleanup Strategy

**Archive Old Seasons:**
- Heatmaps for seasons >2 years old rarely accessed
- Move to cold storage or delete
- Keep season stats, remove coordinates

**Selective Deletion:**
```python
# Remove heatmaps for low-value players after season ends
SofasportHeatmap.objects.filter(
    athlete__total_points__lt=20,
    fixture__fixture__event__lt=current_season_first_gw
).delete()
```

---

## Implementation Checklist

- [ ] Create `build_heatmap_etl.py` script
- [ ] Implement filtering logic (`should_collect_heatmap()`)
- [ ] Add progress tracking and logging
- [ ] Test with 10 players
- [ ] Run Phase 1 collection (high priority)
- [ ] Verify data in database
- [ ] Run Phase 2 collection (starters)
- [ ] Run Phase 3 collection (remaining)
- [ ] Create frontend API endpoint
- [ ] Build heatmap visualization component
- [ ] Test end-to-end user experience
- [ ] Document API endpoints
- [ ] Set up automated refresh schedule

---

## Estimated Resource Usage

### API Quota
- **Selective:** 1,000 calls per gameweek
- **Full:** 2,733 calls per gameweek
- **Season (38 GWs):** 38,000 - 104,000 calls

### Database Storage
- **Per heatmap:** ~1-5 KB (depending on point count)
- **1,000 heatmaps:** 1-5 MB
- **Full season:** 40-200 MB

### Processing Time
- **Initial load:** 8-23 minutes (one-time)
- **Weekly refresh:** 2-5 minutes (new fixtures only)

---

## Recommendation Summary

**Start with Selective Collection (Option 2):**

1. Implement filtering criteria:
   - Minutes ≥ 60 OR
   - Rating ≥ 7.0 OR
   - Goals+Assists ≥ 1 OR
   - FPL points ≥ 30 OR
   - Started match

2. Expected results:
   - ~1,000 heatmaps collected
   - ~8 minutes processing time
   - Covers all important players

3. Can expand later:
   - Add more players if frontend demand increases
   - Switch to on-demand collection for edge cases
   - Archive low-value heatmaps after season

**This approach balances:**
- ✅ API efficiency
- ✅ Processing speed
- ✅ Data completeness for valuable players
- ✅ Storage optimization

---

**Ready to implement?** Say the word and I'll create `build_heatmap_etl.py` with the selective collection strategy! 🚀
