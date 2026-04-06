# Mortgage Rates MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack mortgage rate intelligence platform with 12 MCP tools, 19 lender extractors + 2 benchmarks, Flask API, and PyPI package. Compatible with Claude, ChatGPT, Cursor, Windsurf, and all MCP clients.

**Architecture:** Standalone Flask backend on port 5001 with SQLite storage, patchright-based scraper running 2x daily (7am/7pm EST), thin MCP proxy package on PyPI. Independent auth system with `mort_*` API keys and open registration. Three-tier data fetching: Tier 1 (direct API, 4 sources), Tier 2 (easy browser, 9 lenders), Tier 3 (heavy anti-bot, 6 lenders).

**Tech Stack:** Python 3.14, Flask, APScheduler, patchright (stealth Chromium), Pillow, SQLite, mcp>=1.0.0, werkzeug

**Spec:** `docs/superpowers/specs/2026-04-06-mortgage-rates-mcp-design.md`

**Existing scraper reference:** `C:\Users\seang1121\.openclaw\workspace\Multi-Lender-Mortgage-Rate-Lookup\mortgage_rate_report.py`

---

## File Map

### Backend (`backend/`)

| File | Responsibility |
|------|---------------|
| `app.py` | Flask app, route definitions, before_request auth, startup |
| `database.py` | SQLite singleton wrapper, all DB queries |
| `auth.py` | User registration, API key generation/validation, rate limiting |
| `scraper.py` | Orchestrator — launches browser, runs extractors, stores results |
| `scheduler.py` | APScheduler 7am/7pm EST cron jobs |
| `calculator.py` | Payment math, scenario comparison, savings estimation |
| `recommender.py` | Ranked recommendation engine — borrower profile → top picks with explanations |
| `rate_sheet.py` | Pillow-based PNG rate card generator |
| `validators.py` | Rate sanity bounds, benchmark cross-ref, staleness detection |
| `notifications.py` | Alert dispatch — Discord webhook + email |

### Extractors (`backend/extractors/`)

| File | Tier | Responsibility |
|------|------|---------------|
| `base.py` | — | `BaseLenderExtractor` ABC + `RateResult` dataclass |
| `freddie_mac.py` | 1 | CSV via urllib, no browser (benchmark) |
| `mnd.py` | 1 | HTML via urllib, no browser (benchmark) |
| `pennymac.py` | 1 | REST JSON API at `quote.pennymac.com`, no browser |
| `citizens.py` | 1 | Static JSON file at `citizensbank.com/assets/...`, no browser |
| `bank_of_america.py` | 2 | patchright, promo URL |
| `wells_fargo.py` | 2 | patchright, standard scrape |
| `citi.py` | 2 | patchright, standard scrape |
| `navy_federal.py` | 2 | patchright, standard scrape |
| `sofi.py` | 2 | patchright, standard scrape |
| `us_bank.py` | 2 | patchright, standard scrape |
| `guaranteed_rate.py` | 2 | patchright, standard scrape |
| `truist.py` | 2 | patchright, standard scrape |
| `mr_cooper.py` | 2 | patchright, custom Rate/APR pattern |
| `chase.py` | 3 | Akamai — use AEM endpoint, simpler DOM, patchright + CDP fallback |
| `rocket_mortgage.py` | 3 | Akamai — SSR page, rates in initial HTML, patchright stealth |
| `pnc.py` | 3 | Akamai — form fill (home value, down payment, credit, ZIP) + intercept XHR |
| `usaa.py` | 3 | Akamai heavy — patchright stealth, may need proxy rotation |
| `flagstar.py` | 3 | Cloudflare — form fill via patchright, Turnstile challenge |
| `loandepot.py` | 3 | reCAPTCHA v3 — Angular SPA, stealth browser may pass score check |

### MCP Package (`mcp/`)

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | PyPI package config |
| `src/mortgage_rates_mcp/__init__.py` | Package init, exports `mcp` instance |
| `src/mortgage_rates_mcp/server.py` | 12 MCP tool definitions, API client helpers |

### Scripts (`scripts/`)

| File | Responsibility |
|------|---------------|
| `create_database.py` | Initialize all tables |
| `create_admin.py` | Create admin user + print API key |

### Root Files

| File | Responsibility |
|------|---------------|
| `.env.example` | Required env vars template |
| `.gitignore` | Standard ignores + screenshots/, *.db, .env |
| `CLAUDE.md` | Project instructions for AI agents |
| `README.md` | User-facing docs (multi-client: Claude, ChatGPT, Cursor, Windsurf, VS Code) |
| `LICENSE` | MIT |
| `requirements.txt` | Backend Python dependencies |
| `llms.txt` | AI agent discovery — tools, auth, data freshness, disclaimer |

---

## Task 1: Project Scaffolding + .gitignore + .env.example + CLAUDE.md

**Files:**
- Create: `mortgage-rates-mcp/.gitignore`
- Create: `mortgage-rates-mcp/.env.example`
- Create: `mortgage-rates-mcp/CLAUDE.md`
- Create: `mortgage-rates-mcp/LICENSE`
- Create: `mortgage-rates-mcp/requirements.txt`

- [ ] **Step 1: Create .gitignore**

```
# Environment
.env
.env.*
!.env.example

# Database
*.db

# Python
__pycache__/
*.pyc
*.pyo
venv/
.venv/
dist/
build/
*.egg-info/

# Screenshots (debug artifacts)
screenshots/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# CLAUDE local
CLAUDE.local.md
```

- [ ] **Step 2: Create .env.example**

```
# Flask
FLASK_SECRET_KEY=change-me-to-random-string
FLASK_PORT=5001

# Scraper
DEFAULT_ZIP_CODE=32224

# Discord alerts (optional)
DISCORD_WEBHOOK_URL=

# Email alerts (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
```

- [ ] **Step 3: Create CLAUDE.md**

```markdown
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

## Conventions
- API key prefix: `mort_` (not `sbma_`)
- Port: 5001 (not 5000 — that's betting analyzer)
- Rate bounds: 2.5% to 14.0%
- Products: '30yr', '15yr', 'ARM', 'FHA_30yr', 'VA_30yr'
- Disclaimer required on every API response
```

- [ ] **Step 4: Create LICENSE (MIT)**

Standard MIT license with `Copyright 2026 seang1121`.

- [ ] **Step 5: Create requirements.txt**

```
flask>=3.0.0
apscheduler>=3.10.0
patchright>=1.58.0
Pillow>=10.0.0
werkzeug>=3.0.0
pytz>=2024.1
```

- [ ] **Step 6: Create directory structure**

```bash
mkdir -p backend/extractors mcp/src/mortgage_rates_mcp scripts screenshots
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "scaffold: project structure, .gitignore, .env.example, CLAUDE.md, requirements"
```

---

## Task 2: Database Layer

**Files:**
- Create: `backend/database.py`
- Create: `scripts/create_database.py`

- [ ] **Step 1: Create database.py**

Singleton SQLite wrapper with connection pooling. Must include:
- `get_connection()` — returns context-managed connection with `row_factory = sqlite3.Row`
- `query(sql, params)` — execute SELECT, return list of dicts
- `execute(sql, params)` — execute INSERT/UPDATE/DELETE, return cursor
- All 7 table creation statements from spec (rates, rate_history, users, api_keys, rate_alerts, notification_preferences, scrape_logs)
- `init_db()` — create all tables if not exist
- DB file path: `backend/mortgage_rates.db`

```python
import os
import sqlite3
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mortgage_rates.db")

class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.db_path = DB_PATH
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def query(self, sql, params=None):
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params or ())
            return [dict(row) for row in cursor.fetchall()]

    def execute(self, sql, params=None):
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params or ())
            conn.commit()
            return cursor

    def init_db(self):
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lender TEXT NOT NULL,
                    product TEXT NOT NULL,
                    rate REAL NOT NULL,
                    apr REAL,
                    zip_code TEXT,
                    is_benchmark INTEGER DEFAULT 0,
                    stale INTEGER DEFAULT 0,
                    scraped_at TEXT NOT NULL,
                    scrape_session TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS rate_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time_of_day TEXT NOT NULL,
                    lender TEXT NOT NULL,
                    product TEXT NOT NULL,
                    rate REAL NOT NULL,
                    apr REAL,
                    zip_code TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    key_prefix TEXT NOT NULL,
                    tier TEXT DEFAULT 'free',
                    requests_today INTEGER DEFAULT 0,
                    last_reset_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    revoked_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS rate_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    product TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    lender TEXT,
                    active INTEGER DEFAULT 1,
                    last_triggered_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS notification_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS scrape_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scrape_session TEXT NOT NULL,
                    lender TEXT NOT NULL,
                    status TEXT NOT NULL,
                    rates_found INTEGER DEFAULT 0,
                    error_message TEXT,
                    screenshot_path TEXT,
                    duration_ms INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_rates_scrape_session ON rates(scrape_session);
                CREATE INDEX IF NOT EXISTS idx_rates_lender_product ON rates(lender, product);
                CREATE INDEX IF NOT EXISTS idx_rate_history_date ON rate_history(date, product);
                CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
            """)

db = Database()
```

- [ ] **Step 2: Create scripts/create_database.py**

```python
"""Initialize the mortgage rates database. Safe to run multiple times."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from backend.database import db

print(f"Database initialized at: {db.db_path}")
print("Tables created successfully.")

# Verify
tables = db.query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for t in tables:
    print(f"  - {t['name']}")
```

- [ ] **Step 3: Test database creation**

Run: `cd C:\Users\seang1121\mortgage-rates-mcp && python scripts/create_database.py`

Expected: prints DB path and lists all 7 tables.

- [ ] **Step 4: Commit**

```bash
git add backend/database.py scripts/create_database.py
git commit -m "feat: database layer with all 7 tables"
```

