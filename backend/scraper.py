"""Scrape orchestrator — runs all extractors, validates, stores results.

Execution flow:
  1. Tier 1: Direct API calls (instant, parallel-safe)
  2. Tier 2: Stealth browser in batches of 4 (low protection lenders)
  3. Tier 3: Stealth browser in batches of 2 (heavy anti-bot, more careful)
  4. Validate all rates against sanity bounds + benchmark cross-reference
  5. Store in database (rates + rate_history)
  6. Apply last-known-good fallbacks for failed lenders
  7. Log everything to scrape_logs
"""
import asyncio
import os
import secrets
from datetime import datetime

from backend.database import db
from backend.extractors import (
    TIER1_EXTRACTORS, TIER2_EXTRACTORS, TIER3_EXTRACTORS,
    ALL_EXTRACTORS, TOTAL_LENDER_COUNT,
)
from backend.extractors.base import RateResult
from backend.validators import validate_rate, cross_reference_benchmarks, check_staleness

BATCH_SIZE_T2 = 4   # Tier 2: 4 parallel (low risk)
BATCH_SIZE_T3 = 2   # Tier 3: 2 parallel (heavy sites, be careful)
MAX_RETRIES = 3
WAIT_SCHEDULE = [8000, 12000, 15000]  # increasing wait per retry attempt
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")


def run_scrape(zip_code: str = None) -> dict:
    """Run a full scrape cycle. Returns summary dict.

    This is the main entry point — called by the scheduler and the admin API.
    """
    zip_code = zip_code or os.getenv("DEFAULT_ZIP_CODE", "32224")
    return asyncio.run(_async_scrape(zip_code))


