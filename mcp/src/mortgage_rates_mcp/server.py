"""mortgage-rates-mcp — MCP server for real-time mortgage rate intelligence.

19 lenders + 2 benchmarks. 12 tools for rates, comparison, calculation,
recommendations, and alerts. Works with Claude, ChatGPT, Cursor, Windsurf,
VS Code, and any MCP-compatible client.
"""
import json
import os
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional

from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("MORTGAGE_API_URL", "http://localhost:5001")
API_KEY = os.environ.get("MORTGAGE_API_KEY", "")

DISCLAIMER_NOTE = "Returns publicly advertised rates, not personalized quotes."

mcp = FastMCP(
    "mortgage-rates-mcp",
    instructions=(
        "Real-time mortgage rate comparison across 19 major US lenders + 2 national benchmarks. "
        "12 tools: current rates, best rate finder, lender comparison, 90-day history with trends, "
        "payment calculator, loan scenario comparison, refinance savings, AI-ranked recommendations, "
        "client-ready rate sheet images, and rate threshold alerts. "
        "Rates scraped at 7am and 7pm EST daily. All rates are publicly advertised, not personalized quotes."
    ),
)


# ── API Helpers ─────────────────────────────────────────────────────────────

def _api_get(path: str, params: Optional[dict] = None) -> dict:
    """Authenticated GET request to the backend API."""
    if not API_KEY:
        raise RuntimeError(
            "Set MORTGAGE_API_KEY environment variable. "
            "Register at the API to get your free key."
        )
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={"X-API-Key": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"API error {e.code}: {body[:200]}") from e


def _api_post(path: str, body: dict) -> dict:
    """Authenticated POST request to the backend API."""
    if not API_KEY:
        raise RuntimeError("Set MORTGAGE_API_KEY environment variable.")
    url = f"{BASE_URL}{path}"
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        raise RuntimeError(f"API error {e.code}: {body_text[:200]}") from e


# ── MCP Tools ───────────────────────────────────────────────────────────────

@mcp.tool()
def get_rates(product: str = "", lender: str = "") -> str:
    """Get current mortgage rates across all 19 lenders, grouped by product type.

    Returns publicly advertised rates, not personalized quotes.
    Rates are refreshed at 7am and 7pm EST daily.

    Args:
        product: Filter by product type (optional: "30yr", "15yr", "ARM", "FHA_30yr", "VA_30yr")
        lender: Filter by lender name (optional, partial match)
    """
    params = {}
    if product:
        params["product"] = product
    if lender:
        params["lender"] = lender

    data = _api_get("/api/v1/rates", params)
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    lines = ["CURRENT MORTGAGE RATES\n"]
    for product_group in data.get("products", []):
        lines.append(f"--- {product_group['product_name']} ---")
        for r in product_group["rates"]:
            apr_str = f"  ({r['apr']:.3f}% APR)" if r.get("apr") else ""
            stale_str = "  [stale]" if r.get("stale") else ""
            bench_str = "  (benchmark)" if r.get("is_benchmark") else ""
            lines.append(f"  {r['lender']:28s}  {r['rate']:.3f}%{apr_str}{stale_str}{bench_str}")
        lines.append("")

    lines.append(f"Total: {data.get('total_rates', 0)} rates")
    lines.append(f"\n{DISCLAIMER_NOTE}")
    return "\n".join(lines)


@mcp.tool()
def get_best_rate(product: str = "30yr") -> str:
    """Get the single best (lowest) rate for a given loan type across all lenders.

    Returns publicly advertised rates, not personalized quotes.

    Args:
        product: Loan type ("30yr", "15yr", "ARM", "FHA_30yr", "VA_30yr"). Defaults to 30yr.
    """
    data = _api_get("/api/v1/rates/best", {"product": product} if product else {})
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    lines = ["BEST RATES\n"]
    for r in data.get("best_rates", []):
        apr_str = f" ({r['apr']:.3f}% APR)" if r.get("apr") else ""
        lines.append(f"  {r['product_name']}: {r['lender']} at {r['rate']:.3f}%{apr_str}")

    lines.append(f"\n{DISCLAIMER_NOTE}")
    return "\n".join(lines)


