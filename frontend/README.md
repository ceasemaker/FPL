# AeroFPL Landing Page

This Vite + React front-end renders the Fantasy Premier League analytics landing page with animated insights powered by [anime.js](https://animejs.com/).

## Features

- Neon-inspired dark theme with animated hero metric, movers ticker, and momentum grid.
- Live data fetch from the Django ETL API endpoint at `/api/landing/`.
- Auto-generated player imagery sourced from Premier League media IDs.
- Production build via `npm run build` (output in `dist/`).

## Prerequisites

- Node.js 18+
- The Django ETL service running with the `/api/landing/` endpoint available. During local development, run `python manage.py runserver 0.0.0.0:8000` inside the `django_etl` project or add a dedicated web service to Docker Compose.

## Local Development

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server (default `http://localhost:5173`) proxies `/api` requests to `http://localhost:8000`, so the Django server must be reachable at that address.

## Run Everything in Docker

The project ships with a Compose stack that spins up Postgres, Redis, the Django ETL loop, a dedicated Django web service for the `/api/landing/` endpoint, and the Vite dev server.

```bash
cd /Users/nyashamutseta/Desktop/personal/FPL
DOCKER_CONFIG=/tmp/docker-config /usr/local/bin/docker compose up --build frontend
```

- The `frontend` service exposes the Vite dev server on [http://localhost:5173](http://localhost:5173).
- The `django_web` service publishes the landing API at [http://localhost:8000/api/landing/](http://localhost:8000/api/landing/).
- Source files in `frontend/` are mounted into the container, so edits hot-reload in the browser.

When finished, stop the stack with:

```bash
DOCKER_CONFIG=/tmp/docker-config /usr/local/bin/docker compose down
```

## Production Build

```bash
cd frontend
npm run build
```

The optimized bundle is emitted to `frontend/dist`. You can preview the production build locally with `npm run preview`.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Override proxy target/production API base URL | `http://localhost:8000` |
| `VITE_API_LANDING_URL` | Override landing endpoint URL (when serving statically) | `/api/landing/` |

When serving the static `dist` bundle behind a CDN, set `VITE_API_LANDING_URL` to the fully qualified API URL during build (e.g., `npm run build -- --base=/ --mode production` with `.env.production`).
