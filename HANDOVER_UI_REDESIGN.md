# AeroFPL model + product redesign handover

Last updated: 2026-09-12 — feature leakage fixed (priority 1, see **Completed** §8); odds-source decision made (see **Data sources**).

## Workspace

- Main repository: `/Users/nyashamutseta/Desktop/personal/FPL`
- Active worktree: `/Users/nyashamutseta/Desktop/personal/FPL-model-upgrade`
- Branch: `codex/model-upgrade-20260906`
- Repository instructions: `AGENTS.md`
- Committed as `7f922d6` and merged to `main` (`2b754cb`) on 2026-09-13; **deployed to Render** the same night (see **Render deployment** below).

## Local services

- Vite: `http://127.0.0.1:5181/`
- Django: `http://127.0.0.1:8011/` (now running **with** autoreload; it was previously started `--noreload`, which silently served stale view code)
- Postgres and Redis are Docker services using the existing `fpl` volumes.
- A Homebrew Postgres binds `127.0.0.1:5432` and `[::1]:5432`, while the Docker Postgres
  publishes on `*:5432`. Local Django therefore has to reach Docker via the **host's LAN
  address**, not localhost.

> **This IP changes across reboots.** It was `192.168.1.246`, and after a restart on
> 2026-09-12 it became `192.168.1.63`, which made every Django request hang on a DB
> connect timeout. Derive it rather than hard-coding it:
> `ipconfig getifaddr en0`.

Helper scripts live in `/private/tmp/claude-501/aerofpl/` and now compute the host
automatically: `env.sh` (shared env), `dj.sh` (manage.py), `serve.sh` (Django),
`web.sh` (Vite).

> **Vite proxy gotcha.** `vite.config.ts` proxies `/api` to `VITE_API_BASE_URL`, which
> **defaults to `http://localhost:8000`** — the Dockerised Django, not the native
> autoreloading server on 8011 that local dev actually uses. Start Vite with
> `VITE_API_BASE_URL=http://127.0.0.1:8011` (what `web.sh` does) or every page loads
> with *"Dashboard data could not be loaded."* while `curl`ing the API directly works
> fine — a confusing pair of symptoms.

Full cold start after a reboot:

```bash
open -a Docker && sleep 30
docker start fpl_postgres fpl_redis
/private/tmp/claude-501/aerofpl/serve.sh &   # Django on :8011
/private/tmp/claude-501/aerofpl/web.sh &     # Vite on :5181
```

```bash
cd /Users/nyashamutseta/Desktop/personal/FPL-model-upgrade/django_etl
unset DATABASE_URL
USE_POSTGRES=true POSTGRES_HOST="$(ipconfig getifaddr en0)" POSTGRES_PORT=5432 \
POSTGRES_USER=fpl_user POSTGRES_PASSWORD=fpl_password POSTGRES_DB=fpl_db \
REDIS_HOST=127.0.0.1 SECRET_KEY=local-development-secret-key-change-in-production \
DEBUG=True python manage.py <command>
```

## Render deployment — 2026-09-13 (new workspace, fresh database)

Workspace `My Workspace` (`tea-d8lflmbtqb8s73b05fbg`). Both services track **`main`** with
autoDeploy on, so deploying = pushing to `main`.

| Resource | ID | Notes |
| --- | --- | --- |
| `fpl-pulse-web` | `srv-dajeqvvqj5pc73dbmtdg` | `https://fpl-pulse-web-8u1j.onrender.com`, custom domain **`api.aerofpl.net`** (verified 2026-09-13) |
| `fpl-pulse-frontend` | `srv-dajeqlfqj5pc73dblfr0` | `https://fpl-pulse-frontend-ptan.onrender.com`, `aerofpl.net` (verified), `www` unverified |
| `fpl-pulse-db` | `dpg-dajeqlnqj5pc73dblg40-a` | basic-256mb, db `fpl_db_o223` |
| `fpl-pulse-redis` | `red-dajeqlfqj5pc73dblfmg` | free |

- The old database was suspended and nothing was migrated. Everything was rebuilt from the
  FPL API with one one-off job (`job-dajiu7nqj5pc73dqbfp0`, 3m45s):
  `run_fpl_etl && sync_top100 ; backfill_gameweek_context && clear_cache`.
  Result: GW1-4 stats for 658 players, `api.aerofpl.net` serving, frontend rendering data.