---

## Task 3: Auth System

**Files:**
- Create: `backend/auth.py`
- Create: `scripts/create_admin.py`

- [ ] **Step 1: Create auth.py**

Must include:
- `generate_api_key(user_id)` — creates `mort_` prefixed key, stores scrypt hash, returns plaintext key once
- `validate_api_key(raw_key)` — checks hash, checks rate limit, returns key record or None
- `create_user(email, password, role='user')` — creates user, returns user dict
- `register_user(email, password)` — creates user + generates API key, returns both
- `check_rate_limit(key_record)` — returns True if under limit (20/day free, unlimited admin)
- `increment_request_count(key_id)` — bumps counter, resets if new day

```python
import secrets
import hashlib
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database import db

KEY_PREFIX = "mort_"
FREE_TIER_LIMIT = 20


def generate_api_key(user_id: str) -> str:
    """Generate a mort_* API key. Returns plaintext key (only shown once)."""
    raw = secrets.token_hex(32)
    full_key = f"{KEY_PREFIX}{raw}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    prefix = full_key[:12]

    db.execute(
        """INSERT INTO api_keys (user_id, key_hash, key_prefix, tier, requests_today, last_reset_date)
           VALUES (?, ?, ?, 'free', 0, ?)""",
        (user_id, key_hash, prefix, datetime.now().strftime('%Y-%m-%d'))
    )
    return full_key


def validate_api_key(raw_key: str) -> dict | None:
    """Validate API key. Returns key record with rate_limited flag, or None."""
    if not raw_key or not raw_key.startswith(KEY_PREFIX):
        return None

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    rows = db.query(
        "SELECT ak.*, u.role FROM api_keys ak JOIN users u ON ak.user_id = u.id WHERE ak.key_hash = ? AND ak.revoked_at IS NULL",
        (key_hash,)
    )
    if not rows:
        return None

    record = rows[0]
    today = datetime.now().strftime('%Y-%m-%d')

    # Reset counter if new day
    if record['last_reset_date'] != today:
        db.execute(
            "UPDATE api_keys SET requests_today = 0, last_reset_date = ? WHERE id = ?",
            (today, record['id'])
        )
        record['requests_today'] = 0

    # Check rate limit (admin = unlimited)
    if record['role'] != 'admin' and record['requests_today'] >= FREE_TIER_LIMIT:
        record['rate_limited'] = True
    else:
        record['rate_limited'] = False
        db.execute(
            "UPDATE api_keys SET requests_today = requests_today + 1 WHERE id = ?",
            (record['id'],)
        )

    return record


def create_user(email: str, password: str, role: str = 'user') -> dict:
    """Create a user account. Returns user dict."""
    user_id = secrets.token_hex(16)
    pw_hash = generate_password_hash(password, method='scrypt', salt_length=32)
    db.execute(
        "INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (user_id, email, pw_hash, role)
    )
    return {'id': user_id, 'email': email, 'role': role}


def register_user(email: str, password: str) -> tuple[dict, str]:
    """Create user + generate API key. Returns (user_dict, plaintext_api_key)."""
    user = create_user(email, password)
    api_key = generate_api_key(user['id'])
    return user, api_key
```

- [ ] **Step 2: Create scripts/create_admin.py**

```python
"""Create admin user and print API key."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from backend.auth import create_user, generate_api_key

email = input("Admin email: ").strip()
password = input("Admin password: ").strip()

if not email or not password:
    print("Email and password required.")
    sys.exit(1)

user = create_user(email, password, role='admin')
api_key = generate_api_key(user['id'])

# Set admin tier to unlimited
from backend.database import db
db.execute("UPDATE api_keys SET tier = 'admin' WHERE user_id = ?", (user['id'],))

print(f"\nAdmin user created:")
print(f"  Email: {email}")
print(f"  User ID: {user['id']}")
print(f"  API Key: {api_key}")
print(f"\n  SAVE THIS KEY — it cannot be retrieved later.")
```

- [ ] **Step 3: Test admin creation**

Run: `python scripts/create_admin.py`
Enter email + password when prompted. Verify it prints a `mort_*` key.

- [ ] **Step 4: Commit**

```bash
git add backend/auth.py scripts/create_admin.py
git commit -m "feat: auth system with mort_* API keys and open registration"
```

---

## Task 4: Base Extractor + RateResult + Validators

**Files:**
- Create: `backend/extractors/__init__.py`
- Create: `backend/extractors/base.py`
- Create: `backend/validators.py`

- [ ] **Step 1: Create base.py**

```python
"""Base class for all lender extractors."""
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class RateResult:
    lender: str
    product: str       # '30yr', '15yr', 'ARM', 'FHA_30yr', 'VA_30yr'
    rate: float
    apr: Optional[float] = None
    is_benchmark: bool = False


class BaseLenderExtractor:
    """Abstract base for lender-specific rate extractors."""
    name: str = ""
    url: str = ""
    is_benchmark: bool = False
    requires_browser: bool = True
    wait_ms: int = 10000

    # Regex patterns shared across extractors (fallback)
    RATE_PATTERNS = [
        # Pattern 1: "label ... X.XXX% ... APR ... X.XXX%"
        r'{label}.*?(\d\.\d{{2,3}})%.*?(?:APR|apr)[:\s]*(\d\.\d{{2,3}})%',
        # Pattern 2: "label <tab/space> X.XXX% <tab/space> X.XXX%"
        r'{label}[\t\s]+(\d\.\d{{2,3}})%[\t\s]+(\d\.\d{{2,3}})%',
        # Pattern 3: "label ... is X.XXX% (X.XXX% APR)"
        r'{label}.*?is\s+(\d\.\d{{2,3}})%\s*\((\d\.\d{{2,3}})%\s*APR\)',
        # Pattern 4: "label ... Rate ... X.XXX% ... APR ... X.XXX%" (Mr. Cooper style)
        r'{label}.*?Rate.*?(\d\.\d{{2,3}})%.*?APR.*?(\d\.\d{{2,3}})%',
    ]
    # Rate-only fallback (no APR)
    RATE_ONLY_PATTERN = r'{label}[^\d]*?(\d\.\d{{2,3}})%'

    PRODUCT_LABELS = {
        '30yr': r'30[- ]?[Yy]ear(?:\s*[Ff]ixed)?',
        '15yr': r'15[- ]?[Yy]ear(?:\s*[Ff]ixed)?',
        'ARM': r'(?:7/6|7/1|5/1)\s*(?:ARM|Adj)',
        'FHA_30yr': r'FHA\s*30[- ]?[Yy]ear',
        'VA_30yr': r'VA\s*30[- ]?[Yy]ear',
    }

    def extract(self, page_content: str) -> list[RateResult]:
        """Extract rates from page text. Override for lender-specific logic."""
        return self._regex_extract(page_content)

    def _regex_extract(self, text: str) -> list[RateResult]:
        """Fallback regex extraction shared across all lenders."""
        results = []
        for product, label_pattern in self.PRODUCT_LABELS.items():
            found = False
            for pattern_template in self.RATE_PATTERNS:
                pattern = pattern_template.format(label=label_pattern)
                m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if m:
                    results.append(RateResult(
                        lender=self.name, product=product,
                        rate=float(m.group(1)), apr=float(m.group(2)),
                        is_benchmark=self.is_benchmark
                    ))
                    found = True
                    break
            if not found:
                # Try rate-only fallback
                pattern = self.RATE_ONLY_PATTERN.format(label=label_pattern)
                m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if m and 2.5 <= float(m.group(1)) <= 14.0:
                    results.append(RateResult(
                        lender=self.name, product=product,
                        rate=float(m.group(1)), apr=None,
                        is_benchmark=self.is_benchmark
                    ))
        return results

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Scrape this lender's page. Override for custom interaction logic."""
        try:
            ctx = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = await ctx.new_page()
            await page.goto(self.url, timeout=25000, wait_until="domcontentloaded")
            await page.wait_for_timeout(self.wait_ms)

            # Try ZIP input if present
            await self._try_zip_input(page, zip_code)

            text = await page.inner_text("body")
            await ctx.close()
            return self.extract(text)
        except Exception:
            try:
                await ctx.close()
            except Exception:
                pass
            return []

    async def _try_zip_input(self, page, zip_code: str):
        """Auto-detect and fill ZIP code fields."""
        for sel in ['input[name*="zip" i]', 'input[placeholder*="ZIP" i]', 'input[id*="zip" i]']:
            el = await page.query_selector(sel)
            if el:
                await el.fill(zip_code)
                await page.wait_for_timeout(500)
                for btn_sel in ['button[type="submit"]', 'button:has-text("Update")', 'button:has-text("Get")', 'button:has-text("View")', 'button:has-text("See")']:
                    btn = await page.query_selector(btn_sel)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(5000)
                        break
                break
```

- [ ] **Step 2: Create extractors/__init__.py**

```python
"""Lender extractor registry."""
from backend.extractors.base import BaseLenderExtractor, RateResult

__all__ = ['BaseLenderExtractor', 'RateResult']
```

- [ ] **Step 3: Create validators.py**

