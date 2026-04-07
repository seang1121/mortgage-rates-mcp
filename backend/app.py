"""Flask API for the Mortgage Rates MCP Server.

Port 5001. Independent from the betting analyzer (port 5000).
All rate responses include the compliance disclaimer.
Auth via X-API-Key header with mort_* keys.
"""
import os
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from flask import Flask, request, jsonify, g

from backend.database import db
from backend.auth import validate_api_key, register_user
from backend.validators import DISCLAIMER, DISCLAIMER_SHORT
from backend.calculator import full_calculation, compare_scenarios, estimate_savings
from backend.recommender import get_recommendation
from backend.extractors.base import PRODUCT_DISPLAY_NAMES
from backend.extractors import TOTAL_LENDER_COUNT, TOTAL_BENCHMARK_COUNT

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-change-me')

START_TIME = datetime.now()


# ── Auth Middleware ──────────────────────────────────────────────────────────

@app.before_request
def require_api_key():
    """Require mort_* API key on all routes except health and register."""
    # Public endpoints — no auth needed
    public_paths = ['/api/v1/health', '/api/v1/register', '/llms.txt', '/favicon.ico']
    if request.path in public_paths:
        return None

    # All other /api/ routes need a key
    if not request.path.startswith('/api/'):
        return None

    raw_key = request.headers.get('X-API-Key', '')
    if not raw_key:
        return jsonify({
            'error': 'API key required. Pass via X-API-Key header.',
            'get_key': 'POST /api/v1/register with email + password',
        }), 401

    record = validate_api_key(raw_key)
    if record is None:
        return jsonify({'error': 'Invalid API key'}), 401

    if record.get('rate_limited'):
        return jsonify({
            'error': 'Rate limit reached. Try again tomorrow.',
        }), 429

    g.api_user = record


# ── Helper ──────────────────────────────────────────────────────────────────

def _rate_response(data: dict) -> dict:
    """Wrap rate data with disclaimer and timestamp."""
    data['disclaimer'] = DISCLAIMER
    data['timestamp'] = datetime.now().isoformat()
    return data


def _format_rate_row(row: dict) -> dict:
    """Format a database rate row for API output — consumer-friendly."""
    return {
        'lender': row['lender'],
        'product': row['product'],
        'product_name': PRODUCT_DISPLAY_NAMES.get(row['product'], row['product']),
        'rate': row['rate'],
        'apr': row['apr'],
        'is_benchmark': bool(row.get('is_benchmark', 0)),
        'stale': bool(row.get('stale', 0)),
        'scraped_at': row.get('scraped_at'),
    }


# ── Public Endpoints ────────────────────────────────────────────────────────

@app.route('/api/v1/health')
def health():
    """System health check — public, no auth required."""
    uptime_seconds = (datetime.now() - START_TIME).total_seconds()
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    # Last scrape info
    last_scrape = db.query(
        "SELECT MAX(scraped_at) as last, COUNT(DISTINCT lender) as lenders FROM rates"
    )
    last = last_scrape[0] if last_scrape else {}

    # Scrape log stats
    recent_logs = db.query(
        """SELECT status, COUNT(*) as count FROM scrape_logs
           WHERE created_at > datetime('now', '-1 day')
           GROUP BY status"""
    )
    log_stats = {r['status']: r['count'] for r in recent_logs}

    return jsonify({
        'status': 'healthy',
        'uptime': f'{hours}h {minutes}m',
        'last_scrape': last.get('last'),
        'lenders_reporting': last.get('lenders', 0),
        'total_lenders_tracked': TOTAL_LENDER_COUNT,
        'total_benchmarks': TOTAL_BENCHMARK_COUNT,
        'scrape_stats_24h': log_stats,
        'schedule': '7:00 AM and 7:00 PM EST daily',
    })


@app.route('/api/v1/register', methods=['POST'])
def register():
    """Open registration — anyone can sign up and get a mort_* API key."""
    data = request.get_json(force=True) or {}
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()

    result, key_or_error = register_user(email, password)
    if result is None:
        return jsonify({'error': key_or_error}), 400

    return jsonify({
        'success': True,
        'user': {'id': result['id'], 'email': result['email']},
        'api_key': key_or_error,
        'message': 'Save this API key — it cannot be retrieved later.',
        'usage': 'Pass as X-API-Key header on all requests.',
    })


# ── Rate Endpoints ──────────────────────────────────────────────────────────

