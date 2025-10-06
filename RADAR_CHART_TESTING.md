# Radar Chart Testing Guide

Quick guide to test the new radar chart visualization in PlayerModal.

## 🎯 What Was Built

### 1. API Endpoints (5 new endpoints)
- `GET /api/sofasport/player/<id>/radar/` - Single player radar attributes
- `GET /api/sofasport/player/<id>/season-stats/` - Aggregated season statistics
- `GET /api/sofasport/player/<id>/heatmap/<gameweek>/` - Heatmap coordinates
- `GET /api/sofasport/player/<id>/match-stats/<gameweek>/` - Per-match statistics
- `GET /api/sofasport/compare/radar/?player_ids=123,456` - Multi-player comparison

### 2. RadarChart Component
- **Location:** `/frontend/src/components/RadarChart.tsx`
- **Props:** `playerIds: number[]`, `height?: number`, `width?: number`
- **Features:**
  - Canvas-based rendering (high DPI support)
  - 5 axes: Attacking, Technical, Tactical, Defending, Creativity
  - 1-4 player comparison with overlapping polygons
  - Legend with player names
  - Single-player view includes horizontal bar breakdown
  - Loading/error states

### 3. PlayerModal Integration
- Radar chart section added after fixtures display
- Shows automatically when modal opens
- Icon: 📊 Player Attributes

## 🧪 Testing Steps

### 1. Start the Application

```bash
# Start all services
docker-compose up -d

# Check services are running
docker ps

# Expected containers:
# - fpl_django_web (port 8000)
# - fpl_frontend (port 5173)
# - fpl_postgres
# - fpl_redis
# - fpl_celery_worker
# - fpl_celery_beat
```

### 2. Access the Frontend

Open browser: `http://localhost:5173`

### 3. Test Single Player Radar Chart

**Steps:**
1. Navigate to **Players** page
2. Click on any player card (e.g., Salah, Haaland, Saka)
3. Player modal opens with stats
4. Scroll down past fixtures section
5. Look for **📊 Player Attributes** section
6. Verify radar chart displays with:
   - Purple polygon showing 5 attributes
   - Axis labels (Attacking, Technical, Tactical, Defending, Creativity)
   - Horizontal bars below chart (single player view)
   - Legend showing player name

**Expected Behavior:**
- Chart loads within 1-2 seconds
- If no data: Shows "No radar data available" message
- If career average used: Legend shows "(Career Avg)"

### 4. Test API Endpoints Directly

**Test single player radar:**
```bash
# Get Salah's radar attributes (example player_id: 306)
curl http://localhost:8000/api/sofasport/player/306/radar/

# Expected response:
{
  "player_id": 306,
  "player_name": "Mohamed Salah",
  "position": "F",
  "attributes": {
    "attacking": 71,
    "technical": 64,
    "tactical": 46,
    "defending": 33,
    "creativity": 69
  },
  "is_average": false,
  "year_shift": 0
}
```

**Test comparison endpoint:**
```bash
# Compare 2 players (e.g., Salah vs Haaland)
curl "http://localhost:8000/api/sofasport/compare/radar/?player_ids=306,301"

# Expected response:
{
  "players": [
    {
      "player_id": 306,
      "player_name": "Mohamed Salah",
      "position": "F",
      "attributes": {...}
    },
    {
      "player_id": 301,
      "player_name": "Erling Haaland",
      "position": "F",
      "attributes": {...}
    }
  ]
}
```

### 5. Test Comparison Mode (Future Feature)

**Note:** Current PlayerModal shows only single player. To test comparison mode, you'll need to:

1. Create a comparison UI component (future work)
2. Or test directly in browser console:

```javascript
// In browser console on Players page
import { RadarChart } from './components/RadarChart';

// Render comparison chart
<RadarChart playerIds={[306, 301, 295]} height={500} width={500} />
```

**Expected Result:**
- Multiple colored polygons overlapping
- Legend shows all player names with color indicators
- No horizontal bars (multi-player mode)

### 6. Check for Errors

**Browser Console:**
```
F12 → Console tab
Look for:
- ✅ No red errors
- ⚠️ Check for API fetch errors
- 🔍 Network tab: Verify /api/sofasport/player/*/radar/ returns 200
```

**Django Logs:**
```bash
docker logs fpl_django_web --tail 50

# Look for:
# - "GET /api/sofasport/player/*/radar/ 200"
# - No 500 errors
# - Cache hits after first request
```

## 🎨 Visual Checklist

When testing, verify these visual elements:

### Radar Chart Container
- [ ] Dark background with purple border
- [ ] Border radius: 16px
- [ ] Proper spacing/padding