```python
"""Rate validation pipeline — sanity bounds, cross-reference, staleness detection."""
from backend.extractors.base import RateResult
from backend.database import db

RATE_FLOOR = 2.5
RATE_CEILING = 14.0
BENCHMARK_DEVIATION_MAX = 1.5

DISCLAIMER = (
    "Rates shown are publicly advertised rates scraped from lender websites and are not "
    "personalized quotes. Actual rates depend on credit score, loan amount, property type, "
    "down payment, and other factors. This is not financial advice. Contact lenders directly "
    "for official quotes."
)


def validate_rate(rate: RateResult) -> tuple[bool, str]:
    """Validate a single rate. Returns (is_valid, reason)."""
    if not (RATE_FLOOR <= rate.rate <= RATE_CEILING):
        return False, f"Rate {rate.rate}% outside bounds [{RATE_FLOOR}-{RATE_CEILING}]"
    if rate.apr is not None and not (RATE_FLOOR <= rate.apr <= RATE_CEILING + 2):
        return False, f"APR {rate.apr}% outside bounds"
    if rate.apr is not None and rate.apr < rate.rate:
        return False, f"APR {rate.apr}% lower than rate {rate.rate}% (impossible)"
    return True, "OK"


def validate_product_consistency(rates: list[RateResult]) -> list[RateResult]:
    """Check that 30yr > 15yr for same lender. Flag violations but don't reject."""
    by_lender = {}
    for r in rates:
        by_lender.setdefault(r.lender, {})[r.product] = r

    flagged = []
    for lender, products in by_lender.items():
        if '30yr' in products and '15yr' in products:
            if products['15yr'].rate >= products['30yr'].rate:
                flagged.append(lender)
    return flagged


def cross_reference_benchmarks(rates: list[RateResult]) -> list[RateResult]:
    """Flag rates that deviate too far from benchmark averages."""
    benchmarks = [r for r in rates if r.is_benchmark]
    lender_rates = [r for r in rates if not r.is_benchmark]

    if not benchmarks:
        return lender_rates

    # Get benchmark average per product
    bench_avg = {}
    for b in benchmarks:
        bench_avg.setdefault(b.product, []).append(b.rate)
    bench_avg = {p: sum(rs) / len(rs) for p, rs in bench_avg.items()}

    valid = []
    for r in lender_rates:
        avg = bench_avg.get(r.product)
        if avg and abs(r.rate - avg) > BENCHMARK_DEVIATION_MAX:
            continue  # skip — too far from benchmark
        valid.append(r)
    return valid + benchmarks


def check_staleness(lender: str, product: str, rate: float) -> bool:
    """Check if this exact rate has appeared in the last 5 scrapes. Returns True if stale."""
    rows = db.query(
        """SELECT rate FROM rate_history
           WHERE lender = ? AND product = ?
           ORDER BY created_at DESC LIMIT 5""",
        (lender, product)
    )
    if len(rows) >= 5 and all(r['rate'] == rate for r in rows):
        return True
    return False
```

- [ ] **Step 4: Commit**

```bash
git add backend/extractors/__init__.py backend/extractors/base.py backend/validators.py
git commit -m "feat: base extractor, RateResult dataclass, validation pipeline"
```

---

## Task 5: Tier 1 Extractors (Freddie Mac + MND + PennyMac + Citizens)

**Files:**
- Create: `backend/extractors/freddie_mac.py`
- Create: `backend/extractors/mnd.py`
- Create: `backend/extractors/pennymac.py`
- Create: `backend/extractors/citizens.py`

- [ ] **Step 1: Create freddie_mac.py**

Adapt directly from existing `fetch_freddie_mac_csv()` in `mortgage_rate_report.py`.

```python
"""Freddie Mac PMMS — national benchmark via CSV endpoint. No browser needed."""
import ssl
import urllib.request
from backend.extractors.base import BaseLenderExtractor, RateResult


class FreddieMacExtractor(BaseLenderExtractor):
    name = "Freddie Mac (natl avg)"
    url = "https://www.freddiemac.com/pmms/docs/PMMS_history.csv"
    is_benchmark = True
    requires_browser = False

    def fetch(self) -> list[RateResult]:
        """Fetch rates via direct CSV download. No browser needed."""
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                lines = r.read().decode().strip().split("\n")
            last = lines[-1].split(",")
            results = []
            if len(last) >= 2 and last[1]:
                results.append(RateResult(
                    lender=self.name, product="30yr",
                    rate=float(last[1]), apr=None, is_benchmark=True
                ))
            if len(last) >= 4 and last[3]:
                results.append(RateResult(
                    lender=self.name, product="15yr",
                    rate=float(last[3]), apr=None, is_benchmark=True
                ))
            return results
        except Exception:
            return []

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Override — no browser needed, use direct fetch."""
        return self.fetch()
```

- [ ] **Step 2: Create mnd.py**

Adapt from existing `fetch_mnd_urllib()`.

```python
"""Mortgage News Daily — daily index via HTML. No browser needed."""
import re
import ssl
import urllib.request
from backend.extractors.base import BaseLenderExtractor, RateResult


class MNDExtractor(BaseLenderExtractor):
    name = "MND Index"
    url = "https://www.mortgagenewsdaily.com/mortgage-rates"
    is_benchmark = True
    requires_browser = False

    def fetch(self) -> list[RateResult]:
        """Fetch rates via plain HTTP + HTML parsing."""
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                html = r.read().decode("utf-8", errors="replace")
            text = re.sub(r'<[^>]+>', ' ', html)
            return self.extract(text)
        except Exception:
            return []

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Override — no browser needed, use direct fetch."""
        return self.fetch()
```

- [ ] **Step 3: Create pennymac.py**

PennyMac has a clean public REST API — no browser, no auth needed.

```python
"""PennyMac — REST JSON API. No browser needed."""
import json
import ssl
import urllib.request
from backend.extractors.base import BaseLenderExtractor, RateResult


class PennyMacExtractor(BaseLenderExtractor):
    name = "PennyMac"
    url = "https://quote.pennymac.com/api/v1/rate-sheet/stored/conventional-home-loans"
    requires_browser = False

    ENDPOINTS = {
        "conventional": "https://quote.pennymac.com/api/v1/rate-sheet/stored/conventional-home-loans",
        "fha": "https://quote.pennymac.com/api/v1/rate-sheet/stored/fha-home-loans",
        "va": "https://quote.pennymac.com/api/v1/rate-sheet/stored/va-purchase",
        "jumbo": "https://quote.pennymac.com/api/v1/rate-sheet/stored/jumbo-loans",
    }

    # Map PennyMac product names to our standard product keys
    PRODUCT_MAP = {
        "Conventional 30 Year Fixed": "30yr",
        "Conventional 15 Year Fixed": "15yr",
        "FHA 30 Year Fixed": "FHA_30yr",
        "VA 30 Year Fixed": "VA_30yr",
    }

    def fetch(self) -> list[RateResult]:
        """Fetch rates from all PennyMac endpoints."""
        results = []
        ctx = ssl.create_default_context()
        for endpoint_url in self.ENDPOINTS.values():
            try:
                req = urllib.request.Request(endpoint_url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                })
                with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                    data = json.loads(r.read().decode())
                for rate_item in data.get("bestRates", []):
                    product = self._map_product(rate_item.get("name", ""))
                    if product:
                        results.append(RateResult(
                            lender=self.name,
                            product=product,
                            rate=float(rate_item["rate"]),
                            apr=float(rate_item.get("apr")) if rate_item.get("apr") else None,
                        ))
            except Exception:
                continue
        return results

    def _map_product(self, name: str) -> str | None:
        """Map PennyMac product name to standard key."""
        for pm_name, key in self.PRODUCT_MAP.items():
            if pm_name.lower() in name.lower():
                return key
        if "arm" in name.lower() or "adjustable" in name.lower():
            return "ARM"
        return None

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        return self.fetch()
```

- [ ] **Step 4: Create citizens.py**

Citizens Bank publishes a static JSON file — no browser, no auth.

```python
"""Citizens Bank — static JSON file. No browser needed. Rates regionalized by state."""
import json
import ssl
import urllib.request
from backend.extractors.base import BaseLenderExtractor, RateResult


class CitizensExtractor(BaseLenderExtractor):
    name = "Citizens Bank"
    url = "https://www.citizensbank.com/assets/CB_resources/json/rates/Mortgage.json"
    requires_browser = False

    PRODUCT_MAP = {
        "30 Year Fixed Rate": "30yr",
        "20 Year Fixed Rate": "30yr",  # fallback if no 30yr
        "15 Year Fixed Rate": "15yr",
        "10 Year Fixed Rate": "15yr",  # fallback
    }

    def fetch(self, region: str = "RI") -> list[RateResult]:
        """Fetch rates from static JSON. Region = state code (e.g., 'RI', 'OH', 'CT')."""
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                data = json.loads(r.read().decode())

            results = []
            for brand_entry in data:
                for region_data in brand_entry.get("BrandData", []):
                    if region_data.get("RegionCode") != region:
                        continue
                    for group_wrapper in region_data.get("RegionData", {}).get("GROUPS", []):
                        for group in group_wrapper.get("GROUP", []):
                            group_name = group.get("NAME", "")
                            if "Purchase" not in group_name:
                                continue
                            for product in group.get("PRODUCT", []):
                                descr = product.get("Descr", "")
                                std_product = self._map_product(descr)
                                if not std_product:
                                    continue
                                rate_str = product.get("RATE", "").replace("%", "")
                                apr_str = product.get("APR", "").replace("%", "")
                                try:
                                    results.append(RateResult(
                                        lender=self.name,
                                        product=std_product,
                                        rate=float(rate_str),
                                        apr=float(apr_str) if apr_str else None,
                                    ))
                                except (ValueError, TypeError):
                                    continue
            return results
        except Exception:
            return []

    def _map_product(self, descr: str) -> str | None:
        for pattern, key in self.PRODUCT_MAP.items():
            if pattern.lower() in descr.lower():
                return key
        if "arm" in descr.lower() or "adjustable" in descr.lower():
            return "ARM"
        return None

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        return self.fetch()
```

- [ ] **Step 5: Test all 4 Tier 1 extractors**

