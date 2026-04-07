"""Mortgage payment calculations — the math a consumer actually needs.

Every number here is something a realtor could text to a buyer:
  "On a $400K loan at 6.5%, your monthly payment is $2,528"
  "Switching from Chase to Navy Federal saves you $141/month"
  "15-year costs $180K less in interest but $847/month more"
"""


def monthly_payment(principal: float, annual_rate_pct: float, term_years: int = 30) -> float:
    """Calculate monthly principal & interest payment.

    This is the standard amortization formula. Does not include
    taxes, insurance, or PMI — those vary by location and borrower.
    """
    if annual_rate_pct <= 0 or principal <= 0:
        return principal / max(term_years * 12, 1)

    r = annual_rate_pct / 100 / 12  # monthly rate
    n = term_years * 12              # total payments
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def total_interest(principal: float, annual_rate_pct: float, term_years: int = 30) -> float:
    """Total interest paid over the life of the loan."""
    mp = monthly_payment(principal, annual_rate_pct, term_years)
    return (mp * term_years * 12) - principal


def full_calculation(loan_amount: float, annual_rate_pct: float,
                     term_years: int = 30, down_payment_pct: float = 0) -> dict:
    """Full payment breakdown — everything a buyer needs to see.

    Returns human-readable numbers: monthly payment, total interest,
    total cost, down payment amount.
    """
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
    """Compare loan scenarios side by side.

    A buyer asks: "What's better — 30-year or 15-year?"
    This answers that with real numbers + breakeven analysis.

    Args:
        loan_amount: Total home price (before down payment)
        rates: {"30yr": 6.5, "15yr": 5.8, "ARM": 6.0}
        down_payment_pct: Down payment as percentage of loan amount
    """
    from backend.extractors.base import PRODUCT_DISPLAY_NAMES

    terms = {"30yr": 30, "15yr": 15, "ARM": 30, "FHA_30yr": 30, "VA_30yr": 30}
    results = []

    for product, rate in rates.items():
        term = terms.get(product, 30)
        calc = full_calculation(loan_amount, rate, term, down_payment_pct)
        calc["product"] = product
        calc["product_name"] = PRODUCT_DISPLAY_NAMES.get(product, product)
        results.append(calc)

    # Sort by monthly payment (lowest first — what buyers care about most)
    results.sort(key=lambda r: r["monthly_payment"])

    # Add breakeven analysis: "If you pay more monthly on 15yr, when do you
    # break even on interest savings?"
    if len(results) > 1:
        cheapest_monthly = results[0]["monthly_payment"]
        for r in results:
            if r["monthly_payment"] > cheapest_monthly:
                monthly_extra = r["monthly_payment"] - cheapest_monthly
                # Interest savings compared to the option with the most total interest
                max_interest = max(x["total_interest"] for x in results)
                interest_saved = max_interest - r["total_interest"]
                if monthly_extra > 0 and interest_saved > 0:
                    r["breakeven_months"] = round(interest_saved / monthly_extra)
                else:
                    r["breakeven_months"] = None
            else:
                r["breakeven_months"] = 0  # cheapest monthly — no breakeven needed

    return results


def estimate_savings(loan_amount: float, from_rate: float, to_rate: float,
                     term_years: int = 30, remaining_years: int = None) -> dict:
    """Calculate savings from switching lenders or refinancing.

    A broker tells their client: "I can save you $141/month by moving
    from Chase at 6.5% to Navy Federal at 5.875%. That's $50,760 over
    the life of your loan."

    Args:
        loan_amount: Current loan principal
        from_rate: Current rate (%)
        to_rate: New rate (%)
        term_years: Original loan term
        remaining_years: Years left on current loan (defaults to full term)
    """
    remaining = remaining_years or term_years
    from_mp = monthly_payment(loan_amount, from_rate, remaining)
    to_mp = monthly_payment(loan_amount, to_rate, remaining)

    monthly_diff = from_mp - to_mp
    annual_diff = monthly_diff * 12
    total_diff = monthly_diff * remaining * 12

    return {
        "from_rate": from_rate,
        "to_rate": to_rate,
        "from_monthly": round(from_mp, 2),
        "to_monthly": round(to_mp, 2),
        "monthly_savings": round(monthly_diff, 2),
        "annual_savings": round(annual_diff, 2),
        "total_savings": round(total_diff, 2),
        "term_years": remaining,
    }