@app.route('/api/v1/rates')
def get_rates():
    """All current rates, optionally filtered by product/lender/ZIP."""
    product = request.args.get('product', '').strip()
    lender = request.args.get('lender', '').strip()

    query = "SELECT * FROM rates ORDER BY product, rate ASC"
    params = []

    if product or lender:
        conditions = []
        if product:
            conditions.append("product = ?")
            params.append(product)
        if lender:
            conditions.append("lender LIKE ?")
            params.append(f"%{lender}%")
        query = f"SELECT * FROM rates WHERE {' AND '.join(conditions)} ORDER BY product, rate ASC"

    rows = db.query(query, tuple(params))

    # Group by product for consumer-friendly output
    by_product = {}
    for row in rows:
        product_key = row['product']
        if product_key not in by_product:
            by_product[product_key] = {
                'product': product_key,
                'product_name': PRODUCT_DISPLAY_NAMES.get(product_key, product_key),
                'rates': [],
            }
        by_product[product_key]['rates'].append(_format_rate_row(row))

    return jsonify(_rate_response({
        'success': True,
        'products': list(by_product.values()),
        'total_rates': len(rows),
    }))


@app.route('/api/v1/rates/best')
def get_best_rate():
    """Best (lowest) rate per product across all lenders."""
    product = request.args.get('product', '').strip()

    if product:
        rows = db.query(
            """SELECT * FROM rates WHERE product = ? AND is_benchmark = 0 AND stale = 0
               ORDER BY rate ASC LIMIT 1""",
            (product,)
        )
    else:
        # Best rate for each product
        rows = db.query("""
            SELECT r.* FROM rates r
            INNER JOIN (
                SELECT product, MIN(rate) as min_rate
                FROM rates WHERE is_benchmark = 0 AND stale = 0
                GROUP BY product
            ) best ON r.product = best.product AND r.rate = best.min_rate
            WHERE r.is_benchmark = 0 AND r.stale = 0
            GROUP BY r.product
        """)

    best_rates = [_format_rate_row(row) for row in rows]

    return jsonify(_rate_response({
        'success': True,
        'best_rates': best_rates,
    }))


@app.route('/api/v1/rates/compare')
def compare_lenders_endpoint():
    """Side-by-side comparison of specific lenders."""
    lenders_param = request.args.get('lenders', '')
    product = request.args.get('product', '').strip()

    if not lenders_param:
        return jsonify({'error': 'lenders parameter required (comma-separated)'}), 400

    lender_names = [l.strip() for l in lenders_param.split(',') if l.strip()][:20]  # cap at 20

    conditions = ' OR '.join(['lender LIKE ?' for _ in lender_names])
    params = [f"%{name}%" for name in lender_names]

    if product:
        query = f"SELECT * FROM rates WHERE ({conditions}) AND product = ? ORDER BY rate ASC"
        params.append(product)
    else:
        query = f"SELECT * FROM rates WHERE ({conditions}) ORDER BY product, rate ASC"

    rows = db.query(query, tuple(params))

    # Group by lender for side-by-side view
    by_lender = {}
    for row in rows:
        lender = row['lender']
        if lender not in by_lender:
            by_lender[lender] = []
        by_lender[lender].append(_format_rate_row(row))

    return jsonify(_rate_response({
        'success': True,
        'comparison': by_lender,
        'lenders_found': list(by_lender.keys()),
    }))


@app.route('/api/v1/rates/history')
def get_rate_history():
    """Historical trend data — up to 90 days with AM/PM granularity."""
    product = request.args.get('product', '30yr')
    lender = request.args.get('lender', '').strip()
    days = min(request.args.get('days', 30, type=int) or 30, 90)

    query = """SELECT date, time_of_day, lender, product, rate, apr
               FROM rate_history
               WHERE product = ? AND date >= date('now', ?)"""
    params = [product, f'-{days} days']

    if lender:
        query += " AND lender LIKE ?"
        params.append(f"%{lender}%")

    query += " ORDER BY date ASC, time_of_day ASC"
    rows = db.query(query, tuple(params))

    # Group by date for trend view
    by_date = {}
    for row in rows:
        date_key = f"{row['date']} {row['time_of_day']}"
        if date_key not in by_date:
            by_date[date_key] = {'date': row['date'], 'time_of_day': row['time_of_day'], 'rates': []}
        by_date[date_key]['rates'].append({
            'lender': row['lender'],
            'rate': row['rate'],
            'apr': row['apr'],
        })

    # Calculate daily averages for trend
    daily_avgs = []
    for key, data in by_date.items():
        rates = [r['rate'] for r in data['rates']]
        if rates:
            daily_avgs.append({
                'date': data['date'],
                'time_of_day': data['time_of_day'],
                'avg_rate': round(sum(rates) / len(rates), 3),
                'min_rate': round(min(rates), 3),
                'max_rate': round(max(rates), 3),
                'lender_count': len(rates),
            })

    # Direction indicator
    direction = "flat"
    if len(daily_avgs) >= 2:
        first_avg = daily_avgs[0]['avg_rate']
        last_avg = daily_avgs[-1]['avg_rate']
        diff = last_avg - first_avg
        if diff > 0.01:
            direction = "up"
        elif diff < -0.01:
            direction = "down"

    return jsonify(_rate_response({
        'success': True,
        'product': product,
        'product_name': PRODUCT_DISPLAY_NAMES.get(product, product),
        'days': days,
        'direction': direction,
        'daily_summary': daily_avgs,
        'detailed': list(by_date.values()),
    }))