@mcp.tool()
def compare_lenders(lenders: str, product: str = "") -> str:
    """Compare rates side-by-side for specific lenders.

    Returns publicly advertised rates, not personalized quotes.

    Args:
        lenders: Comma-separated lender names (e.g., "Chase, Wells Fargo, Navy Federal")
        product: Optional product filter ("30yr", "15yr", etc.)
    """
    params = {"lenders": lenders}
    if product:
        params["product"] = product

    data = _api_get("/api/v1/rates/compare", params)
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    lines = ["LENDER COMPARISON\n"]
    for lender_name, rates in data.get("comparison", {}).items():
        lines.append(f"  {lender_name}:")
        for r in rates:
            apr_str = f" ({r['apr']:.3f}% APR)" if r.get("apr") else ""
            lines.append(f"    {r['product_name']}: {r['rate']:.3f}%{apr_str}")
        lines.append("")

    lines.append(DISCLAIMER_NOTE)
    return "\n".join(lines)


@mcp.tool()
def get_rate_history(product: str = "30yr", lender: str = "", days: int = 30) -> str:
    """Get historical rate trends — up to 90 days with AM/PM tracking.

    Returns publicly advertised rates, not personalized quotes.

    Args:
        product: Product type (default "30yr")
        lender: Optional lender filter
        days: Number of days of history (default 30, max 90)
    """
    params = {"product": product, "days": min(days, 90)}
    if lender:
        params["lender"] = lender

    data = _api_get("/api/v1/rates/history", params)
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    lines = [f"RATE HISTORY — {data.get('product_name', product)}\n"]
    lines.append(f"Direction: {data.get('direction', 'unknown')}")
    lines.append(f"Period: {data.get('days', 0)} days\n")

    for day in data.get("daily_summary", []):
        lines.append(
            f"  {day['date']} {day['time_of_day']}: "
            f"avg {day['avg_rate']:.3f}% | "
            f"low {day['min_rate']:.3f}% | "
            f"high {day['max_rate']:.3f}% | "
            f"{day['lender_count']} lenders"
        )

    lines.append(f"\n{DISCLAIMER_NOTE}")
    return "\n".join(lines)


@mcp.tool()
def get_lender_details(lender: str) -> str:
    """Get all available products and rates from a specific lender.

    Returns publicly advertised rates, not personalized quotes.

    Args:
        lender: Lender name (e.g., "Chase", "Navy Federal", "Rocket Mortgage")
    """
    data = _api_get(f"/api/v1/rates/lender/{urllib.parse.quote(lender)}")
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    lines = [f"LENDER DETAILS — {data.get('lender', lender)}\n"]
    for r in data.get("products", []):
        apr_str = f" ({r['apr']:.3f}% APR)" if r.get("apr") else ""
        stale_str = " [stale]" if r.get("stale") else ""
        lines.append(f"  {r['product_name']}: {r['rate']:.3f}%{apr_str}{stale_str}")

    lines.append(f"\n{DISCLAIMER_NOTE}")
    return "\n".join(lines)


@mcp.tool()
def get_system_status() -> str:
    """Health check — uptime, last scrape time, lender count, schedule.

    No authentication required for this endpoint.
    """
    try:
        url = f"{BASE_URL}/api/v1/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return f"Error checking system status: {e}"

    lines = ["SYSTEM STATUS\n"]
    lines.append(f"  Status:    healthy")
    lines.append(f"  Uptime:    {data.get('uptime', 'N/A')}")
    lines.append(f"  Last scrape: {data.get('last_scrape', 'Never')}")
    lines.append(f"  Lenders reporting: {data.get('lenders_reporting', 0)} / {data.get('total_lenders_tracked', 0)}")
    lines.append(f"  Benchmarks: {data.get('total_benchmarks', 0)}")
    lines.append(f"  Schedule:  {data.get('schedule', 'N/A')}")

    stats = data.get("scrape_stats_24h", {})
    if stats:
        lines.append(f"\n  Last 24h: {stats.get('success', 0)} successful, {stats.get('failed', 0)} failed")

    return "\n".join(lines)