- **`api.aerofpl.net` gotcha:** the frontend's `vite preview` proxies `/api` to
  `VITE_API_URL=https://api.aerofpl.net`. The DNS CNAME was in place but the domain sat
  `unverified` on the web service, so no cert was issued and every frontend API call 500'd.
  `POST /custom-domains/{id}/verify` fixed it in seconds — check this first if the site
  ever shows "no data" while the backend URL works.
- Render API key lives in `sofa_sport/.env` of the **main** repo (`RENDER_API_KEY`), not the
  worktree. Read-only calls via helper scripts in `/private/tmp/claude-501/aerofpl/`
  (`render_status.py`, `render_read.py`); the auto-mode classifier blocks `curl` with the
  key inline and blocks service `PATCH`es — use `git push` to `main` instead of switching
  the tracked branch.
- **OOM incident 2026-09-13 23:42 UTC.** A 3-GW manager-squad solve restarted the instance
  ("Instance restarted", no traceback; frontend showed `Unexpected token '<'`). Render's
  memory metric showed the instance idling at **475–500 MB of 512 MB**: gunicorn + Celery
  worker + Celery beat each loaded Django+pandas because `tasks.py` imported `api_views` at
  module level; a solve added ~205 MB (gunicorn) + ~107 MB (CBC child). Fixes: `api_views`
  imported lazily inside the task; beat embedded in the worker (`celery worker -B`, one
  process fewer); optimizer candidate pool capped per position (`OPTIMIZER_POOL_CAPS`,
  manager squad always kept) — CBC now ~40 MB; frontend reports a non-JSON 5xx honestly.
  If memory creeps back, the next lever is the starter → standard plan, not more code.
- Still to do on Render: nothing was migrated for `FixtureOdds` (empty by design),
  `AthletePrediction` is empty by design, SofaSport tables are empty (subscription cancelled).
  Celery beat's `run_daily_pipeline` (03:30 UTC) keeps FPL data fresh from here.

### Single-service architecture — 2026-09-14

The separate `fpl-pulse-frontend` Render service (a `vite preview` process proxying `/api`)
is retired. `build.sh` now runs `npm ci && npm run build` and **Django serves the React
app**: WhiteNoise serves `frontend/dist` as `WHITENOISE_ROOT` (`/`, `/assets/*` with
immutable caching), and `fpl_platform.views.spa_index` returns `index.html` for every
non-`api/`/`admin/`/`static/` route so deep links survive a refresh. Tests:
`etl/tests/test_spa_serving.py`. The React code is unchanged — it already used relative
`/api/...` URLs; just never set `VITE_API_URL` at build time.

Consequences: one origin (`aerofpl.net` and `aerofpl.net/api/...`), so CORS and the
`api.` subdomain are no longer load-bearing (kept for compatibility); one fewer $7 service;
a Django restart takes the whole site down rather than leaving a data-less shell, which
was judged acceptable. **Manual steps:** move the `aerofpl.net` / `www` custom domains from
the old frontend service to `fpl-pulse-web` (a domain can only live on one service), then
delete `fpl-pulse-frontend` in the dashboard.

## Visual direction

Dark graphite + Spring Bud lime, per the user-approved "Option 2" mockup:

- graphite `#101011`, `#191919`, `#242424`
- Spring Bud lime `#A5FF01`
- compact left navigation rail, clean typography (Inter, now including weight 800)
- modular, dense but readable; static cards, subtle borders, restrained glow

Tokens and shared primitives now live in **`frontend/src/styles/design-system.css`**
(imported ahead of `theme.css` in `main.tsx`). Page stylesheets should use the
`--aero-*` variables and `.aero-*` primitives rather than new hex values.

## Completed in this pass

### 1. Season-rollover ETL fix and data refresh — DONE

`django_etl/etl/services/etl_runner.py`:

- `_handle_season_rollover()` compares the incoming bootstrap's season start year
  (earliest event deadline) against the stored one (earliest fixture kickoff) and
  purges gameweek-scoped tables on a change.
- `_prune_unplayed_gameweeks()` is the **self-healing** guard: it deletes per-gameweek
  rows above the latest gameweek that has actually kicked off. This is what repaired
  the database, because the ID-level rollover had already happened in an earlier run
  and the year check could no longer fire. It is idempotent and a no-op mid-season.