### Canvas Element
- [ ] Crisp rendering (high DPI)
- [ ] 5 axes extending from center
- [ ] Scale circles: 20, 40, 60, 80, 100
- [ ] Grid lines visible

### Player Polygon
- [ ] Purple fill (30% opacity)
- [ ] Purple border (90% opacity)
- [ ] Data points as circles
- [ ] Smooth polygon shape

### Legend
- [ ] Color square next to player name
- [ ] "(Career Avg)" text if applicable
- [ ] Proper spacing between items

### Single-Player Bars (only when 1 player)
- [ ] 5 horizontal bars
- [ ] Labels: Attacking, Technical, Tactical, Defending, Creativity
- [ ] Percentage values displayed
- [ ] Purple gradient fill
- [ ] Smooth width animation

### Responsive Design
Test on mobile viewport (<600px):
- [ ] Chart scales down appropriately
- [ ] Legend wraps to multiple rows
- [ ] Text remains readable
- [ ] No horizontal scroll

## 🐛 Common Issues & Fixes

### Issue: Chart Not Showing
**Fix:**
1. Check player has SofaSport data: `SELECT * FROM etl_sofasportplayerattributes WHERE player_id = <id>;`
2. Verify API returns data: `curl http://localhost:8000/api/sofasport/player/<id>/radar/`
3. Check browser console for errors

### Issue: "No radar data available"
**Fix:**
- Player may not have SofaSport attributes yet
- Try a different player (e.g., Salah, Haaland, Saka)
- Check database: `SELECT COUNT(*) FROM etl_sofasportplayerattributes;`

### Issue: Chart Shows "(Career Avg)"
**This is expected behavior:**
- If current season data unavailable, falls back to career average
- `is_average: true` in API response
- Not an error, just informational

### Issue: API Returns 404
**Fix:**
1. Check player_id is correct
2. Verify SofaSport ETL has run: `docker logs fpl_django_etl | grep sofasport`
3. Run ETL manually: `docker exec fpl_django_etl python manage.py run_fpl_etl --sofasport`

### Issue: Comparison Mode Not Working in Modal
**Expected:**
- Current implementation only shows single player in PlayerModal
- Comparison mode is implemented in RadarChart component
- To use comparison, create a separate comparison page (future feature)

## 📊 Test Data

**Players with confirmed SofaSport data:**
- Mohamed Salah (FPL ID: 306)
- Erling Haaland (FPL ID: 301)
- Bukayo Saka (FPL ID: 295)
- Kevin De Bruyne (FPL ID: 303)
- Bruno Fernandes (FPL ID: 304)

**Test these players first for guaranteed data.**

## 🔍 Verification Checklist

Before considering the feature complete:

### API Endpoints
- [ ] Single player radar returns correct JSON structure
- [ ] Comparison endpoint supports 2-4 players
- [ ] 24h caching working (check Redis)
- [ ] Error handling works (test with invalid IDs)
- [ ] Career average fallback triggers correctly

### RadarChart Component
- [ ] Renders for 1 player (with bars)
- [ ] Renders for 2 players (overlapping, no bars)
- [ ] Renders for 3-4 players (distinct colors)
- [ ] Loading spinner shows during fetch
- [ ] Error state displays friendly message
- [ ] Canvas rendering is crisp on Retina displays

### PlayerModal Integration
- [ ] Radar section appears after fixtures
- [ ] Section header displays with icon
- [ ] Info text shows 5 dimension names
- [ ] Chart renders automatically on modal open
- [ ] Layout doesn't break on mobile

### Styling
- [ ] Matches existing FPL Pulse theme
- [ ] CSS variables used consistently
- [ ] Responsive design works at all breakpoints
- [ ] No layout shifts or jumps

## 🚀 Next Steps (Future Work)

1. **Create Player Comparison Page**
   - Select 2-4 players
   - Side-by-side radar comparison
   - Export comparison as image

2. **Heatmap Visualization**
   - Pitch overlay component
   - Coordinate rendering from heatmap data
   - Animation of player movement

3. **Enhanced Stats Display**
   - Season stats table in modal
   - Per-gameweek stats chart
   - Match stats breakdown

4. **Radar Chart Improvements**
   - Tooltip on hover (show exact values)
   - Toggle between current season / career average
   - Download chart as PNG
   - Share comparison link

## 📝 Notes

- All SofaSport data cached for 24 hours
- Radar attributes scale: 0-100
- 5 dimensions based on SofaSport's player evaluation system
- Career average used as fallback if current season unavailable
- Frontend uses native Canvas API (no Chart.js dependency)

---

**Last Updated:** January 2025  
**Feature Status:** ✅ Complete (Single Player), 🚧 Comparison UI Pending
