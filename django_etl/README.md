# Django ETL Pipeline for Fantasy Premier League

This Django project provides an ETL pipeline that loads data from the Fantasy Premier League API into a PostgreSQL database.

## Features

- Sync teams, athletes, fixtures, player summaries, gameweek stats, event status, and set-piece notes.
- Stores raw API payload snapshots for auditing and replay.
- Management command `run_fpl_etl` orchestrates the whole pipeline.
- Docker image that runs the ETL in a loop, suitable for Render.com deployment.
- Landing snapshot API (`/api/landing/`) for the animated front-end dashboard.

## Getting Started

### Environment Variables

Create a `.env` file (or set environment variables) with at least:

```
POSTGRES_USER=fpl_user
POSTGRES_PASSWORD=fpl_password
POSTGRES_DB=fpl_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=False
```

### Run Locally (without Docker)

```bash
cd django_etl
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py run_fpl_etl
```

If you want to expose the landing snapshot API for the front-end, run the Django development server in a separate shell:

```bash
python manage.py runserver 0.0.0.0:8000
```

### Docker Build & Run

```bash
cd django_etl
docker build -t fpl-django-etl .
docker run --env-file ../local.env --network fpl_network fpl-django-etl
```

Ensure the PostgreSQL service is accessible using the configured credentials.

To serve the API alongside the ETL loop, create a second service/container (or Render background worker) that runs `python manage.py runserver` against the same codebase and database.

### Tests

```bash
python manage.py test
```

## Render Deployment

1. Build the Docker image using this `Dockerfile`.
2. Configure environment variables in Render.
3. Set the start command to `python manage.py run_fpl_etl --loop`.
