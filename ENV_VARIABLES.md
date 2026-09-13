# Environment Variables Configuration

This document explains how environment variables are configured for local development vs Render deployment.

## Philosophy

- **Local Development**: Use `.env` file (git-ignored) based on `.env.example`
- **Render Deployment**: All environment variables are set via Render dashboard or `render.yaml`
- **No Hardcoded Secrets**: All sensitive data comes from environment variables

## Files Overview

### `.env.example`
Template file with dummy values showing what environment variables are needed. This file IS committed to git as documentation.

**Usage:**
```bash
cp .env.example .env
# Edit .env with your local values
```

### `.env` (git-ignored)
Your actual local environment variables with real values. This file is NEVER committed to git.

### `render.yaml`
Deployment configuration that tells Render:
- What services to create
- What environment variables to set
- How to build and run each service

## Environment Variable Sources

### Django Settings (`django_etl/fpl_platform/settings.py`)

The settings file reads from environment variables with fallbacks:

```python
# Example: Reads SECRET_KEY, falls back to DJANGO_SECRET_KEY, then to default
SECRET_KEY = os.getenv("SECRET_KEY", os.getenv("DJANGO_SECRET_KEY", "insecure-default"))
```

### Supported Variable Names

The code supports both Render-style and custom environment variable names:

| Setting | Primary Name | Fallback Name | Default |
|---------|-------------|---------------|---------|
| Secret Key | `SECRET_KEY` | `DJANGO_SECRET_KEY` | (insecure default) |
| Debug Mode | `DEBUG` | `DJANGO_DEBUG` | `False` |
| Allowed Hosts | `ALLOWED_HOSTS` | `DJANGO_ALLOWED_HOSTS` | `*` |
| Database | `DATABASE_URL` | Individual vars | (see below) |

### Database Configuration

Two ways to configure the database:

**Option 1: DATABASE_URL (Render's default)**
```
DATABASE_URL=postgresql://user:password@host:port/dbname
```

**Option 2: Individual variables**
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fpl_db
POSTGRES_USER=fpl_user
POSTGRES_PASSWORD=your-password
```

The code automatically parses `DATABASE_URL` if present, otherwise uses individual variables.

### Redis Configuration

Supports both authenticated and non-authenticated Redis:

```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=optional-password  # Leave empty for no auth
REDIS_DB=0
```

The code builds the correct Redis URL based on whether a password is set.

### CORS Configuration

For frontend-backend communication:

```
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://yourfrontend.com
```

Multiple origins separated by commas.

### Fixture Odds (key-free by default)

The fixture-odds job uses Sofascore's public website API by default, so no API
key is required:

```bash
SOFASCORE_ODDS_SOURCE=public
SOFASCORE_PUBLIC_BASE_URL=https://api.sofascore.com/api/v1
SOFASCORE_TOURNAMENT_ID=17
SOFASCORE_SEASON_ID=96668
SOFASCORE_RATE_LIMIT_DELAY=12.5
SOFASCORE_MAX_CALLS_PER_DAY=40
SOFASCORE_ODDS_MAX_AGE_HOURS=36
```

The Sofa identifiers are shared with the previous RapidAPI wrapper. Premier
League's `unique_tournament_id` remains `17`; its season ID is `96668` for
2026/27 (`76986` was 2025/26). The public API can block some IP addresses, so
the machine or container running the worker should be smoke-tested directly.

Odds collection is once daily. Every attempted public request is recorded in
`raw_endpoint_snapshots` before transmission, requests start at least 12
seconds apart (no more than five per minute), and a completed/blocked/capped
run will not make more calls until the next local calendar day. These rules are
inside the collection script, so they also apply to manual runs and Docker—not
only to the Celery schedule. `SOFASCORE_MAX_CALLS_PER_DAY` is an emergency cap,
not a target.

The current tally can be read without contacting Sofascore:

```bash
cd django_etl
python sofa_sport/scripts/fetch_fixture_odds.py --status
```

The prediction job removes the bookmaker margin from 1X2, totals, and BTTS
prices. It infers the match scoring environment from the over-2.5 probability,
then applies a bounded, position-specific correction against the FPL fixture
rating already present in the model. Missing odds leave the original model
prediction unchanged.
Stored prices older than `SOFASCORE_ODDS_MAX_AGE_HOURS` are ignored so a
blocked feed cannot silently influence recommendations for days afterward.

The old paid route remains available as an explicit fallback:

```bash
SOFASCORE_ODDS_SOURCE=rapidapi
SOFASPORT_API_HOST=sofasport.p.rapidapi.com
SOFASPORT_API_KEY=your-key
```

### Football-Data Historical Odds

At 06:15 daily, Celery downloads the current Premier League CSV from
`football-data.co.uk` in one request. The season folder is derived locally
(`2627` for 2026/27), so no index-page request is needed. The compact parsed
snapshot is stored in `raw_endpoint_snapshots`, replacing the prior snapshot
instead of appending the whole growing season every day.

This source currently contains completed matches only. It is used for
historical calibration and backtesting; it is never substituted into live
pre-deadline fixture recommendations. The daily attempt is claimed before the
request, so a failed request or container restart will not cause repeated
downloads that day.

Manual command:

```bash
cd django_etl
python manage.py sync_football_data_odds
```

## Render Deployment

When deploying to Render, all environment variables are configured in `render.yaml`:

```yaml
envVars:
  - key: SECRET_KEY
    generateValue: true  # Render auto-generates secure value
  
  - key: DATABASE_URL
    fromDatabase:
      name: fpl-pulse-db
      property: connectionString  # Render auto-fills from database
  
  - key: REDIS_HOST
    fromService:
      type: redis
      name: fpl-pulse-redis
      property: host  # Render auto-fills from Redis service
```

### Auto-Generated Variables

Render automatically sets:
- `SECRET_KEY` - Secure random string
- `DATABASE_URL` - From PostgreSQL database
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` - From Redis service
- `PORT` - Port number for the service

### Manual Variables

You can also set variables manually in Render dashboard:
1. Go to your service
2. Click "Environment"
3. Add/edit variables
4. Service auto-redeploys with new values

## Security Best Practices

### ✅ DO:
- Use `.env.example` to document required variables
- Keep `.env` in `.gitignore`
- Use strong, random values for `SECRET_KEY`
- Set `DEBUG=False` in production
- Restrict `ALLOWED_HOSTS` to your actual domains
- Use environment-specific CORS origins

### ❌ DON'T:
- Commit `.env` files to git
- Hardcode secrets in code
- Use default/insecure secret keys in production
- Set `DEBUG=True` in production
- Allow `ALLOWED_HOSTS=*` in production

## Testing Environment Variables

### Local Testing

```bash
# Check if environment variables are loaded
python manage.py shell

>>> import os
>>> os.getenv('SECRET_KEY')
'your-secret-key'

>>> from django.conf import settings
>>> settings.DEBUG
False
```

### Render Testing

In Render dashboard:
1. Go to your service
2. Click "Shell" tab
3. Run same commands as above

## Troubleshooting

### "SECRET_KEY not set"
- **Local**: Ensure `.env` file exists and has `SECRET_KEY=...`
- **Render**: Check Environment tab, SECRET_KEY should be auto-generated

### "Database connection failed"
- **Local**: Check `POSTGRES_*` variables in `.env`
- **Render**: Ensure `DATABASE_URL` is set from database service

### "Redis connection failed"
- **Local**: Check `REDIS_HOST` and `REDIS_PORT` in `.env`
- **Render**: Ensure Redis service is running and env vars are linked

### "CORS errors"
- Check `CORS_ALLOWED_ORIGINS` includes your frontend URL
- Ensure no trailing slashes in URLs
- Verify frontend is using correct backend URL

## Adding New Environment Variables

### Step 1: Add to `.env.example`
```bash
# New Feature Configuration
NEW_API_KEY=your-api-key-here
```

### Step 2: Update Django Settings
```python
NEW_API_KEY = os.getenv("NEW_API_KEY", "")
```

### Step 3: Update `render.yaml` (if needed)
```yaml
- key: NEW_API_KEY
  value: actual-production-value
```

### Step 4: Update this documentation
Add the new variable to the relevant sections above.

## Reference

- `.env.example` - Template with all required variables
- `django_etl/fpl_platform/settings.py` - How variables are read
- `render.yaml` - Render deployment configuration
- `.gitignore` - Ensures `.env` is never committed