```bash
python -c "
from backend.extractors.freddie_mac import FreddieMacExtractor
from backend.extractors.mnd import MNDExtractor
from backend.extractors.pennymac import PennyMacExtractor
from backend.extractors.citizens import CitizensExtractor

for ExtClass in [FreddieMacExtractor, MNDExtractor, PennyMacExtractor, CitizensExtractor]:
    ext = ExtClass()
    results = ext.fetch() if hasattr(ext, 'fetch') else []
    print(f'{ext.name}: {len(results)} rates')
    for r in results:
        apr_str = f' ({r.apr}% APR)' if r.apr else ''
        print(f'  {r.product}: {r.rate}%{apr_str}')
    print()
"
```

Expected: All 4 return rates. PennyMac should return conv + FHA + VA + jumbo. Citizens should return 30yr + 15yr + ARM.

- [ ] **Step 6: Commit**

```bash
git add backend/extractors/freddie_mac.py backend/extractors/mnd.py backend/extractors/pennymac.py backend/extractors/citizens.py
git commit -m "feat: Tier 1 extractors — Freddie Mac, MND, PennyMac API, Citizens JSON"
```

---

## Task 6: Tier 2 + Tier 3 Browser Extractors (15 Lenders)

**Files:**
- Create: `backend/extractors/bank_of_america.py`
- Create: `backend/extractors/wells_fargo.py`
- Create: `backend/extractors/chase.py`
- Create: `backend/extractors/citi.py`
- Create: `backend/extractors/navy_federal.py`
- Create: `backend/extractors/sofi.py`
- Create: `backend/extractors/us_bank.py`
- Create: `backend/extractors/guaranteed_rate.py`
- Create: `backend/extractors/truist.py`
- Create: `backend/extractors/mr_cooper.py`
- Create: `backend/extractors/rocket_mortgage.py`
- Create: `backend/extractors/pnc.py`
- Create: `backend/extractors/usaa.py`
- Create: `backend/extractors/flagstar.py`
- Create: `backend/extractors/loandepot.py`

Each extractor inherits `BaseLenderExtractor` and sets `name`, `url`, and optionally overrides `extract()` or `scrape()` for lender-specific logic.

- [ ] **Step 1: Create all 10 extractor files**

Use the URLs from the existing `BROWSER_SOURCES` list. Most use the default `scrape()` from base. Chase gets CDP fallback. Mr. Cooper gets the custom Rate/APR pattern.

Example for `bank_of_america.py`:
```python
"""Bank of America — stealth browser, promo URL."""
from backend.extractors.base import BaseLenderExtractor


class BankOfAmericaExtractor(BaseLenderExtractor):
    name = "Bank of America"
    url = "https://promotions.bankofamerica.com/homeloans/homebuying-hub/home-loan-options?subCampCode=41490&dmcode=18099675931"
    wait_ms = 10000
```

Example for `chase.py` (with CDP fallback):
```python
"""Chase — stealth browser + optional CDP fallback via OpenClaw."""
from backend.extractors.base import BaseLenderExtractor, RateResult


class ChaseExtractor(BaseLenderExtractor):
    name = "Chase"
    url = "https://www.chase.com/personal/mortgage/mortgage-rates"
    wait_ms = 12000

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Try standard scrape first, fall back to CDP if available."""
        results = await super().scrape(browser, zip_code)
        if results:
            return results
        return await self._try_cdp_fallback(zip_code)

    async def _try_cdp_fallback(self, zip_code: str) -> list[RateResult]:
        """Connect to OpenClaw browser via CDP for Chase's anti-bot protection."""
        try:
            from patchright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = await context.new_page()
                await page.goto(self.url, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                await self._try_zip_input(page, zip_code)
                try:
                    await page.wait_for_function(
                        "() => { const t = document.querySelector('table'); return t && t.innerText.includes('%'); }",
                        timeout=10000
                    )
                except Exception:
                    pass
                table_text = await page.evaluate("""() => {
                    const el = document.querySelector('table') ||
                               document.querySelector('[class*="rate"]') ||
                               document.querySelector('[data-testid*="rate"]');
                    return el ? el.innerText : '';
                }""")
                await page.close()
                if table_text and "%" in table_text:
                    return self.extract(table_text)
        except Exception:
            pass
        return []
```

Example for `mr_cooper.py` (custom wait):
```python
"""Mr. Cooper — stealth browser, async rate table rendering."""
from backend.extractors.base import BaseLenderExtractor


class MrCooperExtractor(BaseLenderExtractor):
    name = "Mr. Cooper"
    url = "https://www.mrcooper.com/get-started/rates?internal_ref=rates_home"
    wait_ms = 12000
```

Create the remaining Tier 2 lenders (`wells_fargo.py`, `citi.py`, `navy_federal.py`, `sofi.py`, `us_bank.py`, `guaranteed_rate.py`, `truist.py`) following the same pattern — set `name`, `url`, and `wait_ms`. Use default `scrape()` from base.

Tier 2 URLs:
- Wells Fargo: `https://www.wellsfargo.com/mortgage/rates/`
- Citi: `https://www.citi.com/mortgage/purchase-rates`
- Navy Federal CU: `https://www.navyfederal.org/loans-cards/mortgage/mortgage-rates/`
- SoFi: `https://www.sofi.com/home-loans/mortgage-rates/`
- US Bank: `https://www.usbank.com/home-loans/mortgage/mortgage-rates.html`
- Guaranteed Rate: `https://www.rate.com/mortgage-rates`
- Truist: `https://www.truist.com/mortgage/current-mortgage-rates`

- [ ] **Step 2: Create Tier 3 extractors (heavy anti-bot)**

**`rocket_mortgage.py`** — Akamai, SSR page with rates in initial HTML:
```python
"""Rocket Mortgage — #1 retail lender. Akamai protection, SSR page."""
from backend.extractors.base import BaseLenderExtractor


class RocketMortgageExtractor(BaseLenderExtractor):
    name = "Rocket Mortgage"
    url = "https://www.rocketmortgage.com/mortgage-rates"
    wait_ms = 15000  # extra time for Akamai sensor + JS hydration
```

**`pnc.py`** — Akamai, rates behind interactive form:
```python
"""PNC Bank — Akamai protection, rates require form fill."""
from backend.extractors.base import BaseLenderExtractor, RateResult


class PNCExtractor(BaseLenderExtractor):
    name = "PNC"
    url = "https://www.pnc.com/en/personal-banking/borrowing/home-lending/mortgage-loans/mortgage-rates.html"
    wait_ms = 15000

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Fill rate form with default values and extract results."""
        try:
            ctx = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = await ctx.new_page()
            await page.goto(self.url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(self.wait_ms)

            # Fill form fields if present
            for field_sel, value in [
                ('input[name*="homeValue" i], input[id*="homeValue" i]', '400000'),
                ('input[name*="downPayment" i], input[id*="downPayment" i]', '80000'),
                ('input[name*="zip" i], input[id*="zip" i]', zip_code),
            ]:
                el = await page.query_selector(field_sel)
                if el:
                    await el.fill(value)
                    await page.wait_for_timeout(300)

            # Try to submit / click "See rates"
            for btn_sel in ['button:has-text("See")', 'button:has-text("Get")', 'button[type="submit"]']:
                btn = await page.query_selector(btn_sel)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(8000)
                    break

            text = await page.inner_text("body")
            await ctx.close()
            return self.extract(text)
        except Exception:
            try:
                await ctx.close()
            except Exception:
                pass
            return []
```

**`usaa.py`** — Heavy Akamai, needs stealth:
```python
"""USAA — Heavy Akamai Bot Manager. VA loan specialist."""
from backend.extractors.base import BaseLenderExtractor


class USAAExtractor(BaseLenderExtractor):
    name = "USAA"
    url = "https://www.usaa.com/bank/mortgage-rates"
    wait_ms = 20000  # extra time for heavy Akamai sensor validation
```

**`flagstar.py`** — Cloudflare, form-gated:
```python
"""Flagstar Bank (NYCB) — Cloudflare protection, rates behind form."""
from backend.extractors.base import BaseLenderExtractor, RateResult


class FlagstarExtractor(BaseLenderExtractor):
    name = "Flagstar"
    url = "https://www.flagstar.com/personal/borrow/home-loans/mortgage-rates.html"
    wait_ms = 15000

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Fill rate form and extract results after Cloudflare challenge."""
        try:
            ctx = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = await ctx.new_page()
            await page.goto(self.url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(self.wait_ms)

            # Fill purchase form fields
            for field_sel, value in [
                ('input[name*="purchasePrice" i]', '400000'),
                ('input[name*="downPayment" i]', '80000'),
                ('input[name*="zip" i], input[name*="Zipcode" i]', zip_code),
            ]:
                el = await page.query_selector(field_sel)
                if el:
                    await el.fill(value)
                    await page.wait_for_timeout(300)

            # Submit form
            for btn_sel in ['button:has-text("Submit")', 'button:has-text("See")', 'input[type="submit"]']:
                btn = await page.query_selector(btn_sel)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(8000)
                    break

            text = await page.inner_text("body")
            await ctx.close()
            return self.extract(text)
        except Exception:
            try:
                await ctx.close()
            except Exception:
                pass
            return []
```

**`loandepot.py`** — reCAPTCHA v3, Angular SPA:
```python
"""LoanDepot — reCAPTCHA v3 + Angular SPA. Stealth browser may pass score."""
from backend.extractors.base import BaseLenderExtractor


class LoanDepotExtractor(BaseLenderExtractor):
    name = "LoanDepot"
    url = "https://www.loandepot.com/mortgage-rates"
    wait_ms = 15000  # extra time for Angular hydration + reCAPTCHA
```

- [ ] **Step 3: Update extractors/__init__.py with full registry**