async def _async_scrape(zip_code: str) -> dict:
    """Async scrape orchestrator."""
    session_id = secrets.token_hex(8)
    now = datetime.now()
    time_of_day = "AM" if now.hour < 12 else "PM"
    scraped_at = now.isoformat()

    all_rates: list[RateResult] = []
    successes = []
    failures = []

    print(f"[SCRAPER] Session {session_id} starting — {len(ALL_EXTRACTORS)} extractors, ZIP {zip_code}")

    # ── Tier 1: Direct APIs (no browser) ────────────────────────────
    print(f"[SCRAPER] Tier 1: {len(TIER1_EXTRACTORS)} direct API sources")
    for extractor in TIER1_EXTRACTORS:
        start = datetime.now()
        try:
            rates = await extractor.scrape(None, zip_code)
            duration = int((datetime.now() - start).total_seconds() * 1000)
            if rates:
                all_rates.extend(rates)
                successes.append(extractor.name)
                _log_scrape(session_id, extractor.name, "success", len(rates), duration)
                print(f"  [{extractor.name}] OK — {len(rates)} rates ({duration}ms)")
            else:
                failures.append(extractor.name)
                _log_scrape(session_id, extractor.name, "failed", 0, duration, "No rates returned")
                print(f"  [{extractor.name}] FAIL — no rates ({duration}ms)")
        except Exception as e:
            duration = int((datetime.now() - start).total_seconds() * 1000)
            failures.append(extractor.name)
            _log_scrape(session_id, extractor.name, "failed", 0, duration, str(e))
            print(f"  [{extractor.name}] ERROR — {e} ({duration}ms)")

    # ── Tier 2 + 3: Browser scraping ────────────────────────────────
    from patchright.async_api import async_playwright

    async with async_playwright() as pw:
        # Try system Chrome first (better TLS fingerprint for anti-bot sites),
        # fall back to bundled Chromium if Chrome isn't installed
        try:
            browser = await pw.chromium.launch(headless=True, channel="chrome")
            print("[SCRAPER] Using system Chrome (better TLS fingerprint)")
        except Exception:
            browser = await pw.chromium.launch(headless=True)
            print("[SCRAPER] Using bundled Chromium")

        # Tier 2: Batches of 4
        print(f"[SCRAPER] Tier 2: {len(TIER2_EXTRACTORS)} easy browser lenders")
        t2_failed = await _scrape_tier(browser, TIER2_EXTRACTORS, BATCH_SIZE_T2,
                                        zip_code, session_id, all_rates, successes, failures)

        # Tier 3: Batches of 2 (more careful with anti-bot sites)
        print(f"[SCRAPER] Tier 3: {len(TIER3_EXTRACTORS)} anti-bot lenders")
        t3_failed = await _scrape_tier(browser, TIER3_EXTRACTORS, BATCH_SIZE_T3,
                                        zip_code, session_id, all_rates, successes, failures)

        # ── Retry all failures ──────────────────────────────────────
        all_failed = t2_failed + t3_failed
        if all_failed:
            print(f"[SCRAPER] Retrying {len(all_failed)} failed: {', '.join(e.name for e in all_failed)}")
            for extractor in all_failed:
                retried = False
                for attempt in range(MAX_RETRIES):
                    wait = WAIT_SCHEDULE[min(attempt, len(WAIT_SCHEDULE) - 1)]
                    extractor.wait_ms = wait
                    start = datetime.now()
                    try:
                        rates = await extractor.scrape(browser, zip_code)
                        duration = int((datetime.now() - start).total_seconds() * 1000)
                        if rates:
                            all_rates.extend(rates)
                            successes.append(extractor.name)
                            _log_scrape(session_id, extractor.name, "success", len(rates), duration,
                                        f"Retry {attempt + 1}")
                            print(f"  [{extractor.name}] OK on retry {attempt + 1} ({duration}ms)")
                            retried = True
                            break
                    except Exception as e:
                        last_error = str(e)
                        print(f"  [{extractor.name}] Retry {attempt + 1} error: {last_error[:100]}")

                if not retried:
                    # Final failure — take screenshot for debugging
                    screenshot_path = await _take_screenshot(browser, extractor, zip_code)
                    _log_scrape(session_id, extractor.name, "failed", 0, 0,
                                f"All retries exhausted. Last error: {last_error[:200] if 'last_error' in dir() else 'unknown'}",
                                screenshot_path)
                    print(f"  [{extractor.name}] FAILED after {MAX_RETRIES} retries")

        await browser.close()

    # ── Validate ────────────────────────────────────────────────────
    validated = []
    rejected = 0
    for rate in all_rates:
        is_valid, reason = validate_rate(rate)
        if is_valid:
            validated.append(rate)
        else:
            rejected += 1
            print(f"  [VALIDATE] Rejected {rate.lender} {rate.product}: {reason}")

    # Cross-reference against benchmarks
    before_xref = len(validated)
    validated = cross_reference_benchmarks(validated)
    xref_removed = before_xref - len(validated)
    if xref_removed:
        print(f"  [VALIDATE] Benchmark cross-ref removed {xref_removed} outliers")

    # Deduplicate (keep first per lender+product — lowest rate wins since sorted)
    seen = set()
    unique = []
    for r in sorted(validated, key=lambda x: x.rate):
        key = (r.lender, r.product)
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # ── Store ───────────────────────────────────────────────────────
    _store_rates(unique, zip_code, scraped_at, session_id, time_of_day)

    # Apply last-known-good fallbacks for failed lenders
    _apply_fallbacks(failures, zip_code, scraped_at, session_id)

    # Remove failures that are also in successes (from retry)
    final_failures = [f for f in failures if f not in successes]

    summary = {
        "session_id": session_id,
        "total_rates": len(unique),
        "successes": list(set(successes)),
        "failures": final_failures,
        "rejected": rejected,
        "scraped_at": scraped_at,
        "time_of_day": time_of_day,
        "zip_code": zip_code,
    }

    print(f"[SCRAPER] Complete: {len(unique)} rates stored, "
          f"{len(set(successes))} succeeded, {len(final_failures)} failed, "
          f"{rejected} rejected by validation")

    return summary


