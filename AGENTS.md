# Repository Guidelines

## Project Structure & Module Organization
- `django_etl/`: Django 4.2 backend, ETL services, Celery tasks, and API endpoints (`etl/` app, `fpl_platform/` settings).
- `frontend/`: Vite + React + TypeScript client; pages in `frontend/src/pages/`, shared UI in `frontend/src/components/`.
- `sofa_sport/` and `django_etl/sofa_sport/`: SofaSport ETL scripts and mappings (JSON files under `mappings/`).
- `epl-etl/`, `etl-pipeline/`, `python-proj/`: stand-alone ETL and data scripts.
- `Docker/`, `postgres/`, `docker-compose.yml`: local container orchestration and database setup.
- Root docs like `ENV_VARIABLES.md`, `CELERY_SETUP.md`, and deployment checklists describe environment and ops.

## Build, Test, and Development Commands
- `./start.sh`: full local stack via Docker Compose; includes health checks and API probes.
- `docker-compose up -d --build`: build and run services without the helper script.
- `./start-django-only.sh`: run Django + Gunicorn only (useful for API testing).
- `./start-prod.sh`: run supervisord (Django + Celery worker/beat) for production-like flow.
- `cd django_etl && python manage.py runserver 0.0.0.0:8000`: local Django dev server.
- `cd frontend && npm install && npm run dev`: run the Vite dev server on `http://localhost:5173`.

## Coding Style & Naming Conventions
- Python: 4-space indentation, snake_case for modules/functions, Django conventions for apps/models.
- Frontend: 2-space indentation, PascalCase for components (e.g., `PlayersPage.tsx`), `useX` for hooks.
- Keep file naming consistent with existing folders (pages vs components) and avoid introducing new casing schemes.
- No enforced formatter/linter; match surrounding style and keep imports sorted manually.

## Testing Guidelines
- Django tests live in `django_etl/etl/tests/` (e.g., `test_parsers.py`).
- Run: `cd django_etl && python manage.py test etl`.
- No frontend test runner is configured; add one only if needed for new UI logic.
- No explicit coverage requirement in the repo—focus on critical ETL parsing and API behavior.
 - Date-only fields (e.g., `Athlete.birth_date`) stay as `DateField` values; use UTC normalization only for `DateTimeField` via `_parse_datetime`.

## Commit & Pull Request Guidelines
- Commit history uses short, imperative messages with optional prefixes like `feat:`, `fix:`, `refactor:`, `remove:`.
- Keep commits focused; note user-facing changes in the message when applicable.
- PRs should include a brief summary, key files touched, and test commands run.
- Include screenshots or GIFs for UI changes and link any related issues/tickets.

## Configuration & Secrets
- Use `local.env` and `ENV_VARIABLES.md` for required settings; never commit secrets.
- For Django settings, prefer `DJANGO_*` and `SECRET_KEY` environment variables as documented.
 - Do not add new Render services without explicit approval to avoid increasing hosting costs.
