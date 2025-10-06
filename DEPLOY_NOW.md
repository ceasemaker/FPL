# 🚀 Quick Deployment Guide to Render

## Summary

Deploy your Django + Celery + Frontend app to Render with NO pricing changes to existing services.

---

## 🎯 What You Need to Do

### 1. Update Your Existing Django Web Service

In your Render Dashboard, go to your **existing Django web service** and update:

#### **Build Command:**
```bash
./build.sh
```

#### **Start Command:**
```bash
./start-prod.sh
```

#### **Add Environment Variables:**
Copy from `.env.render` file and add to your service:

**Required:**
- `RAPIDAPI_KEY` - Your SofaSport API key from RapidAPI
- `CORS_ALLOWED_ORIGINS` - Your frontend URL (e.g., `https://your-frontend.onrender.com`)

**Auto-populated** (if you have PostgreSQL and Redis connected):
- `DATABASE_URL` - Internal database URL
- `REDIS_URL` - Internal Redis URL

**Optional** (use defaults if not set):
- `DJANGO_SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `DEBUG` - Set to `false`
- `TZ` - Set to `Europe/London`

---

### 2. Update Your Frontend (If Needed)

#### **Environment Variable:**
```bash
VITE_API_URL=https://<your-django-service>.onrender.com
```

---

### 3. Deploy

1. Commit and push your changes:
   ```bash
   git add .
   git commit -m "Add Celery scheduling and radar chart features"
   git push origin main
   ```

2. In Render Dashboard:
   - Your Django service should auto-deploy (if auto-deploy is enabled)
   - OR click "Manual Deploy" → "Deploy latest commit"

3. Watch the logs to ensure:
   - ✅ Build completes successfully
   - ✅ Migrations run
   - ✅ Static files collected
   - ✅ Gunicorn starts
   - ✅ Celery worker starts
   - ✅ Celery beat starts

---

## ✅ Verify It's Working

### Check the Logs

Look for these lines in your web service logs:

```
✅ Build completed successfully!
gunicorn: Listening at: http://0.0.0.0:10000
celery@hostname ready.
celerybeat: Starting...
```

### Test API Endpoints

```bash
# Basic API
curl https://your-service.onrender.com/api/players/

# Radar chart for player 16 (Saka)
curl https://your-service.onrender.com/api/sofasport/player/16/radar/

# Compare two players
curl 'https://your-service.onrender.com/api/sofasport/compare/radar/?player_ids=16,23'
```

### Test Frontend

1. Open your frontend URL
2. Go to Players page
3. Click any player
4. You should see the radar chart in the modal!
5. Click "Compare" for 2+ players
6. You should see overlapping radar charts!

---

## 📅 Scheduled Tasks (Daily Updates)

Your Celery Beat scheduler will run these tasks **once per day**:

| Day | Time (GMT) | Task |
|-----|-----------|------|
| Monday | 2 AM | Update fixture mappings |
| Tuesday | 3 AM | Update lineups |
| Tuesday | 4 AM | Collect heatmaps |
| Wednesday | 2 AM | Update season stats |
| Wednesday | 3 AM | Update radar attributes |

**No manual intervention needed!**

---

## 🐛 Troubleshooting

### "Module not found" errors
- Check that `build.sh` ran successfully
- Verify `requirements.txt` is in `django_etl/` directory

### Celery not starting
- Check `REDIS_URL` is set correctly
- Look for errors in logs containing "celery"

### Migrations fail
- Check `DATABASE_URL` is set correctly
- Try running migrations manually in Render Shell:
  ```bash
  cd django_etl && python manage.py migrate
  ```

### Static files 404
- Run: `cd django_etl && python manage.py collectstatic --noinput`
- Check `STATIC_ROOT` in settings.py

### CORS errors
- Add your frontend URL to `CORS_ALLOWED_ORIGINS`
- Format: `https://your-frontend.onrender.com` (no trailing slash)

---

## 💰 Cost Reminder

**NO CHANGES to your current pricing!**

- Your existing Django service: (same price)
- Your existing Frontend service: (same price)
- Your existing PostgreSQL: (same price)
- Your existing Redis: (same price)

We're just adding features to your **existing services**, not creating new ones.

---

## 🎉 That's It!

You've deployed:
- ✅ Radar chart visualization
- ✅ Player comparison with overlapping charts
- ✅ Automated daily data updates
- ✅ Django + Celery in one service (cost-efficient!)

All with **zero pricing changes!** 🚀