@app.route('/api/v1/rates/lender/<lender_name>')
def get_lender_details(lender_name):
    """All products from one specific lender."""
    rows = db.query(
        "SELECT * FROM rates WHERE lender LIKE ? ORDER BY rate ASC",
        (f"%{lender_name}%",)
    )

    if not rows:
        return jsonify({'error': f'Lender "{lender_name}" not found in current rates'}), 404

    products = [_format_rate_row(row) for row in rows]
    actual_name = rows[0]['lender']

    return jsonify(_rate_response({
        'success': True,
        'lender': actual_name,
        'products': products,
    }))


@app.route('/api/v1/rates/scenarios')
def compare_scenarios_endpoint():
    """30yr vs 15yr vs ARM — side by side with monthly payments and breakeven."""
    amount = request.args.get('amount', type=float)
    down_pct = request.args.get('down_payment_pct', 20, type=float)

    if not amount:
        return jsonify({'error': 'amount parameter required (home price)'}), 400

    # Get best rate for each product
    products_query = db.query("""
        SELECT product, MIN(rate) as best_rate
        FROM rates WHERE is_benchmark = 0 AND stale = 0
        GROUP BY product
    """)

    rates_dict = {r['product']: r['best_rate'] for r in products_query}
    if not rates_dict:
        return jsonify({'error': 'No rates available. Try again after the next scrape.'}), 404

    results = compare_scenarios(amount, rates_dict, down_pct)

    return jsonify(_rate_response({
        'success': True,
        'home_price': amount,
        'down_payment_pct': down_pct,
        'scenarios': results,
    }))


@app.route('/api/v1/rates/savings')
def estimate_savings_endpoint():
    """Calculate savings from switching lenders."""
    amount = request.args.get('amount', type=float)
    from_lender = request.args.get('from', '').strip()
    to_lender = request.args.get('to', '').strip()
    product = request.args.get('product', '30yr')

    if not amount or not from_lender or not to_lender:
        return jsonify({'error': 'Required: amount, from, to parameters'}), 400

    # Look up current rates for both lenders
    from_rate = db.query(
        "SELECT rate FROM rates WHERE lender LIKE ? AND product = ? LIMIT 1",
        (f"%{from_lender}%", product)
    )
    to_rate = db.query(
        "SELECT rate FROM rates WHERE lender LIKE ? AND product = ? LIMIT 1",
        (f"%{to_lender}%", product)
    )

    if not from_rate:
        return jsonify({'error': f'Lender "{from_lender}" not found for {product}'}), 404
    if not to_rate:
        return jsonify({'error': f'Lender "{to_lender}" not found for {product}'}), 404

    result = estimate_savings(amount, from_rate[0]['rate'], to_rate[0]['rate'])
    result['from_lender'] = from_lender
    result['to_lender'] = to_lender
    result['product'] = product

    return jsonify(_rate_response({
        'success': True,
        'savings': result,
    }))


# ── Calculator ──────────────────────────────────────────────────────────────

@app.route('/api/v1/calculate', methods=['POST'])
def calculate_payment():
    """Monthly payment calculator with full breakdown."""
    data = request.get_json(force=True) or {}
    loan_amount = data.get('loan_amount')
    rate = data.get('rate')
    term_years = data.get('term_years', 30)
    down_payment_pct = data.get('down_payment_pct', 0)

    if not loan_amount:
        return jsonify({'error': 'loan_amount required'}), 400

    # If rate not provided, use best available 30yr
    if rate is None:
        best = db.query(
            "SELECT rate FROM rates WHERE product = '30yr' AND is_benchmark = 0 AND stale = 0 ORDER BY rate ASC LIMIT 1"
        )
        if best:
            rate = best[0]['rate']
        else:
            return jsonify({'error': 'rate required (no rates available to default)'}), 400

    result = full_calculation(loan_amount, rate, term_years, down_payment_pct)

    return jsonify(_rate_response({
        'success': True,
        'calculation': result,
    }))


# ── Recommendation ──────────────────────────────────────────────────────────

