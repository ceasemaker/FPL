# ✅ Pre-Deployment Checklist

## 🎯 Quick Reference

Before you deploy to Render, check off each item below.

---

## 1️⃣ Code Changes ✅

- [x] **Radar chart component** - Created and working locally
- [x] **Player comparison page** - Shows overlapping radar charts
- [x] **Error handling** - Players without data handled gracefully
- [x] **Django API endpoints** - 5 SofaSport endpoints created
- [x] **Celery tasks** - 5 scheduled tasks configured (daily)
- [x] **supervisord.conf** - Configured to run all services in one
- [x] **build.sh** - Build script ready
- [x] **start-prod.sh** - Start script ready
- [x] **WhiteNoise** - Added for static file serving
- [x] **Production dependencies** - gunicorn, supervisor, whitenoise added

---

## 2️⃣ Local Testing ✅

Before deploying, verify these work locally:

### Django API:
- [ ] `http://localhost:8000/api/players/` - Returns player list
- [ ] `http://localhost:8000/api/sofasport/player/16/radar/` - Returns Saka's radar data
- [ ] `http://localhost:8000/api/sofasport/compare/radar/?player_ids=16,23` - Compares 2 players

### Frontend:
- [ ] Click any player → Modal opens
- [ ] Radar chart appears in modal (if player has data)
- [ ] No errors for players without radar data
- [ ] Compare 2+ players → Overlapping radar charts appear
- [ ] Radar chart legend shows correct player names/colors

### Celery:
- [ ] `docker logs fpl_celery_worker` - Shows "ready"
- [ ] `docker logs fpl_celery_beat` - Shows scheduled tasks
- [ ] No errors in Celery logs

---

## 3️⃣ Environment Variables 📝

### Have These Ready:

#### From RapidAPI:
- [ ] **RAPIDAPI_KEY** - Your SofaSport API key
  - Get from: https://rapidapi.com/fluis.lacasse/api/sofasport/
  - Free tier available

#### From Your Render Dashboard:
- [ ] **DATABASE_URL** - PostgreSQL Internal Connection URL
  - Location: Dashboard → PostgreSQL → Info → Internal Database URL
  
- [ ] **REDIS_URL** - Redis Internal Connection URL
  - Location: Dashboard → Redis → Info → Internal Redis URL
  
- [ ] **Frontend URL** - For CORS configuration
  - Format: `https://your-frontend.onrender.com`