@mcp.tool()
def calculate_payment(loan_amount: float, rate: float = 0, term_years: int = 30,
                      down_payment_pct: float = 0) -> str:
    """Calculate monthly mortgage payment with full breakdown.

    Returns publicly advertised rates, not personalized quotes.

    Args:
        loan_amount: Total home price or loan principal
        rate: Interest rate (%). If 0, uses the best available 30yr rate.
        term_years: Loan term in years (default 30)
        down_payment_pct: Down payment as % of home price (default 0)
    """
    body = {
        "loan_amount": loan_amount,
        "term_years": term_years,
        "down_payment_pct": down_payment_pct,
    }
    if rate > 0:
        body["rate"] = rate

    data = _api_post("/api/v1/calculate", body)
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    c = data["calculation"]
    lines = ["PAYMENT CALCULATION\n"]
    lines.append(f"  Home price:      ${loan_amount:,.0f}")
    if c['down_payment'] > 0:
        lines.append(f"  Down payment:    ${c['down_payment']:,.0f} ({down_payment_pct}%)")
    lines.append(f"  Loan amount:     ${c['loan_amount']:,.0f}")
    lines.append(f"  Rate:            {c['rate']:.3f}%")
    lines.append(f"  Term:            {c['term_years']} years")
    lines.append(f"  Monthly P&I:     ${c['monthly_payment']:,.2f}")
    lines.append(f"  Total interest:  ${c['total_interest']:,.0f}")
    lines.append(f"  Total cost:      ${c['total_cost']:,.0f}")
    lines.append(f"\n{DISCLAIMER_NOTE}")
    return "\n".join(lines)


@mcp.tool()
def generate_rate_sheet(zip_code: str = "", products: str = "", branding_text: str = "") -> str:
    """Generate a client-ready rate card image (PNG) suitable for texting to buyers.

    Returns publicly advertised rates, not personalized quotes.

    Args:
        zip_code: Optional ZIP code to display on the card
        products: Comma-separated product types (default: "30yr,15yr,ARM")
        branding_text: Optional broker name/company to display on the card
    """
    body = {}
    if zip_code:
        body["zip_code"] = zip_code
    if products:
        body["products"] = [p.strip() for p in products.split(",")]
    if branding_text:
        body["branding_text"] = branding_text

    data = _api_post("/api/v1/rate-sheet", body)
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    return f"Rate sheet generated (PNG, base64-encoded).\n\nimage_base64: {data['image_base64'][:100]}...\n\n{DISCLAIMER_NOTE}"


@mcp.tool()
def set_rate_alert(product: str, threshold: float, lender: str = "") -> str:
    """Create a rate alert — get notified when a rate drops below your target.

    Args:
        product: Product type ("30yr", "15yr", "ARM", "FHA_30yr", "VA_30yr")
        threshold: Rate threshold (e.g., 6.0 = alert when rate drops below 6.0%)
        lender: Optional specific lender (empty = any lender)
    """
    body = {"product": product, "threshold": threshold}
    if lender:
        body["lender"] = lender

    data = _api_post("/api/v1/alerts", body)
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    return data.get("message", "Alert created successfully.")


@mcp.tool()
def compare_scenarios(loan_amount: float, down_payment_pct: float = 20) -> str:
    """Compare loan scenarios — 30yr vs 15yr vs ARM with payments and breakeven.

    Returns publicly advertised rates, not personalized quotes.

    Args:
        loan_amount: Total home price
        down_payment_pct: Down payment as % (default 20%)
    """
    data = _api_get("/api/v1/rates/scenarios", {
        "amount": loan_amount,
        "down_payment_pct": down_payment_pct,
    })
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    lines = [f"SCENARIO COMPARISON — ${loan_amount:,.0f} home, {down_payment_pct}% down\n"]
    for s in data.get("scenarios", []):
        be_str = f"  (breakeven: {s['breakeven_months']} months)" if s.get('breakeven_months') else ""
        lines.append(f"  {s['product_name']}:")
        lines.append(f"    Rate:          {s['rate']:.3f}%")
        lines.append(f"    Monthly P&I:   ${s['monthly_payment']:,.2f}")
        lines.append(f"    Total interest: ${s['total_interest']:,.0f}")
        lines.append(f"    Total cost:    ${s['total_cost']:,.0f}{be_str}")
        lines.append("")

    lines.append(DISCLAIMER_NOTE)
    return "\n".join(lines)


