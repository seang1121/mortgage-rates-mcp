"""Recommendation engine — ranked picks with human-readable explanations.

Think like a broker giving advice:
  "Based on today's rates, here are your top 3 options for a $400K home
   with 20% down. Navy Federal is your best bet — 0.2% below the national
   average, saving you $141/month compared to the average lender."

The output is designed to be useful to both:
  - An AI agent formatting a response to a user
  - A human reading the JSON directly
"""
from backend.database import db
from backend.calculator import full_calculation
from backend.extractors.base import PRODUCT_DISPLAY_NAMES


def get_recommendation(loan_amount: float, credit_score: int = 740,
                       down_payment_pct: float = 20, product: str = None,
                       property_type: str = "single_family",
                       loan_purpose: str = "purchase") -> dict:
    """Generate ranked lender recommendations based on borrower profile.

    Returns top 5 picks sorted by rate (lowest first), each with:
    - Full payment breakdown
    - Comparison to national average
    - Human-readable explanation of why this lender is recommended
    """
    # Fetch current non-stale, non-benchmark rates
    query = """SELECT lender, product, rate, apr, scraped_at, stale
               FROM rates WHERE is_benchmark = 0"""
    params = []

    if product:
        query += " AND product = ?"
        params.append(product)

    # Exclude stale data from recommendations (fallbacks are for display, not advice)
    query += " AND stale = 0 ORDER BY rate ASC"
    rates = db.query(query, tuple(params))

    if not rates:
        return {
            "recommendations": [],
            "message": "No current rates available. Rates are refreshed at 7:00 AM and 7:00 PM EST.",
            "borrower_profile": _build_profile(loan_amount, credit_score, down_payment_pct,
                                                property_type, loan_purpose, product),
        }

    # Get benchmark averages for context
    benchmarks = db.query(
        "SELECT product, AVG(rate) as avg_rate FROM rates WHERE is_benchmark = 1 GROUP BY product"
    )
    bench_avg = {b['product']: b['avg_rate'] for b in benchmarks}

    # Build recommendations — one per lender (best rate for each)
    recommendations = []
    seen_lenders = set()

    for r in rates:
        if r['lender'] in seen_lenders:
            continue
        seen_lenders.add(r['lender'])

        # Determine loan term from product
        PRODUCT_TERMS = {'15yr': 15}
        term = PRODUCT_TERMS.get(r['product'], 30)

        calc = full_calculation(loan_amount, r['rate'], term, down_payment_pct)

        # Compare to benchmark
        benchmark = bench_avg.get(r['product'])
        vs_market = round(r['rate'] - benchmark, 3) if benchmark else None

        # Generate human-readable explanation
        why = _explain(r, calc, vs_market, loan_purpose, benchmark)

        recommendations.append({
            "rank": len(recommendations) + 1,
            "lender": r['lender'],
            "product": r['product'],
            "product_name": PRODUCT_DISPLAY_NAMES.get(r['product'], r['product']),
            "rate": r['rate'],
            "apr": r['apr'],
            "monthly_payment": calc['monthly_payment'],
            "total_interest": calc['total_interest'],
            "total_cost": calc['total_cost'],
            "loan_amount": calc['loan_amount'],
            "vs_market_avg": f"{vs_market:+.3f}%" if vs_market is not None else None,
            "why": why,
            "scraped_at": r['scraped_at'],
        })

        if len(recommendations) >= 5:
            break

    # Calculate savings vs worst option for context
    if len(recommendations) >= 2:
        best = recommendations[0]
        for rec in recommendations[1:]:
            savings = round(rec['monthly_payment'] - best['monthly_payment'], 2)
            rec['vs_best_monthly'] = f"+${savings:.2f}/mo" if savings > 0 else "$0"

        recommendations[0]['vs_best_monthly'] = "Best rate"

    return {
        "recommendations": recommendations,
        "borrower_profile": _build_profile(loan_amount, credit_score, down_payment_pct,
                                            property_type, loan_purpose, product),
        "rates_as_of": recommendations[0]['scraped_at'] if recommendations else None,
        "total_lenders_compared": len(seen_lenders),
    }


def _build_profile(loan_amount, credit_score, down_payment_pct,
                    property_type, loan_purpose, product):
    """Build borrower profile dict for the response."""
    return {
        "loan_amount": loan_amount,
        "credit_score": credit_score,
        "down_payment_pct": down_payment_pct,
        "property_type": property_type,
        "loan_purpose": loan_purpose,
        "product_filter": product,
    }


def _explain(rate, calc, vs_market, loan_purpose, benchmark) -> str:
    """Generate a human-readable explanation for why this lender is recommended.

    Written the way a broker would explain it to a buyer.
    """
    parts = []

    # Rate vs market
    if vs_market is not None:
        if vs_market < -0.15:
            parts.append(f"{abs(vs_market):.3f}% below the national average — significantly cheaper than most lenders")
        elif vs_market < -0.05:
            parts.append(f"{abs(vs_market):.3f}% below the national average")
        elif vs_market < 0.05:
            parts.append("Right at the national average")
        else:
            parts.append(f"{vs_market:.3f}% above the national average")

    # APR spread (indicates fees)
    if rate.get('apr') and rate['rate']:
        spread = rate['apr'] - rate['rate']
        if spread < 0.2:
            parts.append("very low fees (tight rate-to-APR spread)")
        elif spread > 0.5:
            parts.append("note: higher fees reflected in APR spread")

    # Monthly payment context
    parts.append(f"${calc['monthly_payment']:,.2f}/month on a ${calc['loan_amount']:,.0f} loan")

    return ". ".join(parts) + "."