```python
"""Lender extractor registry — 19 lenders + 2 benchmarks."""
from backend.extractors.base import BaseLenderExtractor, RateResult
from backend.extractors.freddie_mac import FreddieMacExtractor
from backend.extractors.mnd import MNDExtractor
from backend.extractors.pennymac import PennyMacExtractor
from backend.extractors.citizens import CitizensExtractor
from backend.extractors.bank_of_america import BankOfAmericaExtractor
from backend.extractors.wells_fargo import WellsFargoExtractor
from backend.extractors.chase import ChaseExtractor
from backend.extractors.citi import CitiExtractor
from backend.extractors.navy_federal import NavyFederalExtractor
from backend.extractors.sofi import SoFiExtractor
from backend.extractors.us_bank import USBankExtractor
from backend.extractors.guaranteed_rate import GuaranteedRateExtractor
from backend.extractors.truist import TruistExtractor
from backend.extractors.mr_cooper import MrCooperExtractor
from backend.extractors.rocket_mortgage import RocketMortgageExtractor
from backend.extractors.pnc import PNCExtractor
from backend.extractors.usaa import USAAExtractor
from backend.extractors.flagstar import FlagstarExtractor
from backend.extractors.loandepot import LoanDepotExtractor

# Tier 1 — no browser needed (direct API/JSON)
TIER1_EXTRACTORS = [
    FreddieMacExtractor(), MNDExtractor(),
    PennyMacExtractor(), CitizensExtractor(),
]

# Tier 2 — stealth browser, low protection
TIER2_EXTRACTORS = [
    BankOfAmericaExtractor(), WellsFargoExtractor(), CitiExtractor(),
    NavyFederalExtractor(), SoFiExtractor(), USBankExtractor(),
    GuaranteedRateExtractor(), TruistExtractor(), MrCooperExtractor(),
]

# Tier 3 — stealth browser, heavy anti-bot
TIER3_EXTRACTORS = [
    ChaseExtractor(), RocketMortgageExtractor(), PNCExtractor(),
    USAAExtractor(), FlagstarExtractor(), LoanDepotExtractor(),
]

ALL_EXTRACTORS = TIER1_EXTRACTORS + TIER2_EXTRACTORS + TIER3_EXTRACTORS

__all__ = ['BaseLenderExtractor', 'RateResult',
           'TIER1_EXTRACTORS', 'TIER2_EXTRACTORS', 'TIER3_EXTRACTORS', 'ALL_EXTRACTORS']
```

- [ ] **Step 4: Commit**

```bash
git add backend/extractors/
git commit -m "feat: all 21 extractors — 4 Tier 1 (API) + 9 Tier 2 (easy) + 6 Tier 3 (anti-bot)"
```

---

## Task 7: Scraper Orchestrator

**Files:**
- Create: `backend/scraper.py`

- [ ] **Step 1: Create scraper.py**

Orchestrates the full scrape cycle: Tier 1 first (instant), then Tier 2 in batches of 4 with retry. Stores results in DB. Logs per-lender status to `scrape_logs`. Takes screenshots on failure.

```python
"""Scrape orchestrator — runs all extractors, validates, stores results."""
import asyncio
import os
import secrets
from datetime import datetime
from backend.database import db
from backend.extractors import TIER1_EXTRACTORS, TIER2_EXTRACTORS
from backend.extractors.base import RateResult
from backend.validators import validate_rate, cross_reference_benchmarks, check_staleness

BATCH_SIZE = 4
MAX_RETRIES = 3
WAIT_SCHEDULE = [8000, 12000, 15000]
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")


def run_scrape(zip_code: str = None) -> dict:
    """Run a full scrape cycle. Returns summary dict."""
    zip_code = zip_code or os.getenv("DEFAULT_ZIP_CODE", "32224")
    return asyncio.run(_async_scrape(zip_code))


async def _async_scrape(zip_code: str) -> dict:
    session_id = secrets.token_hex(8)
    now = datetime.now()
    time_of_day = "AM" if now.hour < 12 else "PM"
    scraped_at = now.isoformat()

    all_rates: list[RateResult] = []
    successes = []
    failures = []

    # Tier 1: Direct APIs (no browser)
    for extractor in TIER1_EXTRACTORS:
        start = datetime.now()
        try:
            rates = await extractor.scrape(None, zip_code)
            duration = int((datetime.now() - start).total_seconds() * 1000)
            if rates:
                all_rates.extend(rates)
                successes.append(extractor.name)
                _log_scrape(session_id, extractor.name, "success", len(rates), duration)
            else:
                failures.append(extractor.name)
                _log_scrape(session_id, extractor.name, "failed", 0, duration, "No rates returned")
        except Exception as e:
            duration = int((datetime.now() - start).total_seconds() * 1000)
            failures.append(extractor.name)
            _log_scrape(session_id, extractor.name, "failed", 0, duration, str(e))

    # Tier 2: Browser scraping in batches
    from patchright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)

        failed_extractors = []

        # Process in batches
        for batch_start in range(0, len(TIER2_EXTRACTORS), BATCH_SIZE):
            batch = TIER2_EXTRACTORS[batch_start:batch_start + BATCH_SIZE]
            tasks = [_scrape_with_logging(extractor, browser, zip_code, session_id) for extractor in batch]
            results = await asyncio.gather(*tasks)

            for extractor, rates in zip(batch, results):
                if rates:
                    all_rates.extend(rates)
                    successes.append(extractor.name)
                else:
                    failed_extractors.append(extractor)

        # Retry failures sequentially with increasing wait
        for extractor in failed_extractors:
            for attempt in range(MAX_RETRIES):
                extractor.wait_ms = WAIT_SCHEDULE[min(attempt, len(WAIT_SCHEDULE) - 1)]
                start = datetime.now()
                try:
                    rates = await extractor.scrape(browser, zip_code)
                    duration = int((datetime.now() - start).total_seconds() * 1000)
                    if rates:
                        all_rates.extend(rates)
                        successes.append(extractor.name)
                        _log_scrape(session_id, extractor.name, "success", len(rates), duration,
                                    f"Succeeded on retry {attempt + 1}")
                        break
                except Exception:
                    pass
            else:
                failures.append(extractor.name)
                # Screenshot on final failure
                screenshot_path = await _take_screenshot(browser, extractor, zip_code)
                _log_scrape(session_id, extractor.name, "failed", 0, 0,
                            "All retries exhausted", screenshot_path)

        await browser.close()

    # Validate all rates
    validated = []
    for rate in all_rates:
        is_valid, reason = validate_rate(rate)
        if is_valid:
            validated.append(rate)

    # Cross-reference against benchmarks
    validated = cross_reference_benchmarks(validated)

    # Deduplicate (keep first per lender+product)
    seen = set()
    unique = []
    for r in validated:
        key = (r.lender, r.product)
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # Store in database
    _store_rates(unique, zip_code, scraped_at, session_id, time_of_day)

    # Handle last-known-good fallback for failed lenders
    _apply_fallbacks(failures, zip_code, scraped_at, session_id)

    return {
        "session_id": session_id,
        "total_rates": len(unique),
        "successes": successes,
        "failures": failures,
        "scraped_at": scraped_at,
        "time_of_day": time_of_day,
    }


async def _scrape_with_logging(extractor, browser, zip_code, session_id) -> list[RateResult]:
    """Scrape a single extractor with timing and logging."""
    start = datetime.now()
    try:
        rates = await extractor.scrape(browser, zip_code)
        duration = int((datetime.now() - start).total_seconds() * 1000)
        status = "success" if rates else "failed"
        _log_scrape(session_id, extractor.name, status, len(rates), duration)
        return rates
    except Exception as e:
        duration = int((datetime.now() - start).total_seconds() * 1000)
        _log_scrape(session_id, extractor.name, "failed", 0, duration, str(e))
        return []


async def _take_screenshot(browser, extractor, zip_code) -> str | None:
    """Capture screenshot of failed lender page for debugging."""
    try:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        await page.goto(extractor.url, timeout=15000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        filename = f"{extractor.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join(SCREENSHOT_DIR, filename)
        await page.screenshot(path=path)
        await ctx.close()
        return path
    except Exception:
        return None


def _log_scrape(session_id, lender, status, rates_found, duration_ms, error=None, screenshot=None):
    """Write to scrape_logs table."""
    db.execute(
        """INSERT INTO scrape_logs (scrape_session, lender, status, rates_found, error_message, screenshot_path, duration_ms)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (session_id, lender, status, rates_found, error, screenshot, duration_ms)
    )


def _store_rates(rates, zip_code, scraped_at, session_id, time_of_day):
    """Store validated rates in both rates and rate_history tables."""
    today = datetime.now().strftime('%Y-%m-%d')

    with db.get_connection() as conn:
        # Clear previous latest rates and insert new
        conn.execute("DELETE FROM rates WHERE scrape_session != ?", (session_id,))

        for r in rates:
            stale = 1 if check_staleness(r.lender, r.product, r.rate) else 0
            conn.execute(
                """INSERT INTO rates (lender, product, rate, apr, zip_code, is_benchmark, stale, scraped_at, scrape_session)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (r.lender, r.product, r.rate, r.apr, zip_code, int(r.is_benchmark), stale, scraped_at, session_id)
            )
            conn.execute(
                """INSERT INTO rate_history (date, time_of_day, lender, product, rate, apr, zip_code)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (today, time_of_day, r.lender, r.product, r.rate, r.apr, zip_code)
            )
        conn.commit()

    # Prune history older than 90 days
    db.execute("DELETE FROM rate_history WHERE date < date('now', '-90 days')")


def _apply_fallbacks(failures, zip_code, scraped_at, session_id):
    """For failed lenders, copy their last known good rates with stale=1."""
    for lender in failures:
        last_good = db.query(
            """SELECT lender, product, rate, apr FROM rate_history
               WHERE lender = ? ORDER BY created_at DESC LIMIT 5""",
            (lender,)
        )
        seen = set()
        for r in last_good:
            key = (r['lender'], r['product'])
            if key in seen:
                continue
            seen.add(key)
            db.execute(
                """INSERT INTO rates (lender, product, rate, apr, zip_code, is_benchmark, stale, scraped_at, scrape_session)
                   VALUES (?, ?, ?, ?, ?, 0, 1, ?, ?)""",
                (r['lender'], r['product'], r['rate'], r['apr'], zip_code, scraped_at, session_id)
            )
```