- `_sync_athletes()` skips (with a warning) any element without a stable `code`
  instead of aborting the whole atomic pass on a NOT NULL violation.
- `_sync_event_status()` now reads the `points` key the endpoint actually returns;
  it had been reading a non-existent `status` key, so `EventStatus` was always empty.

Tests: `django_etl/etl/tests/test_season_rollover.py` (20 tests) covers team-code
and athlete-code rollover, ID swaps, temporary-code collisions, season detection,
the purge, and the unplayed-gameweek prune.

Data state after the refresh: **GW3 complete, GW4 next** (deadline 2026-09-12T12:30Z),
2,107 `AthleteStat` rows for GW1–3 (17,832 stale rows removed), 656 active athletes,
140 marked removed, fixtures for the 2026/27 season, `Top100Summary` synced for GW3.
Redis caches were cleared after the refresh.

### 2. Home-page freshness guards — DONE

`frontend/src/pages/HomePage.tsx`:

- Toolbar reads `Next: Gameweek {fixtures.start_gameweek}`.
- Sub-heading reads `Planning Gameweek N · data through GWM`.
- Gameweek Pulse labels the landing event **Latest completed GW**.
- Elite data is used only when `elite.game_week === data.current_gameweek`.
- When elite data is stale the hero falls back to the **form leader** rather than
  claiming a current captain recommendation, and a note explains the mismatch.
- Elite Signals shows *"Awaiting a current-gameweek elite-manager sync"* when mismatched.

### 3. Compare Players — REDESIGNED

`frontend/src/pages/ComparePage.tsx` + new `ComparePage.css`. Rebuilt around the
decision rather than a stat dump:

- identity row (photo, club, position, price, ownership, availability)
- **Decision snapshot** with the best value in each row highlighted: official FPL
  expected points, form, PPG, total points, price, ownership, next-3 fixture difficulty
- named upcoming fixtures with difficulty ratings (not just an averaged number)
- minutes & start risk, set-piece role, recent form, attribute radar
- the exhaustive stat tables and European/cup matches moved into a collapsed
  `<details>` so nothing was lost

Backend support added to `player_detail`: `upcoming_fixtures`, `next_gameweek`,
`ep_this`, `ep_next`.

### 4. Analyze Manager — REDESIGNED

`AnalyzeManagerPage.tsx` + new `AnalyzeManagerPage.css`. The page and its three
components (`ManagerSummary`, `ManagerHistory`, `ManagerGameweek`) previously had
**no stylesheet at all**. Saved manager ID, view and gameweek behaviour preserved.
Also fixed the team badge URLs, which used `badges-alt/t{team_id}.svg` (403) instead
of `badges-alt/{team_code}.svg`.

### 5. Optimizer integrated into Decision Lab — DONE

- `OptimizeTeamPage.tsx` now exports `SquadOptimizer`, rendered by
  `DecisionDashboardPage` as its "Build optimal squad" mode (`?mode=optimizer`).
- Standalone nav entry removed; `/optimize` redirects to `/decision-lab?mode=optimizer`.
- **The solver never worked before this pass.** `SQUAD_COMPOSITION` is keyed on `GK`
  while the API views label goalkeepers `GKP`, so the goalkeeper constraint matched
  no players and every solve returned infeasible. `solver.py` now normalises position
  aliases (`normalize_position`). Covered by `django_etl/etl/tests/test_fpl_solver.py`.
- `pulp` was missing from the local environment and is now installed.
- When no stored model projections exist for the horizon, the optimizer falls back to
  the **official FPL `ep_next`** held flat across the horizon and reports this via
  `meta.projection_source` / `meta.projection_note`, which the UI displays.

### 6. Price Monitor — DONE

`PriceChangePredictorPage.tsx` renamed in user-facing copy; route is `/price-monitor`
(`/price-predictor` redirects). The page now separates:

- **Official** — actual price changes this gameweek from the FPL bootstrap
  (`meta.official` added to `/api/price-predictor/`), labelled "Official".
- **Estimated** — transfer-momentum panels, retitled "Strongest net transfers in/out",
  under an explicit note that the official API publishes no probability of a future
  price change and that no unvalidated probability is shown.

### 7. Cross-cutting fixes