@mcp.tool()
def estimate_savings(loan_amount: float, from_lender: str, to_lender: str,
                     product: str = "30yr") -> str:
    """Calculate savings from switching lenders or refinancing.

    Returns publicly advertised rates, not personalized quotes.

    Args:
        loan_amount: Current loan amount
        from_lender: Current lender name
        to_lender: Target lender name
        product: Loan type (default "30yr")
    """
    data = _api_get("/api/v1/rates/savings", {
        "amount": loan_amount,
        "from": from_lender,
        "to": to_lender,
        "product": product,
    })
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    s = data["savings"]
    lines = ["SAVINGS ESTIMATE\n"]
    lines.append(f"  Switching from {s.get('from_lender', from_lender)} to {s.get('to_lender', to_lender)}")
    lines.append(f"  Product:        {product}")
    lines.append(f"  Current rate:   {s['from_rate']:.3f}% (${s['from_monthly']:,.2f}/mo)")
    lines.append(f"  New rate:       {s['to_rate']:.3f}% (${s['to_monthly']:,.2f}/mo)")
    lines.append(f"  Monthly savings: ${s['monthly_savings']:,.2f}")
    lines.append(f"  Annual savings:  ${s['annual_savings']:,.0f}")
    lines.append(f"  Total savings:   ${s['total_savings']:,.0f} over {s['term_years']} years")
    lines.append(f"\n{DISCLAIMER_NOTE}")
    return "\n".join(lines)


@mcp.tool()
def get_recommendation(loan_amount: float, credit_score: int = 740,
                       down_payment_pct: float = 20, product: str = "",
                       property_type: str = "single_family",
                       loan_purpose: str = "purchase") -> str:
    """AI-powered ranked recommendation — top lender picks based on your profile.

    Returns publicly advertised rates, not personalized quotes.

    Args:
        loan_amount: Total home price
        credit_score: Borrower credit score (default 740)
        down_payment_pct: Down payment % (default 20)
        product: Optional product filter ("30yr", "15yr", etc.)
        property_type: "single_family", "condo", "townhouse", "multi_family"
        loan_purpose: "purchase" or "refinance"
    """
    body = {
        "loan_amount": loan_amount,
        "credit_score": credit_score,
        "down_payment_pct": down_payment_pct,
        "property_type": property_type,
        "loan_purpose": loan_purpose,
    }
    if product:
        body["product"] = product

    data = _api_post("/api/v1/recommend", body)
    if not data.get("success"):
        return f"Error: {data.get('error', 'Unknown error')}"

    recs = data.get("recommendations", [])
    if not recs:
        return data.get("message", "No recommendations available.")

    profile = data.get("borrower_profile", {})
    lines = [
        f"TOP RECOMMENDATIONS — ${loan_amount:,.0f} home, {down_payment_pct}% down",
        f"Credit: {credit_score} | {loan_purpose.title()} | {property_type.replace('_', ' ').title()}\n",
    ]

    for rec in recs:
        apr_str = f" ({rec['apr']:.3f}% APR)" if rec.get('apr') else ""
        vs_str = f"  vs market: {rec['vs_market_avg']}" if rec.get('vs_market_avg') else ""
        vs_best = f"  [{rec['vs_best_monthly']}]" if rec.get('vs_best_monthly') else ""

        lines.append(f"  #{rec['rank']} {rec['lender']} — {rec['product_name']}")
        lines.append(f"     Rate: {rec['rate']:.3f}%{apr_str}")
        lines.append(f"     Monthly: ${rec['monthly_payment']:,.2f}{vs_best}")
        lines.append(f"     Total cost: ${rec['total_cost']:,.0f}")
        if rec.get('why'):
            lines.append(f"     Why: {rec['why']}")
        lines.append("")

    lines.append(f"Compared {data.get('total_lenders_compared', 0)} lenders")
    lines.append(f"Rates as of: {data.get('rates_as_of', 'N/A')}")
    lines.append(f"\n{DISCLAIMER_NOTE}")
    return "\n".join(lines)


@mcp.tool()
def register(email: str, password: str) -> str:
    """Register for a free API key to access mortgage rate data.

    Creates an account and returns your mort_* API key instantly.
    Free, unlimited access. No credit card required.

    Args:
        email: Your email address
        password: Choose a password (8+ characters)
    """
    try:
        body = {"email": email, "password": password}
        url = f"{BASE_URL}/api/v1/register"
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        if data.get("success"):
            return (
                f"Account created successfully!\n\n"
                f"Your API Key: {data['api_key']}\n\n"
                f"SAVE THIS KEY — it cannot be retrieved later.\n\n"
                f"To use: set MORTGAGE_API_KEY={data['api_key']} in your MCP config."
            )
        else:
            return f"Registration failed: {data.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Registration error: {e}"
