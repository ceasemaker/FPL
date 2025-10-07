# 🚨 URGENT: Fix Whitenoise Error - Render Configuration

## The Problem
Render is still using OLD build commands stored in the Dashboard, ignoring your `render.yaml` file.

## The Root Cause
When you manually created the web service, Render stored these commands:
- **Build Command:** `pip install -r requirements.txt; pip install gunicorn`
- **Start Command:** `cd django_etlpython manage.py migrategunicorn...`

These stored commands take precedence over `render.yaml`. Even though we updated `render.yaml`, Render won't use it unless you:
1. Create a NEW service via Blueprint, OR
2. Clear the old commands in Dashboard settings

## ✅ SOLUTION (Choose ONE)

### Option 1: Update Existing Service (EASIER - 2 minutes)

Go to your Render Dashboard and manually update both commands:

1. **Navigate to Service:**
   - Go to: https://dashboard.render.com
   - Click on your `fpl-pulse-web` service

2. **Update Build Command:**
   - Click **Settings** → **Build & Deploy**
   - Find "Build Command" field
   - **REPLACE WITH:** `./build.sh`
   - (Current wrong value: `pip install -r requirements.txt; pip install gunicorn`)

3. **Update Start Command (if not already done):**
   - Same section: "Start Command"
   - **REPLACE WITH:** `./start-django-only.sh`
   - (Current wrong value: `cd django_etl python manage.py migrate gunicorn...`)

4. **Save and Deploy:**
   - Click "Save Changes" button
   - Click "Manual Deploy" → "Deploy latest commit"

5. **Watch Build Logs:**
   You should see:
   ```
   ==> Running build command './build.sh'
   🚀 Starting build process...
   📦 Installing from requirements.txt...
   📦 Installing critical packages explicitly...
   whitenoise (6.6.0)  ← THIS SHOULD APPEAR!
   ```

---

### Option 2: Create New Service via Blueprint (CLEAN START - 5 minutes)

This uses your `render.yaml` automatically:

1. **In Render Dashboard:**
   - Go to: https://dashboard.render.com/blueprints
   - Click "New Blueprint Instance"

2. **Connect Repository:**
   - Select your GitHub repository
   - Click "Connect"

3. **Name and Deploy:**
   - Give it a name (or use defaults)
   - Click "Apply"
   - Render will read `render.yaml` and create services automatically

4. **Update Environment Variables:**
   - Add `RAPIDAPI_KEY` (your SofaSport API key)
   - Add `RAPIDAPI_HOST` = `sofasport.p.rapidapi.com`
   - `DATABASE_URL` and `REDIS_URL` should auto-populate

---

## 🔍 Verification

After deploying, check build logs for these SUCCESS indicators:

```bash
==> Running build command './build.sh'
🚀 Starting build process...
🐍 Python version: Python 3.11.x
📦 Installing from requirements.txt...
📦 Installing critical packages explicitly...
📋 Verifying installed packages:
celery                5.3.x
django-cors-headers   4.3.x
gunicorn             21.2.x
psycopg2-binary      2.9.x
redis                 5.0.x
supervisor            4.2.x
whitenoise            6.6.x  ← MUST BE HERE!
🗄️  Running database migrations...
📊 Collecting static files...
✅ Build completed successfully!
```

Then check deploy logs:

```bash
==> Running './start-django-only.sh'
🚀 Starting Django with Gunicorn...
Starting gunicorn 21.2.x
Listening at: http://0.0.0.0:10000
Booting worker with pid: 123
```

---

## 📁 What We've Fixed

### ✅ Correct Files (Already Pushed to GitHub)

1. **`render.yaml`** - Updated to use scripts:
   ```yaml
   buildCommand: ./build.sh
   startCommand: ./start-django-only.sh
   ```

2. **`build.sh`** - Installs from correct requirements.txt:
   ```bash
   python -m pip install -r django_etl/requirements.txt
   python -m pip install whitenoise gunicorn supervisor celery[redis]
   ```

3. **`start-django-only.sh`** - Runs Django only (for testing):
   ```bash
   cd django_etl
   exec gunicorn fpl_platform.wsgi:application --bind 0.0.0.0:${PORT:-10000}
   ```

4. **`django_etl/requirements.txt`** - Contains all dependencies:
   ```
   whitenoise>=6.6
   gunicorn>=21.2
   celery>=5.3
   redis>=5.0
   supervisor>=4.2
   Django>=4.2
   ```

5. **`django_etl/fpl_platform/settings.py`** - Whitenoise configured:
   ```python
   MIDDLEWARE = [
       "django.middleware.security.SecurityMiddleware",
       "whitenoise.middleware.WhiteNoiseMiddleware",  # ← Correct!
       ...
   ]
   STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
   ```

### ❌ What Render Is STILL Doing Wrong

Render Dashboard has OLD commands stored that ignore your correct `render.yaml`.

---

## 🎯 Expected Outcome

After you update the Build Command in Render Dashboard:

1. ✅ Build succeeds with whitenoise installed
2. ✅ Django starts with Gunicorn
3. ✅ Service goes "Live" (green status)
4. ✅ You can access: `https://your-service.onrender.com/api/players/`

---

## 🔄 After Django Works: Add Celery (Optional)

Once Django is working, you can add Celery back:

1. Change Start Command to: `./start-prod.sh`
2. This uses supervisord to run:
   - Django (Gunicorn)
   - Celery Worker
   - Celery Beat (scheduled tasks)

---

## 📞 Still Having Issues?

If you update the Build Command and STILL see whitenoise errors:

1. Share the **full build logs** from Render
2. Check that build logs show: `==> Running build command './build.sh'`
3. Verify build logs list whitenoise in installed packages
4. If whitenoise IS installed but Django can't import it, check Python version mismatch

---

## 🎓 Why This Happened

Render has TWO ways to configure services:

1. **Dashboard Settings** (stored in Render's database)
2. **`render.yaml`** (stored in your repo)

Dashboard settings take precedence! You must either:
- Clear dashboard settings (then Render uses render.yaml), OR
- Update dashboard settings manually to match render.yaml

We've been updating render.yaml, but Render kept using the old dashboard settings.

**The fix:** Update the Build Command in Dashboard Settings → Build & Deploy.
