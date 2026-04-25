"""Rate validation pipeline — sanity bounds, benchmark cross-reference, staleness detection.

Every rate passes through this pipeline before being stored in the database.
Consumers trust our data for financial decisions — accuracy is non-negotiable.
"""
from backend.extractors.base import RateResult
from backend.database import db

# ── Constants ───────────────────────────────────────────────────────────────

RATE_FLOOR = 2.5
RATE_CEILING = 14.0
APR_CEILING = 16.0  # APR can be higher than rate due to fees
BENCHMARK_DEVIATION_MAX = 1.5  # flag if >1.5% from national average

DISCLAIMER = (
    "Rates shown are publicly advertised rates scraped from lender websites "
    "and are not personalized quotes. Actual rates depend on credit score, "
    "loan amount, property type, down payment, and other factors. This is not "
    "financial advice. Contact lenders directly for official quotes."
)

DISCLAIMER_SHORT = (
    "Publicly advertised rates, not personalized quotes. "
    "Contact lenders for official rates."
)


# ── Validation functions ───────────────────────────────────────────────────

def validate_rate(rate: RateResult) -> tuple[bool, str]:
    """Validate a single rate against sanity bounds.

    Returns (is_valid, reason). Invalid rates are rejected before DB storage.
    """
    # Rate must be in realistic range
    if not (RATE_FLOOR <= rate.rate <= RATE_CEILING):
        return False, f"Rate {rate.rate}% outside bounds [{RATE_FLOOR}-{RATE_CEILING}]"

    # APR must be in realistic range (can be higher than rate due to fees)
    if rate.apr is not None:
        if not (RATE_FLOOR <= rate.apr <= APR_CEILING):
            return False, f"APR {rate.apr}% outside bounds [{RATE_FLOOR}-{APR_CEILING}]"
        # APR should never be lower than base rate
        if rate.apr < rate.rate - 0.01:  # tiny tolerance for rounding
            return False, f"APR {rate.apr}% lower than rate {rate.rate}% (impossible)"

    return True, "OK"


def validate_product_consistency(rates: list[RateResult]) -> list[str]:
    """Check that 30yr rate > 15yr rate for same lender (basic sanity).

    Returns list of flagged lender names. Does not reject — just warns.
    """
    by_lender = {}
    for r in rates:
        by_lender.setdefault(r.lender, {})[r.product] = r

    flagged = []
    for lender, products in by_lender.items():
        r30 = products.get('30yr')
        r15 = products.get('15yr')
        if r30 and r15 and r15.rate >= r30.rate:
            flagged.append(lender)
    return flagged


def cross_reference_benchmarks(rates: list[RateResult]) -> list[RateResult]:
    """Remove lender rates that deviate too far from benchmark averages.

    Keeps benchmark rates and lender rates within BENCHMARK_DEVIATION_MAX
    of the benchmark average for the same product.
    """
    benchmarks = [r for r in rates if r.is_benchmark]
    lender_rates = [r for r in rates if not r.is_benchmark]

    if not benchmarks:
        # No benchmarks available — can't cross-reference, keep all
        return rates

    # Calculate benchmark average per product
    bench_avg = {}
    for b in benchmarks:
        bench_avg.setdefault(b.product, []).append(b.rate)
    bench_avg = {p: sum(rs) / len(rs) for p, rs in bench_avg.items()}

    valid = []
    for r in lender_rates:
        avg = bench_avg.get(r.product)
        if avg is not None and abs(r.rate - avg) > BENCHMARK_DEVIATION_MAX:
            # Too far from benchmark — likely a scrape error
            continue
        valid.append(r)

    return valid + benchmarks


def check_staleness(lender: str, product: str, rate: float) -> bool:
    """Stale = lender's rate hasn't moved in 14+ scrapes (~7 days at 2x/day)
    AND the Freddie Mac 30yr benchmark moved meaningfully in that window.

    Markets routinely sit flat for many consecutive scrapes, so flatness alone
    is not a stale signal — only flatness *while the market moved* is.
    """
    HISTORY = 14
    BENCHMARK_MOVE_THRESHOLD = 0.05  # percentage points

    rows = db.query(
        """SELECT rate FROM rate_history
           WHERE lender = ? AND product = ?
           ORDER BY created_at DESC LIMIT ?""",
        (lender, product, HISTORY)
    )
    if len(rows) < HISTORY:
        return False
    if not all(abs(r['rate'] - rate) < 0.001 for r in rows):
        return False

    bench = db.query(
        """SELECT rate FROM rate_history
           WHERE lender = 'Freddie Mac (natl avg)' AND product = '30yr'
           ORDER BY created_at DESC LIMIT ?""",
        (HISTORY,)
    )
    if len(bench) < 2:
        return False
    bench_range = max(b['rate'] for b in bench) - min(b['rate'] for b in bench)
    return bench_range >= BENCHMARK_MOVE_THRESHOLD
