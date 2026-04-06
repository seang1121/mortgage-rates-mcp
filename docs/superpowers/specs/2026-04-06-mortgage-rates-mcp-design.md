# Mortgage Rates MCP Server — Design Spec

**Date:** 2026-04-06
**Status:** Draft
**Author:** seang1121

---

## Overview

An MCP server that gives AI agents access to real-time mortgage rates from 10 major lenders + 2 national benchmarks. Designed for realtors, mortgage brokers, and homebuyers who need accurate, actionable rate intelligence delivered through any MCP-compatible AI client.

The system has three components:
1. **Backend API** — Flask app (standalone, own port) serving cached rate data with independent auth
2. **Scraper Service** — Adapted from the existing Multi-Lender-Mortgage-Rate-Lookup, runs 2x daily
3. **MCP Package** — `mortgage-rates-mcp` on PyPI, thin proxy to the backend

---

## Architecture

```
AI Client (Claude Desktop, Cursor, VS Code, etc.)
    | stdio
mortgage-rates-mcp (PyPI package)
    | HTTPS + mort_* API key
Flask Backend (Windows, port 5001)
    | reads from
SQLite (mortgage_rates.db)
    | populated by
Scraper (7am + 7pm EST via APScheduler)
    | patchright + urllib
10 Lenders + 2 Benchmarks
```

### Key Decisions

- **Separate Flask app** on port 5001 (not inside betting analyzer)
- **Separate SQLite database** (`mortgage_rates.db`)
- **Separate auth system** with `mort_*` API key prefix
- **Separate Cloudflare tunnel** when domain is ready
- **Windows machine** — patchright + Chromium already installed, server infra exists

---

## Data Sources

### Tier 1 — Direct APIs (no browser)

| Source | Method | Purpose |
|--------|--------|---------|
| Freddie Mac PMMS | urllib → CSV | National benchmark (30yr + 15yr) |
| Mortgage News Daily | urllib → HTML | Real-time national benchmark |

### Tier 2 — Stealth Browser (patchright)

| # | Lender | Type |
|---|--------|------|
| 1 | Bank of America | Big 4 Bank |
| 2 | Wells Fargo | Big 4 Bank |
| 3 | Chase | Big 4 Bank |
| 4 | Citi | Big 4 Bank |
| 5 | Navy Federal CU | Credit Union |
| 6 | SoFi | Online Lender |
| 7 | US Bank | National Bank |
| 8 | Guaranteed Rate | Online Lender |
| 9 | Truist | National Bank |
| 10 | Mr. Cooper | Largest Servicer |

### Products Tracked

- 30-Year Fixed
- 15-Year Fixed
- ARM (5/1, 7/1, 7/6)
- FHA 30-Year (where available)
- VA 30-Year (where available)

---

## Scraping Hardening

### Lender-Specific Extractors

Each lender gets its own extractor class inheriting from a base:

```python
class BaseLenderExtractor:
    name: str
    url: str
    def extract(self, page_content: str) -> list[RateResult]
    def validate(self, rates: list[RateResult]) -> list[RateResult]
```

Benefits:
- One lender breaks, others unaffected
- Targeted CSS selectors per bank's DOM structure
- Custom wait times and interaction logic per lender
- Regex fallback as safety net alongside structured extraction

### Validation Pipeline

Every scraped rate passes through:

1. **Sanity bounds** — reject rates outside 2.5%-14.0% range
2. **Benchmark cross-reference** — flag if >1.5% deviation from Freddie Mac/MND average
3. **Dual extraction** — CSS selector extraction + regex extraction must agree (if both produce results)
4. **Product validation** — 30yr must be higher than 15yr for same lender (basic sanity)
5. **Staleness check** — if a rate matches the previous 5+ scrapes exactly, flag as potentially stale/cached by the lender

### Failure Handling

- **Screenshot-on-failure** — capture rendered page when extraction returns zero rates
- **Last-known-good fallback** — serve previous successful scrape with `"stale": true` and `"scraped_at"` timestamp
- **Alert on degradation** — if 3+ lenders fail in a single scrape cycle, send Discord alert
- **Retry logic** — 3 attempts with increasing wait (8s, 12s, 15s) per failed lender
- **Batch processing** — 4 lenders in parallel, never hammer a single site