- [ ] **Step 2: Test scraper with Tier 1 only (quick verification)**

```bash
python -c "
from backend.scraper import run_scrape
# This will attempt all lenders — Tier 1 should succeed, Tier 2 depends on patchright
result = run_scrape('32224')
print(f'Rates: {result[\"total_rates\"]}')
print(f'Successes: {result[\"successes\"]}')
print(f'Failures: {result[\"failures\"]}')
"
```

- [ ] **Step 3: Commit**

```bash
git add backend/scraper.py
git commit -m "feat: scraper orchestrator with batch processing, retry, screenshots, fallbacks"
```

---

## Task 8: Calculator Module

**Files:**
- Create: `backend/calculator.py`

- [ ] **Step 1: Create calculator.py**

Pure math — no DB dependency. All functions take rate/amount as input.

```python
"""Mortgage payment calculations — payment, scenarios, savings."""


def monthly_payment(principal: float, annual_rate_pct: float, term_years: int = 30) -> float:
    """Calculate monthly P&I payment."""
    if annual_rate_pct <= 0:
        return principal / (term_years * 12)
    r = annual_rate_pct / 100 / 12
    n = term_years * 12
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def total_interest(principal: float, annual_rate_pct: float, term_years: int = 30) -> float:
    """Total interest paid over the life of the loan."""
    mp = monthly_payment(principal, annual_rate_pct, term_years)
    return (mp * term_years * 12) - principal


def full_calculation(loan_amount: float, annual_rate_pct: float,
                     term_years: int = 30, down_payment_pct: float = 0) -> dict:
    """Full payment breakdown."""
    if down_payment_pct > 0:
        down = loan_amount * (down_payment_pct / 100)
        principal = loan_amount - down
    else:
        down = 0
        principal = loan_amount

    mp = monthly_payment(principal, annual_rate_pct, term_years)
    ti = total_interest(principal, annual_rate_pct, term_years)
    total_cost = principal + ti

    return {
        "loan_amount": round(principal, 2),
        "down_payment": round(down, 2),
        "rate": annual_rate_pct,
        "term_years": term_years,
        "monthly_payment": round(mp, 2),
        "total_interest": round(ti, 2),
        "total_cost": round(total_cost, 2),
    }


def compare_scenarios(loan_amount: float, rates: dict[str, float],
                      down_payment_pct: float = 0) -> list[dict]:
    """Compare multiple loan scenarios side by side.

    rates: {"30yr": 6.5, "15yr": 5.8, "ARM": 6.0}
    """
    terms = {"30yr": 30, "15yr": 15, "ARM": 30}
    results = []
    for product, rate in rates.items():
        term = terms.get(product, 30)
        calc = full_calculation(loan_amount, rate, term, down_payment_pct)
        calc["product"] = product
        results.append(calc)

    # Add breakeven analysis (vs cheapest monthly payment)
    if len(results) > 1:
        cheapest_monthly = min(r["monthly_payment"] for r in results)
        for r in results:
            if r["monthly_payment"] > cheapest_monthly:
                monthly_diff = r["monthly_payment"] - cheapest_monthly
                interest_savings = max(0, max(x["total_interest"] for x in results) - r["total_interest"])
                r["breakeven_months"] = round(interest_savings / monthly_diff) if monthly_diff > 0 else None
            else:
                r["breakeven_months"] = 0

    return results


def estimate_savings(loan_amount: float, from_rate: float, to_rate: float,
                     term_years: int = 30, remaining_years: int = None) -> dict:
    """Calculate savings from switching lenders / refinancing."""
    remaining = remaining_years or term_years
    from_mp = monthly_payment(loan_amount, from_rate, remaining)
    to_mp = monthly_payment(loan_amount, to_rate, remaining)

    monthly_savings = from_mp - to_mp
    annual_savings = monthly_savings * 12
    total_savings = monthly_savings * remaining * 12

    return {
        "from_rate": from_rate,
        "to_rate": to_rate,
        "from_monthly": round(from_mp, 2),
        "to_monthly": round(to_mp, 2),
        "monthly_savings": round(monthly_savings, 2),
        "annual_savings": round(annual_savings, 2),
        "total_savings": round(total_savings, 2),
        "term_years": remaining,
    }
```

- [ ] **Step 2: Create backend/recommender.py**

Ranked recommendation engine — takes borrower profile, queries current rates, returns top picks with explanations.

```python
"""Recommendation engine — ranked picks with explanations for borrower profiles."""
from backend.database import db
from backend.calculator import full_calculation


def get_recommendation(loan_amount: float, credit_score: int = 740,
                       down_payment_pct: float = 20, product: str = None,
                       property_type: str = "single_family",
                       loan_purpose: str = "purchase") -> dict:
    """Generate ranked lender recommendations based on borrower profile."""

    # Fetch current non-stale, non-benchmark rates
    query = """SELECT lender, product, rate, apr, scraped_at
               FROM rates WHERE stale = 0 AND is_benchmark = 0"""
    params = []
    if product:
        query += " AND product = ?"
        params.append(product)
    query += " ORDER BY rate ASC"

    rates = db.query(query, tuple(params))
    if not rates:
        return {"recommendations": [], "message": "No rates available. Try again after the next scrape."}

    # Get benchmark average for context
    benchmarks = db.query(
        "SELECT product, AVG(rate) as avg_rate FROM rates WHERE is_benchmark = 1 GROUP BY product"
    )
    bench_avg = {b['product']: b['avg_rate'] for b in benchmarks}

    # Score and rank
    recommendations = []
    seen_lenders = set()

    for r in rates:
        if r['lender'] in seen_lenders:
            continue
        seen_lenders.add(r['lender'])

        calc = full_calculation(loan_amount, r['rate'],
                                term_years=30 if '30' in r['product'] or r['product'] == 'ARM' else 15,
                                down_payment_pct=down_payment_pct)

        # Compare to benchmark
        benchmark = bench_avg.get(r['product'])
        vs_market = round(r['rate'] - benchmark, 3) if benchmark else None

        # Generate explanation
        why = _explain(r, calc, vs_market, loan_purpose)

        recommendations.append({
            "rank": len(recommendations) + 1,
            "lender": r['lender'],
            "product": r['product'],
            "rate": r['rate'],
            "apr": r['apr'],
            "monthly_payment": calc['monthly_payment'],
            "total_interest": calc['total_interest'],
            "total_cost": calc['total_cost'],
            "vs_market_avg": f"{vs_market:+.3f}%" if vs_market is not None else None,
            "why": why,
            "scraped_at": r['scraped_at'],
        })

        if len(recommendations) >= 5:
            break

    return {
        "recommendations": recommendations,
        "borrower_profile": {
            "loan_amount": loan_amount,
            "credit_score": credit_score,
            "down_payment_pct": down_payment_pct,
            "property_type": property_type,
            "loan_purpose": loan_purpose,
        },
        "rates_as_of": recommendations[0]['scraped_at'] if recommendations else None,
    }


def _explain(rate, calc, vs_market, loan_purpose) -> str:
    """Generate a human-readable explanation for why this lender is recommended."""
    parts = []
    if rate.get('apr') and rate['apr'] < rate['rate'] + 0.3:
        parts.append("Low fees reflected in tight rate-to-APR spread")
    if vs_market is not None and vs_market < -0.1:
        parts.append(f"{abs(vs_market):.3f}% below the national average")
    elif vs_market is not None and vs_market < 0:
        parts.append("Below the national average")
    parts.append(f"${calc['monthly_payment']:,.2f}/month on ${calc['loan_amount']:,.0f}")
    return ". ".join(parts) + "."
```

- [ ] **Step 3: Commit**

```bash
git add backend/calculator.py backend/recommender.py
git commit -m "feat: calculator + recommendation engine with ranked explanations"
```

---

## Task 9: Flask API

**Files:**
- Create: `backend/app.py`

- [ ] **Step 1: Create app.py**

Flask app with all routes from the spec. Port 5001. Auth via `X-API-Key` header. Health endpoint is public. All rate endpoints include the disclaimer.

This is the largest file. Key sections:
- `before_request` auth check (skip for `/api/v1/health` and `/register`)
- `GET /api/v1/health` — public
- `POST /api/v1/register` — open registration, returns user + API key
- `GET /api/v1/rates` — all current rates with optional filters
- `GET /api/v1/rates/best` — best rate per product
- `GET /api/v1/rates/compare` — side by side
- `GET /api/v1/rates/history` — historical trend
- `GET /api/v1/rates/lender/<name>` — single lender
- `GET /api/v1/rates/scenarios` — scenario comparison
- `GET /api/v1/rates/savings` — savings estimation
- `POST /api/v1/calculate` — payment calculator
- `POST /api/v1/recommend` — AI-powered ranked recommendations (uses recommender.py)
- `POST /api/v1/rate-sheet` — generate PNG (Task 11)
- `POST /api/v1/alerts` — create alert
- `GET /api/v1/alerts` — list alerts
- `DELETE /api/v1/alerts/<id>` — remove alert
- `POST /api/v1/admin/scrape` — manual scrape trigger (admin only)

The app.py should import from `database`, `auth`, `calculator`, `validators` (for DISCLAIMER constant), and `scraper`.