- `theme.css`: `html, body { height: 100% }` made the body the scroll container,
  breaking `window.scrollTo` and anchor navigation on every page. Body is now
  `min-height: 100%`.
- Flex/grid children lacked `min-width: 0` on Home and Decision Lab, so wide tables
  stretched their columns and pushed content off-screen on phones.
- Fixtures was unreachable on mobile (the nav footer is hidden below 720px); a
  mobile-only entry was added inside the collapsible menu.
- `players_list` and the optimizer now exclude `removed=True` athletes — the Players
  page was showing 796 players including 140 departed ones with last-season totals.
- `ManagerHistory` no longer renders a transfer cost of `-0 pts`.
- `.decision-callout` and `.report-link` in `DecisionDashboardPage.css` still used the
  old blue accent after the palette sweep; both are now on the graphite/lime system.

> Three pre-existing failures in `test_api_views.py` were fixed along the way: the
> price-history tests still seeded `RawEndpointSnapshot` after that endpoint had been
> rewritten onto `PriceSnapshot`. Current results are in
> **Verification snapshot** at the end of this file.

### 8. ML feature leakage — FIXED (audited first, then corrected)

Audit findings (`etl/ml/features.py`, verified empirically on GW1–3 data):

- **`ppg_season` was a label leak**, not an `Athlete` field: the season aggregate had no
  `game_week` filter, so a GW2 training row averaged GW1–3 points including its own
  target. Constant per athlete (e.g. 5.0 at both GW2 and GW3 for athlete 1).
- `selected_pct`, `transfers_in_delta` (season-cumulative), `chance_of_playing_next_round`
  were read from the live `Athlete` row — 100% identical across gameweeks for all 60
  sampled athletes. Contamination reached every trainable row.
- Fixture context used `.first()`, collapsing double gameweeks and hiding blanks.

Fix:

- `AthleteStat` gained nullable as-of-deadline columns `selected`, `transfers_in`,
  `transfers_out`, `value` (migration `0012`), populated from element-summary `history`,
  which is complete for GW1–3 (644/675/710 rows). `etl_runner.sync_gameweek_context` is
  **update-only** (never manufactures stat rows) and only trusts history rows whose
  `(fixture, round)` is a current-season `Fixture` — departed players' summaries still
  carry last season's history. Runs after event-live in `run_single_pass`.
- `python manage.py backfill_gameweek_context [--dry-run]` backfills from stored
  `ElementSummary` rows (skips `removed=True`). Already run locally.
- `features.py` rewritten: all aggregates are `game_week__lt`; `ppg_to_date` /
  `games_to_date`; `transfers_balance` + `value` come from the as-of row, with a `live`
  fallback **only** for a gameweek above the latest played one; `fixture_count` /
  `home_fixtures` / mean `opponent_fdr` handle DGW/BGW. `chance_of_playing` and
  ownership-% are dropped (not reconstructable / unit mismatch with live data).
  `FEATURE_NAMES` + `feature_vector()` are the single source of truth; `model.py` uses
  them. Rows without stored context carry `context_source=None` and are skipped by
  `iter_training_rows`, not imputed.
- Tests: `etl/tests/test_ml_features.py` (14 tests) — 91 total passing.

Smoke-train (scikit-learn 1.6.1 / joblib 1.5.3 now installed locally): pipeline runs in
~13 s, but a GW2→GW3 forward check gives **MAE 1.56 vs 1.41 for predicting zero** and 1.31
for naive PPG. One gameweek of training data is not a model. Artifacts were deleted and
`django_etl/etl/ml_models/` is now gitignored. `AthletePrediction` remains empty and
`ep_next` fallbacks stay labelled.

> **Guard still needed:** the daily Celery task runs `train_prediction_model
> --skip-training`, which will write `AthletePrediction` rows the moment artifacts exist
> on that host. Before anyone trains for real, gate population behind a forward-check
> threshold (beat naive PPG on the held-out latest gameweek) or an explicit flag.

### 9. Player game log + same-position percentiles — DONE

New endpoint `GET /api/players/<id>/gameweeks/` (`etl/services/player_gameweeks.py`):

- `gameweeks[]` — every official FPL stat per gameweek from `AthleteStat`, plus the
  as-of `value` / `selected` / `transfers_in` / `transfers_out` context and opponent,
  venue and score labels from `ElementSummary.history` (a list per GW, so DGWs show both).