---

## Database Schema

### `rates` — Latest scraped rates

```sql
CREATE TABLE rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lender TEXT NOT NULL,
    product TEXT NOT NULL,          -- '30yr', '15yr', 'ARM', 'FHA_30yr', 'VA_30yr'
    rate REAL NOT NULL,
    apr REAL,                       -- nullable, not all lenders provide APR
    zip_code TEXT,
    is_benchmark INTEGER DEFAULT 0, -- 1 for Freddie Mac / MND
    stale INTEGER DEFAULT 0,        -- 1 if serving fallback data
    scraped_at TEXT NOT NULL,        -- ISO timestamp of scrape
    scrape_session TEXT NOT NULL,    -- groups rates from same scrape run
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### `rate_history` — Rolling 90-day history

```sql
CREATE TABLE rate_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,              -- YYYY-MM-DD
    time_of_day TEXT NOT NULL,       -- 'AM' or 'PM'
    lender TEXT NOT NULL,
    product TEXT NOT NULL,
    rate REAL NOT NULL,
    apr REAL,
    zip_code TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### `users` — Account system

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,            -- hex token
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',       -- 'user' or 'admin'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### `api_keys` — Auth tokens

```sql
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    key_prefix TEXT NOT NULL,       -- first 8 chars for identification
    tier TEXT DEFAULT 'free',       -- 'free' or 'pro'
    requests_today INTEGER DEFAULT 0,
    last_reset_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    revoked_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### `rate_alerts` — User-configured threshold alerts

```sql
CREATE TABLE rate_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    product TEXT NOT NULL,           -- '30yr', '15yr', etc.
    threshold REAL NOT NULL,         -- alert when rate drops below this
    lender TEXT,                     -- NULL = any lender
    active INTEGER DEFAULT 1,
    last_triggered_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### `scrape_logs` — Debugging and monitoring

```sql
CREATE TABLE scrape_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scrape_session TEXT NOT NULL,
    lender TEXT NOT NULL,
    status TEXT NOT NULL,            -- 'success', 'failed', 'stale_fallback'
    rates_found INTEGER DEFAULT 0,
    error_message TEXT,
    screenshot_path TEXT,            -- path to failure screenshot
    duration_ms INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Routes

All routes under Flask app on port 5001. Auth via `X-API-Key` header with `mort_*` keys.

### Public (no auth)

```
GET /api/v1/health              — system status, last scrape time, lender count
```

### Authenticated

```
GET  /api/v1/rates                          — all current rates (optional ?zip=&product=&lender=)
GET  /api/v1/rates/best                     — best rate per product (optional ?product=30yr)
GET  /api/v1/rates/compare?lenders=chase,sofi,wells_fargo  — side-by-side comparison
GET  /api/v1/rates/history?product=30yr&days=30            — historical trend
GET  /api/v1/rates/lender/:name             — all products from one lender
GET  /api/v1/rates/scenarios?amount=400000  — 30yr vs 15yr vs ARM comparison
GET  /api/v1/rates/savings?from=chase&to=navy_federal&amount=400000  — switch savings