Include the disclaimer in every response that contains rate data by adding it to the JSON response dict.

Full code for this file — implement all routes using `db.query()` for reads and `db.execute()` for writes. Each route handler should be 10-30 lines. Use `flask.g.api_key_auth` to store the validated key record from `before_request`.

- [ ] **Step 2: Test basic startup**

```bash
cd C:\Users\seang1121\mortgage-rates-mcp
FLASK_SECRET_KEY=test python -c "
from backend.app import app
print('App created, routes:')
for rule in app.url_map.iter_rules():
    print(f'  {rule.methods} {rule.rule}')
"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app.py
git commit -m "feat: Flask API with all 15 routes, auth, disclaimers"
```

---

## Task 10: Scheduler

**Files:**
- Create: `backend/scheduler.py`

- [ ] **Step 1: Create scheduler.py**

APScheduler with two cron jobs: 7am and 7pm EST. Post-scrape triggers alert checking.

```python
"""Scraper scheduler — 7am and 7pm EST daily."""
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

scheduler = None


def _scrape_job():
    """Run scrape and check alerts."""
    from backend.scraper import run_scrape
    from backend.notifications import check_and_send_alerts

    print(f"[SCRAPER] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — Starting scheduled scrape")
    try:
        result = run_scrape()
        print(f"[SCRAPER] Complete: {result['total_rates']} rates, "
              f"{len(result['successes'])} succeeded, {len(result['failures'])} failed")

        if result['failures']:
            print(f"[SCRAPER] Failures: {', '.join(result['failures'])}")

        # Check rate alerts post-scrape
        check_and_send_alerts()

    except Exception as e:
        print(f"[SCRAPER] Error: {e}")
        import traceback
        traceback.print_exc()


def start_scheduler():
    """Start the 7am/7pm EST scrape scheduler."""
    global scheduler

    if scheduler is not None:
        print("[SCHEDULER] Already running")
        return

    scheduler = BackgroundScheduler(timezone=pytz.timezone('US/Eastern'))

    scheduler.add_job(
        _scrape_job,
        trigger=CronTrigger(hour=7, minute=0, timezone='US/Eastern'),
        id='morning_scrape',
        name='Morning rate scrape (7am EST)',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=600,
    )

    scheduler.add_job(
        _scrape_job,
        trigger=CronTrigger(hour=19, minute=0, timezone='US/Eastern'),
        id='evening_scrape',
        name='Evening rate scrape (7pm EST)',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=600,
    )

    scheduler.start()
    print("[SCHEDULER] Started — 7am and 7pm EST scrape jobs scheduled")
```

- [ ] **Step 2: Wire scheduler into app.py startup**

Add to the bottom of `app.py`:

```python
from backend.scheduler import start_scheduler
start_scheduler()
```

- [ ] **Step 3: Commit**

```bash
git add backend/scheduler.py
git commit -m "feat: APScheduler — 7am/7pm EST scrape cron jobs"
```

---

## Task 11: Rate Sheet Generator

**Files:**
- Create: `backend/rate_sheet.py`

- [ ] **Step 1: Create rate_sheet.py**

Pillow-based PNG generator. Produces a clean card with:
- Title with date/time
- Ranked rates per product
- Best rate highlighted
- Day-over-day change
- Disclaimer at bottom

```python
"""Rate sheet generator — Pillow-based PNG rate card for texting to clients."""
import base64
import io
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from backend.database import db
from backend.validators import DISCLAIMER

# Card dimensions
WIDTH = 800
PADDING = 30
LINE_HEIGHT = 28
HEADER_HEIGHT = 80

# Colors
BG_COLOR = (255, 255, 255)
TEXT_COLOR = (30, 30, 30)
HEADER_COLOR = (15, 82, 186)
BEST_COLOR = (0, 150, 0)
BENCHMARK_COLOR = (120, 120, 120)
DISCLAIMER_COLOR = (160, 160, 160)
BORDER_COLOR = (200, 200, 200)


def generate_rate_sheet(zip_code: str = None, products: list[str] = None,
                        branding_text: str = None) -> str:
    """Generate a rate card PNG. Returns base64-encoded string."""
    products = products or ['30yr', '15yr', 'ARM']

    # Fetch current rates from DB
    rates = db.query("SELECT * FROM rates ORDER BY product, rate ASC")

    # Group by product
    by_product = {}
    for r in rates:
        if r['product'] in products:
            by_product.setdefault(r['product'], []).append(r)

    # Calculate image height
    total_lines = 0
    for product in products:
        product_rates = by_product.get(product, [])
        if product_rates:
            total_lines += 2 + len(product_rates)  # header + blank + rates
    total_lines += 4  # disclaimer lines

    height = HEADER_HEIGHT + PADDING + (total_lines * LINE_HEIGHT) + PADDING + 60

    # Create image
    img = Image.new('RGB', (WIDTH, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Try to load a nice font, fall back to default
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        font_bold = ImageFont.truetype("arialbd.ttf", 16)
        font_header = ImageFont.truetype("arialbd.ttf", 22)
        font_small = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font = ImageFont.load_default()
        font_bold = font
        font_header = font
        font_small = font

    y = PADDING

    # Header
    draw.rectangle([(0, 0), (WIDTH, HEADER_HEIGHT)], fill=HEADER_COLOR)
    title = f"Mortgage Rate Comparison"
    draw.text((PADDING, 15), title, fill=(255, 255, 255), font=font_header)
    subtitle = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    if zip_code:
        subtitle += f"  |  ZIP: {zip_code}"
    draw.text((PADDING, 45), subtitle, fill=(200, 220, 255), font=font)

    y = HEADER_HEIGHT + PADDING

    # Branding
    if branding_text:
        draw.text((PADDING, y), branding_text, fill=TEXT_COLOR, font=font_bold)
        y += LINE_HEIGHT + 5

    # Rate tables per product
    product_labels = {'30yr': '30-Year Fixed', '15yr': '15-Year Fixed', 'ARM': 'ARM',
                      'FHA_30yr': 'FHA 30-Year', 'VA_30yr': 'VA 30-Year'}

    for product in products:
        product_rates = by_product.get(product, [])
        if not product_rates:
            continue

        # Section header
        label = product_labels.get(product, product)
        draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill=BORDER_COLOR, width=1)
        y += 5
        draw.text((PADDING, y), label, fill=HEADER_COLOR, font=font_bold)
        y += LINE_HEIGHT + 3

        # Rate rows
        best_non_benchmark = None
        for r in product_rates:
            if not r.get('is_benchmark') and best_non_benchmark is None:
                best_non_benchmark = r['lender']

            color = TEXT_COLOR
            suffix = ""
            if r.get('is_benchmark'):
                color = BENCHMARK_COLOR
                suffix = "  (benchmark)"
            elif r['lender'] == best_non_benchmark:
                color = BEST_COLOR
                suffix = "  BEST"

            rate_str = f"{r['rate']:.3f}%"
            apr_str = f"  ({r['apr']:.3f}% APR)" if r.get('apr') else ""
            stale_str = "  [stale]" if r.get('stale') else ""

            line = f"  {r['lender']:28s}  {rate_str}{apr_str}{stale_str}{suffix}"
            draw.text((PADDING, y), line, fill=color, font=font)
            y += LINE_HEIGHT

        y += LINE_HEIGHT // 2

    # Disclaimer
    y += 10
    draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill=BORDER_COLOR, width=1)
    y += 8
    disclaimer = "Publicly advertised rates as of " + datetime.now().strftime("%m/%d/%Y %I:%M %p") + ". Not personalized quotes. Contact lenders for official rates."
    # Word wrap disclaimer
    words = disclaimer.split()
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font_small)
        if bbox[2] > WIDTH - 2 * PADDING:
            draw.text((PADDING, y), line, fill=DISCLAIMER_COLOR, font=font_small)
            y += 16
            line = word
        else:
            line = test
    if line:
        draw.text((PADDING, y), line, fill=DISCLAIMER_COLOR, font=font_small)

    # Encode to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()
```

- [ ] **Step 2: Commit**

```bash
git add backend/rate_sheet.py
git commit -m "feat: rate sheet generator — Pillow PNG rate cards for clients"
```

---

## Task 12: Notifications Module

**Files:**
- Create: `backend/notifications.py`

- [ ] **Step 1: Create notifications.py**

Discord webhook + email SMTP alert delivery. Called post-scrape by scheduler.

