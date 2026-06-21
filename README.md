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


## Endpoints

- `GET /` renders the GPS-first home page.
- `GET /search?from=Kalpetta&to=Kozhikode` renders server-side search results.
- `GET /api/v1/search?from=Kalpetta&to=Kozhikode` returns route JSON.
- `GET /api/v1/nearby?lat=11.6101&lng=76.0824` returns nearby eligible buses.
- `GET /api/v1/health` returns service and last scrape status.

## Privacy

There are no accounts, cookies, sessions, or analytics. GPS coordinates are used only to calculate nearby buses and are never stored.