POST /api/v1/calculate                      — monthly payment calculator
POST /api/v1/rate-sheet                     — generate rate card image (returns base64 PNG)
POST /api/v1/alerts                         — create rate alert
GET  /api/v1/alerts                         — list user's alerts
DELETE /api/v1/alerts/:id                   — remove alert
```

---

## MCP Tools (11)

### 1. `get_rates`
All current rates by product, optional ZIP code filter.
```
Input:  zip_code (optional), product (optional: "30yr", "15yr", "ARM", "FHA", "VA")
Output: Ranked list of rates per product with lender, rate, APR, stale flag, scraped_at
```

### 2. `get_best_rate`
Single best rate for a given loan type.
```
Input:  product (required: "30yr", "15yr", "ARM", "FHA", "VA")
Output: Best lender, rate, APR, how it compares to national average
```

### 3. `compare_lenders`
Side-by-side comparison of specific lenders.
```
Input:  lenders (required: list of lender names), product (optional)
Output: Table of rates per lender per product, highlights best
```

### 4. `get_rate_history`
Historical trend data.
```
Input:  product (optional), lender (optional), days (optional, default 30, max 90)
Output: Daily AM/PM rates, averages, direction (up/down/flat), change amounts
```

### 5. `get_lender_details`
All products from one lender.
```
Input:  lender (required)
Output: All available products with rates, APR, last scraped time
```

### 6. `get_system_status`
Health check.
```
Input:  none
Output: Uptime, last scrape time, lenders reporting, next scheduled scrape, any failures
```

### 7. `calculate_payment`
Monthly payment calculator with full amortization breakdown.
```
Input:  loan_amount (required), rate (optional — uses best available if omitted),
        term_years (optional, default 30), down_payment_pct (optional)
Output: Monthly P&I, total interest paid, total cost, effective monthly with taxes/insurance estimate
```

### 8. `generate_rate_sheet`
Client-ready rate card image.
```
Input:  zip_code (optional), products (optional), branding_text (optional)
Output: Base64-encoded PNG image — clean formatted rate comparison card
```

### 9. `set_rate_alert`
Create a threshold notification.
```
Input:  product (required), threshold (required), lender (optional)
Output: Confirmation with alert ID
```

### 10. `compare_scenarios`
Side-by-side loan scenario comparison.
```
Input:  loan_amount (required), scenarios (optional, default: ["30yr", "15yr", "ARM"])
Output: Per scenario: monthly payment, total interest, total cost, breakeven vs others
```

### 11. `estimate_savings`
Calculate savings from switching lenders.
```
Input:  loan_amount (required), from_lender (required), to_lender (required),
        product (optional, default "30yr")
Output: Monthly savings, annual savings, total savings over loan life,
        breakeven months if refinancing
```

---

## Scraper Schedule

- **7:00 AM EST** — morning scrape via APScheduler CronTrigger
- **7:00 PM EST** — evening scrape via APScheduler CronTrigger
- Each scrape stores results with `time_of_day` = 'AM' or 'PM'
- Rate history tracks both data points daily for intraday movement analysis
- Manual scrape trigger available via admin API endpoint

---

## Rate Sheet Generator

Produces a clean PNG image suitable for texting to clients. Inspired by the Nimrod bet slip generator.

Content:
- Date and time of rates
- ZIP code (if specified)
- Ranked rates for selected products (default: 30yr, 15yr, ARM)
- Best rate highlighted
- Day-over-day change arrows
- National benchmark comparison line
- Optional branding text (broker name/company)

---

## Auth System

- **Independent from betting analyzer** — own users table, own API keys
- **Key prefix:** `mort_` (e.g., `mort_a3f8b2c1d4e5...`)
- **Key storage:** scrypt hashed, only prefix stored in plaintext for identification
- **Free tier:** 20 requests/day
- **Rate limiting:** per API key, resets at midnight EST
- **Admin role:** unlimited requests, can trigger manual scrapes

### Account Onboarding

**V1 (launch):**
- CLI script `create_admin.py` to create admin account + generate first API key
- Admin manually generates `mort_*` keys for brokers they're pitching — invite-only, controlled rollout
- No self-service signup — keeps it tight while validating the product

**Later (with domain):**
- Self-service signup page with email verification
- Same registration flow pattern as the betting analyzer

---

## Alert Delivery System

### Notification Channels (priority order)

1. **Discord webhook** — free, immediate, infra already exists. Default for admin.
2. **Email (SMTP)** — for brokers. Gmail SMTP or SendGrid free tier (100/day). Triggered post-scrape when a rate crosses a threshold.
3. **SMS (future)** — Twilio at ~$0.007/msg. Add when broker demand warrants.

### Flow

After each 7am/7pm scrape completes:
1. Query all active alerts from `rate_alerts` table
2. Compare new rates against each alert's threshold
3. For triggered alerts, look up user's `notification_preferences`
4. Dispatch through configured channel(s)
5. Update `last_triggered_at` to prevent duplicate notifications

### Database Addition

```sql
CREATE TABLE notification_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL,           -- 'email', 'discord_webhook', 'sms'
    destination TEXT NOT NULL,       -- email address, webhook URL, or phone number
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## Compliance & Disclaimers

