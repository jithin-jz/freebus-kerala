# FreeBus Kerala

Production-oriented FastAPI, Jinja2, TailwindCSS, PostgreSQL/Supabase, Docker, and PWA for finding Priyadarshini eligible KSRTC ordinary buses.

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/YOUR_USERNAME/priyadarshini-bus-finder.git
cd priyadarshini-bus-finder
cp .env.example .env
# Edit .env with your values

# 2. Start local services
docker compose up --build

# 3. Run initial scrape (populates the database)
docker compose exec app python -m scraper.main

# 4. Seed OSM stop coordinates (run once)
docker compose exec app python scripts/seed_stops.py

# 5. Open the app
open http://localhost:8000

# Dev extras
docker compose --profile tools up
docker compose exec app pytest tests/ -v
docker compose exec app ruff check .

# Tailwind watch (run in separate terminal for CSS changes)
npx tailwindcss -i ./app/static/css/app.css -o ./app/static/css/app.min.css --watch
```

On Windows PowerShell, use `Start-Process http://localhost:8000` instead of `open`.

## Supabase + Render Production Setup

1. Create a project at supabase.com and note the Project URL and anon key.
2. Open the SQL Editor and run every file in `migrations/` in order (`001_initial_schema.sql`, then `002_route_stops_and_reconciliation.sql`).
3. Go to Settings → Database and copy the transaction-mode (pooler) connection string and prefix it with `postgresql+asyncpg://`.
4. Build the CSS once and commit it if you changed any templates: `npm install && npm run build:css` (outputs `app/static/css/app.min.css`, which is committed so the deploy needs no Node).
5. Push to GitHub. CI (`.github/workflows/deploy.yml`) runs tests and lint.
6. In Render, create a Blueprint from `render.yaml`. It provisions the web service on the **native Python runtime** (no Docker): build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
7. Set these as Render secrets (synced=false in `render.yaml`): `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_DB_URL` (with the password filled in).
8. Render auto-deploys on every push to `main`. The daily scrape runs via GitHub Actions (`.github/workflows/scrape.yml`) — add `SUPABASE_DB_URL` as a repo secret and `SCRAPER_SOURCE_URL` as a repo variable.
9. Add the custom domain `priyadarshinibus.in` in Render and point DNS accordingly.

Note: keep `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` small (defaults 5/5). The Supabase pooler multiplexes connections, so a large SQLAlchemy pool only exhausts the upstream limit. Docker (`Dockerfile`/`docker-compose.yml`) is kept for local development only.

## Endpoints

- `GET /` renders the GPS-first home page.
- `GET /search?from=Kalpetta&to=Kozhikode` renders server-side search results.
- `GET /api/v1/search?from=Kalpetta&to=Kozhikode` returns route JSON.
- `GET /api/v1/nearby?lat=11.6101&lng=76.0824` returns nearby eligible buses.
- `GET /api/v1/health` returns service and last scrape status.

## Privacy

There are no accounts, cookies, sessions, or analytics. GPS coordinates are used only to calculate nearby buses and are never stored.