#### Generate New:
- [ ] **DJANGO_SECRET_KEY** - New secret key (don't reuse old one!)
  - Generate with: `python -c "import secrets; print(secrets.token_urlsafe(50))"`

---

## 4️⃣ Render Dashboard Setup 🎛️

### Your Django Web Service:

1. **Build Command** (update to):
   ```bash
   ./build.sh
   ```

2. **Start Command** (update to):
   ```bash
   ./start-prod.sh
   ```

3. **Environment Variables** (add these):
   ```
   DJANGO_SECRET_KEY=<your-generated-key>
   DEBUG=false
   DJANGO_ALLOWED_HOSTS=<your-service>.onrender.com
   DATABASE_URL=<from-postgres>
   REDIS_URL=<from-redis>
   RAPIDAPI_KEY=<from-rapidapi>
   RAPIDAPI_HOST=sofasport.p.rapidapi.com
   CORS_ALLOWED_ORIGINS=https://<your-frontend>.onrender.com
   TZ=Europe/London
   C_FORCE_ROOT=true
   ```

4. **Connected Services** (verify):
   - [ ] PostgreSQL database connected
   - [ ] Redis instance connected

### Your Frontend Service:

1. **Environment Variable** (verify):
   ```
   VITE_API_URL=https://<your-django-service>.onrender.com
   ```

2. **Build Command** (should already be):
   ```bash
   npm run build
   ```

---

## 5️⃣ Pre-Push Checklist 🚀

- [ ] All changes committed locally
- [ ] No sensitive data in code (keys, passwords, etc.)
- [ ] `.env` files NOT committed (in `.gitignore`)
- [ ] `build.sh` is executable (`chmod +x`)
- [ ] `start-prod.sh` is executable (`chmod +x`)
- [ ] Local Docker tests pass
- [ ] No merge conflicts

### Final Commands:
```bash
# Review changes
git status
git diff

# Commit
git add .
git commit -m "Add Celery scheduling, radar charts, and Render deployment config"

# Push
git push origin main
```

---

## 6️⃣ Deployment Day 🎉

### Step 1: Push Code
- [ ] Code pushed to GitHub
- [ ] Branch is `main` (or your deployment branch)

### Step 2: Update Render Service
- [ ] Navigate to Django Web Service in Render Dashboard
- [ ] Update Build Command
- [ ] Update Start Command  
- [ ] Add/Update Environment Variables
- [ ] Click "Manual Deploy" → "Deploy latest commit"

### Step 3: Monitor Deployment
- [ ] Watch build logs
- [ ] Look for "✅ Build completed successfully!"
- [ ] Wait for service to start

### Step 4: Verify Services Started
Look for these in logs:
- [ ] `gunicorn: Listening at: http://0.0.0.0:10000`
- [ ] `celery@... ready.`
- [ ] `celerybeat: Starting...`

---

## 7️⃣ Post-Deployment Verification ✅

### Test API Endpoints:

```bash
# Replace YOUR_SERVICE with your service name

# Basic API
curl https://YOUR_SERVICE.onrender.com/api/players/ | head -20

# Radar chart
curl https://YOUR_SERVICE.onrender.com/api/sofasport/player/16/radar/

# Compare players
curl 'https://YOUR_SERVICE.onrender.com/api/sofasport/compare/radar/?player_ids=16,23'
```

Expected:
- [ ] All endpoints return 200 OK
- [ ] Radar endpoint returns JSON with attributes
- [ ] Compare endpoint returns multiple players

### Test Frontend:

1. Open your frontend URL
2. **Players Page:**
   - [ ] Players list loads
   - [ ] Can search/filter players
3. **Player Modal:**
   - [ ] Click a player → Modal opens
   - [ ] Player info displays
   - [ ] Radar chart appears (for players with data)
   - [ ] No errors for players without data
4. **Compare Page:**
   - [ ] Select 2+ players
   - [ ] Click "Compare"
   - [ ] Comparison page opens
   - [ ] Radar charts overlap correctly
   - [ ] Legend shows player names
   - [ ] Stats table displays

### Check Celery:

- [ ] In Render logs, search for "celery-worker"
- [ ] Should see: "ready" message
- [ ] In logs, search for "celery-beat"  
- [ ] Should see: "Starting..." message
- [ ] Verify scheduled tasks listed

---

## 8️⃣ Common Issues & Quick Fixes 🔧

### "Build failed" ❌
- **Check:** Is `build.sh` in root directory?
- **Check:** Are dependencies in `django_etl/requirements.txt`?
- **Fix:** Review build logs for specific error

### "Service won't start" ❌
- **Check:** Is `start-prod.sh` executable?
- **Check:** Is `supervisord.conf` in correct location?
- **Fix:** Check Start Command in Render dashboard

### "Database connection error" ❌
- **Check:** Is `DATABASE_URL` set?
- **Check:** Is PostgreSQL connected to web service?
- **Fix:** Verify internal connection URL

### "Celery not starting" ❌
- **Check:** Is `REDIS_URL` set?
- **Check:** Is Redis connected to web service?
- **Fix:** Look for "celery" errors in logs

### "CORS error on frontend" ❌
- **Check:** Is `CORS_ALLOWED_ORIGINS` set?
- **Check:** Does it match your frontend URL exactly?
- **Fix:** Format should be `https://your-frontend.onrender.com` (no trailing slash)

### "Radar chart not showing" ❌
- **Check:** Does player have SofaSport data?
- **Check:** Is `RAPIDAPI_KEY` set correctly?
- **Fix:** Test API endpoint directly: `/api/sofasport/player/{id}/radar/`

---

## 9️⃣ Rollback Plan 🔄

If something goes wrong:

### Quick Rollback:
1. In Render Dashboard → Your Service
2. Click "Rollbacks" tab
3. Select previous working deployment
4. Click "Rollback"

### Manual Fix:
1. In Render Dashboard → Shell tab
2. Run diagnostics:
   ```bash
   cd django_etl
   python manage.py check
   python manage.py showmigrations
   celery -A fpl_platform inspect active
   ```

---

## 🎉 Success Indicators

You're done when:

- ✅ Build completed without errors
- ✅ Service shows "Live" status in Render
- ✅ All 3 logs visible (gunicorn, celery-worker, celery-beat)
- ✅ API endpoints return data
- ✅ Frontend loads without errors
- ✅ Radar charts display in player modal
- ✅ Player comparison works
- ✅ No CORS errors in browser console
- ✅ Celery tasks registered (check logs)
- ✅ **No increase in Render costs!**

---

## 📚 Documentation Reference

- **DEPLOY_NOW.md** - Step-by-step deployment guide
- **DEPLOYMENT_SUMMARY.md** - Complete overview of changes
- **.env.render** - Environment variable template
- **RENDER_DEPLOYMENT.md** - Detailed Render configuration guide

---

## 🎯 Final Check

Before clicking "Deploy":

- [ ] Read through this entire checklist
- [ ] All checkboxes above are checked
- [ ] Environment variables are ready
- [ ] Local tests pass
- [ ] Code is pushed to GitHub
- [ ] You have a rollback plan

**Ready?** Let's deploy! 🚀

---

## 📝 Notes

- **Cost:** No additional costs - using existing services
- **Downtime:** Minimal (< 2 minutes during deploy)
- **Data:** No data loss (migrations are additive)
- **Rollback:** Available instantly if needed

**You got this!** 💪