async def _scrape_tier(browser, extractors, batch_size, zip_code, session_id,
                        all_rates, successes, failures) -> list:
    """Scrape a tier of extractors in batches. Returns list of failed extractors."""
    failed_extractors = []

    for batch_start in range(0, len(extractors), batch_size):
        batch = extractors[batch_start:batch_start + batch_size]
        batch_num = (batch_start // batch_size) + 1
        print(f"  Batch {batch_num}: {', '.join(e.name for e in batch)}")

        tasks = [_scrape_one(extractor, browser, zip_code, session_id) for extractor in batch]
        results = await asyncio.gather(*tasks)

        for extractor, (rates, duration) in zip(batch, results):
            if rates:
                all_rates.extend(rates)
                successes.append(extractor.name)
                print(f"    [{extractor.name}] OK — {len(rates)} rates ({duration}ms)")
            else:
                failed_extractors.append(extractor)
                failures.append(extractor.name)
                print(f"    [{extractor.name}] FAIL ({duration}ms)")

    return failed_extractors


async def _scrape_one(extractor, browser, zip_code, session_id) -> tuple[list[RateResult], int]:
    """Scrape a single extractor with timing and logging."""
    start = datetime.now()
    try:
        rates = await extractor.scrape(browser, zip_code)
        duration = int((datetime.now() - start).total_seconds() * 1000)
        status = "success" if rates else "failed"
        _log_scrape(session_id, extractor.name, status, len(rates), duration)
        return rates, duration
    except Exception as e:
        duration = int((datetime.now() - start).total_seconds() * 1000)
        _log_scrape(session_id, extractor.name, "failed", 0, duration, str(e))
        return [], duration


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
    try:
        db.execute(
            """INSERT INTO scrape_logs (scrape_session, lender, status, rates_found,
               error_message, screenshot_path, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, lender, status, rates_found, error, screenshot, duration_ms)
        )
    except Exception:
        pass  # don't let logging failures break the scrape


def _store_rates(rates, zip_code, scraped_at, session_id, time_of_day):
    """Store validated rates in both `rates` (current) and `rate_history` (rolling 90-day).

    Uses atomic swap: insert new rates first, then delete old ones in same transaction.
    This prevents a zero-rate window where the API serves empty results mid-scrape.
    """
    today = datetime.now().strftime('%Y-%m-%d')

    with db.get_connection() as conn:
        # Insert new rates first (alongside old ones temporarily)
        for r in rates:
            stale = 1 if check_staleness(r.lender, r.product, r.rate) else 0
            conn.execute(
                """INSERT INTO rates (lender, product, rate, apr, zip_code,
                   is_benchmark, stale, scraped_at, scrape_session)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (r.lender, r.product, r.rate, r.apr, zip_code,
                 int(r.is_benchmark), stale, scraped_at, session_id)
            )
            conn.execute(
                """INSERT INTO rate_history (date, time_of_day, lender, product,
                   rate, apr, zip_code)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (today, time_of_day, r.lender, r.product, r.rate, r.apr, zip_code)
            )

        # Now delete old rates (from previous scrape sessions) — atomic with inserts above
        conn.execute("DELETE FROM rates WHERE scrape_session != ?", (session_id,))
        conn.commit()

    # Prune history older than 90 days
    db.execute("DELETE FROM rate_history WHERE date < date('now', '-90 days')")


def _apply_fallbacks(failures, zip_code, scraped_at, session_id):
    """For failed lenders, serve their last known good rates with stale=1."""
    for lender in failures:
        last_good = db.query(
            """SELECT lender, product, rate, apr
               FROM rate_history
               WHERE lender = ?
               ORDER BY date DESC, time_of_day DESC
               LIMIT 10""",
            (lender,)
        )

        seen = set()
        for r in last_good:
            key = (r['lender'], r['product'])
            if key in seen:
                continue
            seen.add(key)
            try:
                db.execute(
                    """INSERT INTO rates (lender, product, rate, apr, zip_code,
                       is_benchmark, stale, scraped_at, scrape_session)
                       VALUES (?, ?, ?, ?, ?, 0, 1, ?, ?)""",
                    (r['lender'], r['product'], r['rate'], r['apr'],
                     zip_code, scraped_at, session_id)
                )
            except Exception:
                pass