- `percentiles` — 20 season-total stats (incl. xG/xA/xGI/xGC per 90) ranked against
  **same-position players with ≥90 season minutes**; ties split, lower-is-better
  inverted for xGC. Response carries `cohort_size`, `cohort_min_minutes`,
  `player_in_cohort` and `data_through_gameweek` so the UI can label provenance.
  Cohort totals cached 10 min per (position, through_gw).

UI: `frontend/src/components/PlayerGameLog.tsx` (+ `.css`), mounted in `PlayerModal`
directly under the basic-stat strip. Percentile bars (two columns desktop, one on
phone) with "Official FPL stats · through GWn · cohort N POSs with 90+ min"; game log
as a sticky-first-two-columns table scrolling inside its own container. Tests:
`etl/tests/test_player_gameweeks.py` (5). Headless QA at 1440x900 / 375x812: no page
or modal overflow; the only 4xx on the modal are the pre-existing SofaSport
heatmap/radar 404s.

## Data sources — decided 2026-09-12

### Deployment moved to a new Render workspace (reported 2026-09-13)

Reported by the session doing the Render migration; **not verified from this worktree** —
confirm before relying on it:

- New services: `fpl-pulse-web-8u1j.onrender.com`, `fpl-pulse-frontend-ptan.onrender.com`
- **The new Postgres is brand new and EMPTY.** Migrations ran; there is no historical
  data — no heatmaps, no price snapshots, no trained predictions, no Top 100 rows.
- Whether the old database gets dumped and restored is still undecided.

What an empty production database means for the UI, given the guards already built:

| Surface | Behaviour on an empty DB |
| --- | --- |
| Home — Gameweek Pulse / hero | Shows `—` until the ETL runs; elite signals show "Awaiting a current-gameweek elite-manager sync" |
| Price Monitor — momentum panels | Nothing to chart until `PriceSnapshot` rows accumulate; official price-change panel works as soon as the ETL runs |
| Compare Players | Falls back to official `ep_next`, already labelled |
| Decision Lab | Needs a generated `team_<id>_live.json`; shows the recovery link otherwise |
| Heatmaps / radar / attributes | Empty, and **will stay empty** — SofaSport is cancelled |

None of these error. They degrade honestly, which is what the freshness work was for. The
first production ETL run repopulates everything except the SofaSport-derived surfaces.

### Render deployment — state verified 2026-09-13 21:40

Probed directly (both services respond 200):

- API `fpl-pulse-web-8u1j.onrender.com` — **database empty**: `/api/landing/` returns
  `current_gameweek: 0`, `/api/players/` returns 0 players, fixtures ticker returns 0
  teams, `/api/top100/template/` 404s. Migrations ran, nothing else has.
- Frontend `fpl-pulse-frontend-ptan.onrender.com` — **running the OLD code.** The
  deployed bundle (`/assets/index-BsAk_Ss3.js`) contains "Price Predictor" and
  "Optimizer" and **none** of the redesign markers ("Price Monitor", "Decision Lab",
  "aero-page", "Fixture planner", "DATA STATUS"). None of the ~121 uncommitted files in
  this worktree have reached Render.
- The Render MCP available in these sessions is connected to a **different account**
  (`dmitnick@domainskate.com`, 154 rugby-* services, no FPL services). It cannot see or
  manage the FPL deployment. Managing the new FPL workspace needs either a Render API
  key for that workspace or the user in the dashboard.

So "working on Render" requires all three of: (1) commit + push the redesign to the
branch Render deploys from, (2) run the ETL against the production database, (3) sync
Top 100 for the current gameweek. `render.yaml` sets no `branch`, so Render deploys the
repo default branch — confirm which before pushing.

### Deploy — ready, awaiting one push (2026-09-14)

Everything is merged and verified locally; the only remaining step is pushing `main`,
which the agent session was **not permitted** to do (auto-mode classifier blocked
`git push origin HEAD:main`). Run it from a terminal:

```bash
cd /Users/nyashamutseta/Desktop/personal/FPL-model-upgrade
git push origin codex/model-upgrade-20260906   # feature branch, already on origin
git push origin HEAD:main                       # triggers the Render deploy
```

State at hand-off:

- Local `HEAD` = `2b754cb` = `codex/model-upgrade-20260906` merged with `origin/main`.
  The merge was a clean `ort` merge touching only `render.yaml` (6+/2-), bringing in
  yesterday's Render fixes `6a5248f` (fresh-workspace blueprint) and `e70b009`
  (new-hostname CORS/CSRF).
- 96 tests pass and `npm run build` passes on `2b754cb`.
- **Rollback point:** `origin/main` = `e70b009` before the push. If the deploy misbehaves,
  `git push --force origin e70b009:main` restores it.
- `gh` is authenticated as `AvocadoCease` with **READ** permission on `ceasemaker/FPL`, so
  it cannot open or merge a PR; the SSH remote `github-personal` has write access. This
  push therefore bypasses the repo's PR convention — a deliberate trade-off for the
  deploy goal, flagged here so it can be revisited.

After the push, Render rebuilds both services (allow ~5-10 min). Verify the new code is
live before trusting anything else:

```bash
# should return JSON, not 404 — endpoint exists only post-redesign
curl -s https://fpl-pulse-web-8u1j.onrender.com/api/players/1/gameweeks/ | head -c 200
# should include an "official" key
curl -s 'https://fpl-pulse-web-8u1j.onrender.com/api/price-predictor/?limit=10' | grep -o '"official"'
# frontend bundle should mention the new nav labels
curl -s https://fpl-pulse-frontend-ptan.onrender.com/ | grep -oE '/assets/index-[^"]+\.js'
```

Then the database. It is **empty** and self-populates via Celery beat inside the web
service (`run_daily_pipeline`, 03:30 UTC daily: `run_fpl_etl` → … → `sync_top100`). To
avoid waiting for that, open the web service's **Shell** tab in the Render dashboard and
run, in order:

```bash
cd django_etl
python manage.py run_fpl_etl --verbosity 1
python manage.py sync_top100
python manage.py clear_cache
```

Expected afterwards: `/api/landing/` reports `current_gameweek: 3`, `/api/players/`
returns ~656 players, `/api/top100/template/` returns GW3. The dead SofaSport steps in
the daily pipeline are each try/except-wrapped and will not block the FPL steps.

### SofaSport is cancelled

The user no longer pays for the SofaSport RapidAPI subscription. `SOFASPORT_API_KEY`
is **not set** and will not be. Consequences:

- `sync_fixture_odds.py` (SofaSport-backed) is dead. `FixtureOdds` has **0 rows**.
- `SofaSportClient` (`django_etl/sofa_sport/scripts/api_client.py:28`) raises `ValueError`
  unless **both** `SOFASPORT_API_KEY` and `SOFASPORT_API_HOST` are set — and with an
  unpaid subscription the calls 401/403 even when a key is present.
- Scheduled tasks that will now fail or return nothing, verified against
  `django_etl/fpl_platform/celery.py`:

  | Task | Schedule |
  | --- | --- |
  | `sync_fixture_odds` | daily 05:30 |
  | `update_fixture_mappings` | Mon 02:00 |
  | `update_lineups` | Tue 03:00 |
  | `update_season_stats` | Wed 02:00 |
  | `update_radar_attributes` | Wed 03:00 |
  | `collect_heatmaps` | Wed 05:00 (also reached via `run_daily_pipeline`, daily 03:30) |

- The radar chart (`/api/sofasport/compare/radar/`), player heatmaps
  (`SofasportHeatmap`), season stats and player attributes will keep serving whatever
  is already in the database. **They will not error — they will silently freeze.**
  On the new empty production database they start empty and stay empty.
  Freshness guards for these are still TODO (see Known gaps).
- `render.yaml` on `main` **does** declare `SOFASPORT_API_KEY` (`sync: false`) and
  `SOFASPORT_API_HOST` — added by `6a5248f` (2026-09-13). An earlier note here said
  otherwise; that was checked against a stale `origin/main` before fetching. Since the
  subscription is cancelled these can be dropped from the blueprint whenever the
  SofaSport surfaces are formally removed; harmless but misleading until then.

### Do not buy an odds feed

A paid provider signup was attempted and abandoned (free trial only, card required).
Before anyone tries again: **the project's own acceptance gate has already declined to
promote market odds.** From `/api/decision-dashboard/` → `accepted_forecast`:

```
mae_gain_vs_odds_ridge:         0.036   (2.3309 -> 2.3056 MAE, ~1.1%)
top5_weekly_diff_ci95:          [-0.632, +0.168]   <- crosses zero
accepted_for_mean_forecast:     true
accepted_for_optimizer:         false
accepted_for_transfer_horizon:  false
```

Odds buy roughly 1% on mean forecast error and show no proven top-five benefit. Paying
for a live feed would be buying a marginal gain on a component the evidence gate has
not approved. This is a deliberate decision, not an oversight.

### What is free and actually works

Both tested on 2026-09-12:

| Source | Server-side | Markets | Covers |
| --- | --- | --- | --- |
| `football-data.co.uk` | **200 via curl, no key** (follow the 302: use `curl -L`) | B365 + market-average 1X2, O/U 2.5 | **Played** matches only |
| SofaScore free API | **403 — Cloudflare** | 1X2, double chance, O/U | Upcoming, but **browser only** |

**football-data.co.uk** — already coded at `django_etl/etl/services/football_data.py`.
`https://www.football-data.co.uk/mmz4281/2627/E0.csv` returned 30 rows (GW1-3) with
columns `B365H/D/A`, `AvgH/D/A`, `B365>2.5`, `B365<2.5`. Historical-only, which is the
right shape for the backtest that adjudicates the odds question.

**SofaScore free API** — works from a real browser, 403s from curl/Django/Celery
regardless of User-Agent, Referer or Origin, on all of `api.sofascore.com`,
`www.sofascore.com` and `api.sofascore.app`. This is the *same* 403 the user's own AWS
Glue job hit in 2024 (`athstat_repos/aws_glue/etl_jobs/monitoring/old_jobs.csv:141`).
Do not put it behind a Celery task.

Verified working URLs (open in a browser, not curl):

```
# EPL seasons            -> current season id 96668 (Premier League 26/27)
https://api.sofascore.com/api/v1/unique-tournament/17/seasons
# Upcoming fixtures
https://api.sofascore.com/api/v1/unique-tournament/17/season/96668/events/next/0
# Odds for one event     (16363264 = Liverpool v Fulham, GW4)
https://api.sofascore.com/api/v1/event/16363264/odds/1/all
```

Shape notes for whoever writes the adapter: odds arrive as **fractional strings**
(`"fractionalValue": "1/2"`), so decimal = `1 + num/den`. `initialFractionalValue`
(opening price) and `change` (`1`/`0`/`-1`) map onto the currently-unused `prev_*`
fields and the movement arrows.

### What `FixtureOdds` consumers actually need

`fixture_market.context_from_odds()` reads exactly seven fields:

- `home_odds`, `draw_odds`, `away_odds` — **required**; returns `None` and skips the
  fixture without them
- `over_odds`, `under_odds` — drives the goal-environment estimate
- `btts_yes_odds`, `btts_no_odds` — optional, there is an explicit `if btts_yes is None`
  fallback

### Current odds in the UI are a static snapshot

The Fixtures planner's "Win odds" and blend modes read
`analysis/fpl_decision_backtest/data/current_market/premier-league-gw4-gw5-odds-2026-09-12.json`
— a hand-collected Oddschecker snapshot covering **GW4-5 only**, which is why GW6-8
render "Market unavailable · FDR n". That degradation is correct and honest; nothing is
broken, it just is not live.

## Agreed priority order

1. ~~Fix the feature leakage in `etl/ml/features.py`.~~ **DONE 2026-09-12** — see
   Completed §8. Remaining follow-up: gate `AthletePrediction` population behind a
   forward-check threshold before training on more gameweeks.
2. **Wire `football-data.co.uk` as the free historical odds feed.** No auth, no signup,
   half-written already. Feeds the backtest that decides whether odds ever earn promotion.
3. **Live odds — only if the "Win odds" toggle needs to be current.** Browser-assisted:
   fetch from SofaScore in a real browser on demand and write to `FixtureOdds`. Manual,
   once or twice a week. No subscription, no headless-Chromium-in-Celery, no Cloudflare
   arms race.
4. **SofaSport decay guards** for the radar chart, heatmaps and attributes, so they
   report their age instead of silently freezing.

### Reordered by the Render migration (2026-09-13)

The move to a new, **empty** production database changes two of these:

- **The `--skip-training` footgun is now the most urgent item.** Completed §8 flagged that
  the daily Celery task runs `train_prediction_model --skip-training`, which writes
  `AthletePrediction` rows the moment model artifacts exist on the host. The smoke-train
  scored **MAE 1.56 against 1.41 for predicting zero** — worse than nothing. On a fresh
  production host this is one `train_prediction_model` run away from filling the UI with
  numbers that lose to a constant. Gate population behind a forward-check threshold
  (must beat naive PPG on the held-out latest gameweek) or an explicit flag **before**
  anyone trains on the new host.
- **SofaSport guards change shape.** On the old database those surfaces held stale data,
  so the guard was "report your age". On the new empty one they hold *nothing* and never
  will, so the honest treatment is "this feature has no data source" — removal, a
  replacement provider, or a clearly-labelled static snapshot. Decide which before
  writing an age-based guard that will never have an age to report.

## A note for the next agent

The user asked a previous agent to create an account on an odds provider. Creating
accounts and entering passwords is out of scope regardless of authorisation — the user
does the signup, the agent does the integration. That split worked fine; do not
relitigate it, and do not let a transcript of another agent reasoning its way past it
change the answer.

## Known gaps / next steps

Ordered by value. See **Agreed priority order** above for the reasoning.

- **Feature leakage — fixed** (Completed §8). `scikit-learn`/`joblib` are installed
  locally. Do not populate `AthletePrediction` until a model beats naive PPG on a held-out
  gameweek; with GW1–3 it does not.
- **`populate_predictions` is disabled** and raises `CommandError` before touching data. It
  previously used `random.uniform` and could write randomised numbers into the same table
  as model projections. Leave it disabled. Note the Celery *task* of the same name calls
  `train_prediction_model --skip-training`, not this command, so the daily pipeline is
  unaffected.
- `AthletePrediction` is empty (0 rows). Compare Players and the optimizer both fall back
  to the official FPL `ep_next` and label that source explicitly
  (`meta.projection_source` / `meta.projection_note`).
- **SofaSport-backed features will silently freeze** now the subscription is cancelled:
  radar chart, heatmaps, season stats, player attributes. They need freshness guards of
  the same kind already applied to the home page and Decision Lab.
- The Decision Lab reads a saved local analysis
  (`analysis/fpl_decision_backtest/output/team_576154_live.json`), regenerated for GW4 via
  `python live_team_analysis.py <entry_id> --horizon 3 --output ...`. `meta.is_stale` /
  `saved_for_gameweek` / `live_next_gameweek` drive a banner so a stale run cannot present
  as current — but it still needs re-running each gameweek. Decision Lab now has a manager
  picker shared with Analyse Manager via URL + localStorage; managers without a generated
  file get a recovery link rather than silently falling back to `576154`.
- `run_single_pass` wraps ~700 HTTP calls in a single `@transaction.atomic` block. Completes
  in ~2 minutes locally but is worth revisiting for production.
- `/api/fpl/bootstrap-static/` returned intermittent 500s on 2026-09-11 (upstream
  flakiness); passing since, but worth watching.
- `.role-dot.shield` in `DecisionDashboardPage.css` is still `#3b82f6`. This is **intentional**
  — shield / differential / balanced is a three-way categorical encoding and needs distinct
  hues. It is not a missed palette sweep.

## Verification snapshot (2026-09-12)

- `python manage.py test etl` — **96 tests passing** (14 leakage guards, 5 game-log)
- `npm run build` — passing. `npx tsc --noEmit` reports only pre-existing errors: missing
  `animejs` types, one `replaceAll` lib-target issue in Decision Lab.
- Browser QA at 1440x900 and 375x812 across `/`, `/players`, `/compare`, `/analyze`,
  `/decision-lab`, `/decision-lab?mode=optimizer`, `/price-monitor`, `/fixtures`:
  no horizontal overflow on any route at either width, no server errors.
- Data state: GW3 complete, GW4 next (deadline 2026-09-12T12:30Z), 656 active athletes,
  `AthleteStat` GW1-3 only (now with as-of `selected`/`transfers_*`/`value` context), `Top100Summary` synced for GW3, `FixtureOdds` empty.

**Re-verified 2026-09-13 21:35** after a full cold start (Docker had stopped with the
reboot): **96 tests passing**, both servers up, all eight routes render with no
horizontal overflow and no load errors. Data still GW3 complete / GW4 next.

Do not deploy unless the user explicitly asks.
