# Wildcard Simulator - Implementation Guide

## Overview

Hybrid storage wildcard simulator with:
- ✅ Minimal database tracking for analytics
- ✅ localStorage for instant auto-save (free, fast)
- ✅ Full database save only when user clicks "Save & Share"
- ✅ Shareable team codes

## Files Created

### Backend
1. **`etl/models.py`** - Added `WildcardSimulation` model
2. **`etl/views_wildcard.py`** - API endpoints for wildcard feature
3. **`fpl_platform/urls.py`** - URL routing (updated)

### Frontend
4. **`static/js/wildcard-manager.js`** - JavaScript manager for hybrid storage
5. **`templates/wildcard/index.html`** - Main wildcard page

## Deployment Steps

### 1. Create Migration
```bash
cd django_etl
python manage.py makemigrations etl --name add_wildcard_simulation
python manage.py migrate
```

### 2. Commit and Push
```bash
git add .
git commit -m "Add wildcard simulator with hybrid storage"
git push origin main
```

### 3. Deploy to Render
- Render will automatically deploy
- Migration runs during build

## API Endpoints

### Track Team Start
```
POST /api/wildcard/track/
Response: { "success": true, "code": "WC-ABC123" }
```

### Get Team
```
GET /api/wildcard/{code}/
Response: { "success": true, "squad_data": {...}, "total_cost": 100.0, ... }
```

### Save Team
```
PATCH /api/wildcard/{code}/save/
Body: { "squad_data": {...}, "team_name": "My Team" }
Response: { "success": true, "code": "WC-ABC123", ... }
```

### Stats
```
GET /api/wildcard/stats/
Response: { "total_teams": 150, "saved_teams": 50, "drafts": 100 }
```

## Frontend Usage

### HTML
```html
<script src="/static/js/wildcard-manager.js"></script>
```

### JavaScript API
```javascript
// Access the manager
const manager = window.wildcardManager;

// Add player
manager.addPlayer(playerId);

// Remove player
manager.removePlayer(playerId);

// Set formation
manager.setFormation('3-4-3');

// Set captain
manager.setCaptain(playerId);

// Save to cloud (database)
manager.saveToCloud();

// Clear draft
manager.clearDraft();
```

## How It Works

### User Flow

1. **Visit `/wildcard/`**
   - JavaScript checks localStorage for existing code
   - If no code, calls `/api/wildcard/track/` to create tracking entry
   - Returns code: `WC-ABC123`
   - Code saved to localStorage

2. **Build Team**
   - User selects players
   - Auto-saves to localStorage every 30 seconds
   - Instant, no server calls

3. **Save & Share** (Optional)
   - User clicks "Save & Share" button
   - Calls `/api/wildcard/{code}/save/` with full team data
   - Database updated with complete squad
   - Shows modal with shareable code

4. **Return Later**
   - JavaScript loads draft from localStorage
   - Team restored instantly
   - Can continue editing

### Storage Strategy

| Data | Location | When | Cost |
|------|----------|------|------|
| Team code | localStorage | First visit | $0 |
| Minimal entry | Database | First visit | ~$0.0001 |
| Team edits | localStorage | Every 30s | $0 |
| Full save | Database | User clicks "Save" | ~$0.001 |

### Benefits

- ✅ Free auto-save for all users
- ✅ Fast (no network latency)
- ✅ Tracks all teams for analytics
- ✅ Minimal database costs
- ✅ Shareable teams when user wants

## Analytics

Access basic stats:
```bash
# In Django shell
from etl.models import WildcardSimulation

# Total teams created
WildcardSimulation.objects.count()

# Saved teams (user clicked "Save & Share")
WildcardSimulation.objects.filter(is_saved=True).count()

# Drafts only (localStorage only)
WildcardSimulation.objects.filter(is_saved=False).count()

# Created today
from django.utils import timezone
WildcardSimulation.objects.filter(
    created_at__date=timezone.now().date()
).count()
```

## Next Steps

### Immediate
1. Run migration
2. Test locally (if possible)
3. Deploy to Render

### Future Enhancements
- Email code to user (optional)
- Import user's actual FPL team
- Compare wildcard vs current team
- Team comparison view
- Public team leaderboard

## Testing

### Test Flow
1. Visit `/wildcard/`
2. Open browser DevTools → Application → Local Storage
3. Verify `wildcard_code` and `wildcard_draft` are saved
4. Refresh page → Team should restore
5. Click "Save & Share" → Should show modal with code
6. Visit `/wildcard/{code}/` → Team should load

### Database Check
```bash
# SSH into Render
cd django_etl
python manage.py shell

from etl.models import WildcardSimulation
WildcardSimulation.objects.all()
```

## Notes

- localStorage limit: 5-10MB (enough for 1000+ teams)
- Session persists: Forever (until user clears browser)
- Database grows: Only when users click "Save & Share"
- Code format: `WC-{6 random chars}` (e.g., WC-7F2A9C)

## Support

Need help? Check:
1. Browser console for JavaScript errors
2. Django logs for API errors
3. localStorage in DevTools

---

Built with ❤️ for FPL Pulse
