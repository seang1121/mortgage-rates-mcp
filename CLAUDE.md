# Mortgage Rates MCP Server

## Language & Stack
- **Python** — all source files are `.py`
- **Flask** web framework with SQLite (`mortgage_rates.db`)
- No build step, no transpilation — run directly with Python 3.14+

## Key Entry Points
- `backend/app.py` — Flask application (port 5001)
- `backend/scraper.py` — Scrape orchestrator (called by scheduler)
- `backend/scheduler.py` — APScheduler 7am/7pm EST cron

## Architecture
- `backend/` — Flask API + business logic
- `backend/extractors/` — One file per lender, inherits BaseLenderExtractor
- `mcp/` — PyPI MCP package (thin proxy to backend API)
- `scripts/` — One-off setup scripts

## Database (7 tables)
Core: `rates`, `rate_history`
Auth: `users`, `api_keys`
Alerts: `rate_alerts`, `notification_preferences`
Monitoring: `scrape_logs`

Database is NOT in git. Use `scripts/create_database.py` to initialize.

## Three-Tier Data Fetching
- **Tier 1** (4 sources): Direct API/JSON — Freddie Mac, MND, PennyMac, Citizens
- **Tier 2** (9 lenders): Stealth browser, low protection — BofA, Wells, Citi, Navy Fed, SoFi, US Bank, Guaranteed Rate, Truist, Mr. Cooper
- **Tier 3** (6 lenders): Stealth browser, heavy anti-bot — Chase, Rocket, PNC, USAA, Flagstar, LoanDepot

## Conventions
- API key prefix: `mort_` (not `sbma_`)
- Port: 5001 (not 5000 — that's betting analyzer)
- Rate bounds: 2.5% to 14.0%
- Products: '30yr', '15yr', 'ARM', 'FHA_30yr', 'VA_30yr'
- Disclaimer required on every API response containing rate data
- Human-readable product names in API responses (e.g., "30-Year Fixed" not "30yr")

## Key Patterns
- Every extractor inherits `BaseLenderExtractor` from `backend/extractors/base.py`
- Scraper runs in batches of 4 with 3x retry on failure
- Failed lenders serve last-known-good with `stale: true` flag
- Rates validated against benchmark cross-reference before storage

## Environment Variables
See `.env.example` — required: `FLASK_SECRET_KEY`
Never commit `.env` or `mortgage_rates.db`