```python
"""Alert delivery — Discord webhook + email. Called after each scrape."""
import json
import os
import smtplib
import urllib.request
from email.mime.text import MIMEText
from datetime import datetime
from backend.database import db


def check_and_send_alerts():
    """Check all active alerts against current rates and dispatch notifications."""
    alerts = db.query(
        "SELECT ra.*, u.email FROM rate_alerts ra JOIN users u ON ra.user_id = u.id WHERE ra.active = 1"
    )
    if not alerts:
        return

    current_rates = db.query("SELECT * FROM rates WHERE stale = 0")

    for alert in alerts:
        matching_rates = [
            r for r in current_rates
            if r['product'] == alert['product']
            and (alert['lender'] is None or r['lender'] == alert['lender'])
            and r['rate'] <= alert['threshold']
        ]

        if not matching_rates:
            continue

        # Don't re-trigger within 12 hours
        if alert.get('last_triggered_at'):
            last = datetime.fromisoformat(alert['last_triggered_at'])
            if (datetime.now() - last).total_seconds() < 43200:
                continue

        # Get user notification preferences
        prefs = db.query(
            "SELECT * FROM notification_preferences WHERE user_id = ? AND active = 1",
            (alert['user_id'],)
        )

        message = _format_alert_message(alert, matching_rates)

        for pref in prefs:
            if pref['channel'] == 'discord_webhook':
                _send_discord(pref['destination'], message)
            elif pref['channel'] == 'email':
                _send_email(pref['destination'], "Mortgage Rate Alert", message)

        # If no prefs configured, try email from user record
        if not prefs and alert.get('email'):
            _send_email(alert['email'], "Mortgage Rate Alert", message)

        # Update last triggered
        db.execute(
            "UPDATE rate_alerts SET last_triggered_at = ? WHERE id = ?",
            (datetime.now().isoformat(), alert['id'])
        )


def _format_alert_message(alert, matching_rates) -> str:
    """Format alert notification message."""
    lines = [f"Rate Alert: {alert['product']} dropped below {alert['threshold']}%\n"]
    for r in matching_rates:
        apr_str = f" ({r['apr']}% APR)" if r.get('apr') else ""
        lines.append(f"  {r['lender']}: {r['rate']}%{apr_str}")
    lines.append(f"\nAs of {datetime.now().strftime('%I:%M %p %m/%d/%Y')}")
    return "\n".join(lines)


def _send_discord(webhook_url: str, message: str):
    """Send message via Discord webhook."""
    try:
        data = json.dumps({"content": f"```\n{message}\n```"}).encode()
        req = urllib.request.Request(
            webhook_url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[ALERT] Discord send failed: {e}")


def send_discord_alert(message: str):
    """Send to admin Discord webhook (for system alerts like scrape failures)."""
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook:
        _send_discord(webhook, message)


def _send_email(to_addr: str, subject: str, body: str):
    """Send email via SMTP."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")

    if not user or not password:
        print(f"[ALERT] Email not configured, skipping alert to {to_addr}")
        return

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_addr

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
    except Exception as e:
        print(f"[ALERT] Email send failed: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add backend/notifications.py
git commit -m "feat: notification system — Discord webhook + email alerts"
```

---

## Task 13: MCP Package

**Files:**
- Create: `mcp/pyproject.toml`
- Create: `mcp/src/mortgage_rates_mcp/__init__.py`
- Create: `mcp/src/mortgage_rates_mcp/server.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mortgage-rates-mcp"
version = "0.1.0"
description = "MCP server for real-time mortgage rate comparison — 19 lenders, 12 tools, AI-powered rate intelligence for realtors and brokers."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"
authors = [{ name = "seang1121" }]
keywords = ["mcp", "mortgage", "rates", "real-estate", "lending", "broker", "realtor"]
dependencies = ["mcp>=1.0.0"]

[project.scripts]
mortgage-rates-mcp = "mortgage_rates_mcp.server:mcp.run"

[project.urls]
Repository = "https://github.com/seang1121/mortgage-rates-mcp"

[tool.hatch.build.targets.wheel]
packages = ["src/mortgage_rates_mcp"]
```

- [ ] **Step 2: Create __init__.py**

```python
from mortgage_rates_mcp.server import mcp
__all__ = ["mcp"]
```

- [ ] **Step 3: Create server.py**

All 12 MCP tools as thin proxies to the backend API. Same pattern as `sports-betting-mcp`: `_api_get()` and `_api_post()` helpers with `X-API-Key` auth.

Each tool calls the corresponding `/api/v1/` endpoint and formats the response as a readable string. Every tool description includes the disclaimer note: "Returns publicly advertised rates, not personalized quotes."

Tools (12): `get_rates`, `get_best_rate`, `compare_lenders`, `get_rate_history`, `get_lender_details`, `get_system_status`, `calculate_payment`, `generate_rate_sheet`, `set_rate_alert`, `compare_scenarios`, `estimate_savings`, `get_recommendation`.

The `get_recommendation` tool calls `POST /api/v1/recommend` with borrower profile params and returns ranked picks with explanations.

Full implementation following the sports-betting-mcp server.py pattern — `_api_get()`, `_api_post()`, `@mcp.tool()` decorator per tool.

- [ ] **Step 4: Commit**

```bash
git add mcp/
git commit -m "feat: MCP package — 12 tools, PyPI-ready, multi-client compatible"
```

---

## Task 14: README + llms.txt + Final Wiring

**Files:**
- Create: `README.md`
- Create: `llms.txt`
- Modify: `backend/app.py` (add scheduler startup + dotenv loading + llms.txt route)

- [ ] **Step 1: Create README.md**

Cover:
- What it is (one paragraph — 19 lenders, 12 tools, AI-native)
- Quick start (pip install for MCP users, backend setup for self-hosting)
- **Multi-client setup** — config examples for Claude Desktop, ChatGPT Desktop, Cursor, Windsurf, VS Code
- All 12 tools with descriptions
- Full lender list (Tier 1/2/3 breakdown)
- Schedule (7am/7pm EST)
- API key acquisition (open registration)
- Accuracy & validation pipeline description
- Disclaimer
- Competitive advantages vs RateAPI/Bankrate/NerdWallet

- [ ] **Step 1b: Create llms.txt**

```text
# mortgage-rates-mcp

> Real-time mortgage rate comparison across 19 major US lenders + 2 national benchmarks. AI-native MCP server for realtors, brokers, and homebuyers.

## Tools (12)

- get_rates: All current rates by product (30yr, 15yr, ARM, FHA, VA). Optional ZIP filter.
- get_best_rate: Single best rate for a loan type across all lenders.
- compare_lenders: Side-by-side comparison of specific lenders.
- get_rate_history: Trend data up to 90 days with AM/PM tracking.
- get_lender_details: All products from one specific lender.
- get_system_status: Health check — last scrape time, lender count, uptime.
- calculate_payment: Monthly payment, total interest, full amortization breakdown.
- generate_rate_sheet: Client-ready PNG rate card image.
- set_rate_alert: Threshold notification when rates drop below target.
- compare_scenarios: 30yr vs 15yr vs ARM with monthly payments and breakeven.
- estimate_savings: Savings from switching lenders with refinance breakeven.
- get_recommendation: AI-ranked top picks based on borrower profile with explanations.

## Authentication

API key required. Prefix: mort_*
Free tier: 20 requests/day.
Get key: POST /api/v1/register with email + password.

## Data Freshness

Rates scraped at 7:00 AM and 7:00 PM EST daily.
4 lenders via direct API (instant, most reliable).
15 lenders via stealth browser scraping.
90-day rolling history with AM/PM granularity.

## Lenders (19)

Bank of America, Wells Fargo, Chase, Citi, Navy Federal CU, SoFi, US Bank, Guaranteed Rate, Truist, Mr. Cooper, Rocket Mortgage, PNC, PennyMac, Citizens Bank, USAA, Flagstar, LoanDepot

## Benchmarks (2)

Freddie Mac PMMS (national average), Mortgage News Daily Index

## Disclaimer

Rates shown are publicly advertised rates scraped from lender websites and are not personalized quotes. Not financial advice. Contact lenders directly for official quotes.

## Links

- PyPI: pip install mortgage-rates-mcp
- GitHub: https://github.com/seang1121/mortgage-rates-mcp
```

- [ ] **Step 2: Add dotenv loading to app.py**

Add to the top of `backend/app.py`:

```python
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
```

- [ ] **Step 3: Add llms.txt route to app.py**

```python
@app.route('/llms.txt')
def llms_txt():
    """Serve llms.txt for AI agent discovery."""
    llms_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'llms.txt')
    with open(llms_path) as f:
        return f.read(), 200, {'Content-Type': 'text/plain'}
```

- [ ] **Step 4: Add startup block to app.py**

```python
if __name__ == '__main__':
    from backend.scheduler import start_scheduler
    start_scheduler()
    app.run(host='0.0.0.0', port=int(os.getenv('FLASK_PORT', 5001)), debug=False)
```

- [ ] **Step 5: Commit**

```bash
git add README.md backend/app.py
git commit -m "feat: README, dotenv loading, startup wiring"
```

---

## Task 15: End-to-End Test + GitHub Push

- [ ] **Step 1: Create .env from .env.example**

Copy `.env.example` to `.env` and fill in `FLASK_SECRET_KEY`.

- [ ] **Step 2: Initialize database**

```bash
python scripts/create_database.py
```

- [ ] **Step 3: Create admin user**

```bash
python scripts/create_admin.py
```

Save the `mort_*` key it prints.

- [ ] **Step 4: Start the server**

```bash
python backend/app.py
```

Verify it starts on port 5001 and prints scheduler startup message.

- [ ] **Step 5: Test health endpoint**

```bash
curl http://localhost:5001/api/v1/health
```

Expected: JSON with status, last scrape time, lender count.

- [ ] **Step 6: Test registration endpoint**

```bash
curl -X POST http://localhost:5001/api/v1/register -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"testpass123"}'
```

Expected: JSON with user info and `mort_*` API key.

- [ ] **Step 7: Test rate endpoint (will be empty until first scrape)**

```bash
curl http://localhost:5001/api/v1/rates -H "X-API-Key: mort_YOUR_KEY"
```

Expected: empty rates array with disclaimer.

- [ ] **Step 8: Trigger manual scrape (admin only)**

```bash
curl -X POST http://localhost:5001/api/v1/admin/scrape -H "X-API-Key: mort_YOUR_ADMIN_KEY"
```

Expected: scrape runs, returns summary with rates found.

- [ ] **Step 9: Test rates again after scrape**

```bash
curl http://localhost:5001/api/v1/rates -H "X-API-Key: mort_YOUR_KEY"
```

Expected: populated rates from all successful lenders.

- [ ] **Step 10: Create GitHub repo and push**

```bash
cd C:\Users\seang1121\mortgage-rates-mcp
gh repo create seang1121/mortgage-rates-mcp --public --source=. --push
```

- [ ] **Step 11: Final commit**

```bash
git add -A
git commit -m "ready for launch — all 11 tools, 12 extractors, Flask API, scheduler"
git push origin master
```