### Legal Position

We are aggregating **publicly displayed rates** from lender websites. We are NOT originating loans, providing personalized quotes, or acting as a mortgage broker. This is informational aggregation, similar to what Bankrate or NerdWallet does, but without the lead generation.

### Required Disclaimers

**Every API response** includes a `disclaimer` field:
> "Rates shown are publicly advertised rates scraped from lender websites and are not personalized quotes. Actual rates depend on credit score, loan amount, property type, down payment, and other factors. This is not financial advice. Contact lenders directly for official quotes."

**Every rate sheet image** includes disclaimer text at the bottom:
> "Publicly advertised rates as of [date/time]. Not personalized quotes. Contact lenders for official rates."

**Every MCP tool description** includes a one-line note:
> "Returns publicly advertised rates, not personalized quotes."

**Terms of use (with domain):**
- Informational service only, not advisory
- Rates are scraped from public websites and may not reflect current offers
- Users should verify rates directly with lenders before making decisions
- No guarantee of accuracy — lender websites may update between scrape cycles

---

## Repo Structure

```
mortgage-rates-mcp/
├── backend/
│   ├── app.py                  — Flask API (port 5001)
│   ├── database.py             — SQLite wrapper (mortgage_rates.db)
│   ├── auth.py                 — API key generation/validation
│   ├── scraper.py              — orchestrator (batch + retry logic)
│   ├── scheduler.py            — APScheduler 7am/7pm EST
│   ├── rate_sheet.py           — PNG rate card generator
│   ├── calculator.py           — payment/scenario/savings math
│   ├── validators.py           — rate sanity checks + cross-reference
│   ├── notifications.py        — alert delivery (Discord, email, SMS)
│   └── extractors/
│       ├── __init__.py
│       ├── base.py             — BaseLenderExtractor
│       ├── bank_of_america.py
│       ├── wells_fargo.py
│       ├── chase.py
│       ├── citi.py
│       ├── navy_federal.py
│       ├── sofi.py
│       ├── us_bank.py
│       ├── guaranteed_rate.py
│       ├── truist.py
│       ├── mr_cooper.py
│       ├── freddie_mac.py      — Tier 1, no browser
│       └── mnd.py              — Tier 1, no browser
├── mcp/
│   ├── pyproject.toml
│   └── src/mortgage_rates_mcp/
│       ├── __init__.py
│       └── server.py           — 11 MCP tool definitions
├── scripts/
│   ├── create_database.py      — DB init
│   └── create_admin.py         — create admin user + API key
├── screenshots/                — failure screenshots (gitignored)
├── .env.example
├── .gitignore
├── README.md
├── CLAUDE.md
└── LICENSE
```

---

## Dependencies

### Backend
- Flask
- APScheduler
- patchright (stealth browser)
- Pillow (rate sheet image generation)
- werkzeug (password hashing)
- pytz (EST timezone handling)

### MCP Package
- mcp>=1.0.0

---

## Monitoring

- **Watchdog integration** — add mortgage API to existing watchdog or create own
- **Discord alerts** — notify on 3+ lender failures per scrape cycle
- **Scrape logs table** — every scrape run logged with per-lender status, duration, error messages
- **Screenshot storage** — failure screenshots saved to `screenshots/` for debugging

---

## Future Considerations (not in V1 but designed for)

- Additional lenders (Rocket Mortgage, PNC, LoanDepot — currently too anti-bot)
- SMS delivery for rate alerts (Twilio integration)
- White-label rate sheets with broker logo upload
- Credit score tiers (rates vary by credit score)
- Jumbo loan rates
- Refinance-specific rates vs purchase rates
- Own domain + Cloudflare tunnel
- Self-service signup page with email verification
- Broker dashboard (web UI for managing alerts, viewing history)
