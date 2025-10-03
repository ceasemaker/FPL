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