@app.route('/api/v1/recommend', methods=['POST'])
def recommend():
    """AI-powered ranked recommendations based on borrower profile."""
    data = request.get_json(force=True) or {}
    loan_amount = data.get('loan_amount')

    if not loan_amount:
        return jsonify({'error': 'loan_amount required'}), 400

    result = get_recommendation(
        loan_amount=loan_amount,
        credit_score=data.get('credit_score', 740),
        down_payment_pct=data.get('down_payment_pct', 20),
        product=data.get('product'),
        property_type=data.get('property_type', 'single_family'),
        loan_purpose=data.get('loan_purpose', 'purchase'),
    )

    return jsonify(_rate_response({
        'success': True,
        **result,
    }))


# ── Rate Sheet ──────────────────────────────────────────────────────────────

@app.route('/api/v1/rate-sheet', methods=['POST'])
def generate_rate_sheet():
    """Generate a client-ready rate card image (PNG, base64-encoded)."""
    data = request.get_json(force=True) or {}

    from backend.rate_sheet import generate_rate_sheet as gen_sheet
    image_b64 = gen_sheet(
        zip_code=data.get('zip_code'),
        products=data.get('products'),
        branding_text=data.get('branding_text'),
    )

    return jsonify({
        'success': True,
        'image_base64': image_b64,
        'format': 'PNG',
        'disclaimer': DISCLAIMER,
    })


# ── Alerts ──────────────────────────────────────────────────────────────────

@app.route('/api/v1/alerts', methods=['GET'])
def list_alerts():
    """List current user's rate alerts."""
    user_id = g.api_user['user_id']
    alerts = db.query(
        "SELECT * FROM rate_alerts WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    return jsonify({
        'success': True,
        'alerts': [dict(a) for a in alerts],
    })


@app.route('/api/v1/alerts', methods=['POST'])
def create_alert():
    """Create a rate threshold alert."""
    data = request.get_json(force=True) or {}
    product = data.get('product')
    threshold = data.get('threshold')

    if not product or threshold is None:
        return jsonify({'error': 'product and threshold required'}), 400

    # Validate product is a known type
    from backend.extractors.base import VALID_PRODUCTS
    if product not in VALID_PRODUCTS:
        return jsonify({'error': f'Invalid product. Valid: {", ".join(sorted(VALID_PRODUCTS))}'}), 400

    # Validate threshold is a reasonable number
    try:
        threshold = float(threshold)
        if not (1.0 <= threshold <= 15.0):
            return jsonify({'error': 'Threshold must be between 1.0 and 15.0'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Threshold must be a number'}), 400

    user_id = g.api_user['user_id']
    db.execute(
        """INSERT INTO rate_alerts (user_id, product, threshold, lender)
           VALUES (?, ?, ?, ?)""",
        (user_id, product, float(threshold), data.get('lender'))
    )

    return jsonify({
        'success': True,
        'message': f'Alert created: notify when {PRODUCT_DISPLAY_NAMES.get(product, product)} drops below {threshold}%',
    })


@app.route('/api/v1/alerts/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """Delete a rate alert."""
    user_id = g.api_user['user_id']
    db.execute(
        "DELETE FROM rate_alerts WHERE id = ? AND user_id = ?",
        (alert_id, user_id)
    )
    return jsonify({'success': True, 'message': 'Alert deleted'})


# ── Admin ───────────────────────────────────────────────────────────────────

@app.route('/api/v1/admin/scrape', methods=['POST'])
def admin_scrape():
    """Trigger a manual scrape (admin only)."""
    if g.api_user.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    from backend.scraper import run_scrape
    data = request.get_json(force=True) or {}
    zip_code = data.get('zip_code')

    result = run_scrape(zip_code)
    return jsonify({'success': True, 'scrape_result': result})


# ── llms.txt ────────────────────────────────────────────────────────────────

@app.route('/llms.txt')
def llms_txt():
    """Serve llms.txt for AI agent discovery."""
    llms_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'llms.txt')
    try:
        with open(llms_path) as f:
            return f.read(), 200, {'Content-Type': 'text/plain'}
    except FileNotFoundError:
        return "mortgage-rates-mcp — llms.txt not yet generated", 200, {'Content-Type': 'text/plain'}


# ── Startup ─────────────────────────────────────────────────────────────────

# ── Global Error Handler ────────────────────────────────────────────────────

@app.errorhandler(Exception)
def handle_exception(e):
    """Catch unhandled exceptions — never expose stack traces to users."""
    print(f"[ERROR] Unhandled exception: {e}")
    import traceback
    traceback.print_exc()
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({'error': 'Method not allowed'}), 405


# ── Startup ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import signal
    import sys

    from backend.scheduler import start_scheduler
    start_scheduler()

    def graceful_shutdown(signum, frame):
        print("\n[APP] Shutting down gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    port = int(os.getenv('FLASK_PORT', 5001))
    print(f"Mortgage Rates API starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
