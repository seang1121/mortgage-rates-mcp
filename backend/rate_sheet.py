"""Rate sheet generator — client-ready PNG rate cards for brokers.

Generates a clean, professional image that a realtor can text to a buyer.
Inspired by the Nimrod bet slip generator from the betting analyzer.

Output: base64-encoded PNG string
"""
import base64
import io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from backend.database import db
from backend.extractors.base import PRODUCT_DISPLAY_NAMES
from backend.validators import DISCLAIMER_SHORT

# ── Card Design Constants ───────────────────────────────────────────────────

WIDTH = 820
PADDING = 32
LINE_HEIGHT = 30
HEADER_HEIGHT = 85

# Colors — professional, clean, trust-building
BG = (255, 255, 255)
TEXT = (33, 33, 33)
HEADER_BG = (15, 82, 186)
HEADER_TEXT = (255, 255, 255)
HEADER_SUB = (200, 220, 255)
BEST_COLOR = (0, 140, 60)
BENCHMARK_COLOR = (130, 130, 130)
STALE_COLOR = (200, 150, 50)
DISCLAIMER_COLOR = (160, 160, 160)
DIVIDER = (220, 220, 220)
SECTION_BG = (248, 250, 252)


def generate_rate_sheet(zip_code: str = None, products: list[str] = None,
                        branding_text: str = None) -> str:
    """Generate a rate card PNG. Returns base64-encoded string."""
    products = products or ['30yr', '15yr', 'ARM']

    # Fetch current rates
    rates = db.query("SELECT * FROM rates ORDER BY product, rate ASC")

    # Group by product
    by_product = {}
    for r in rates:
        if r['product'] in products:
            by_product.setdefault(r['product'], []).append(r)

    # Calculate image height dynamically
    total_lines = 0
    for product in products:
        product_rates = by_product.get(product, [])
        if product_rates:
            total_lines += 2 + len(product_rates)
    total_lines += 5  # disclaimer + padding

    height = HEADER_HEIGHT + PADDING + (total_lines * LINE_HEIGHT) + PADDING + 80
    if branding_text:
        height += LINE_HEIGHT + 10

    # ── Create Image ────────────────────────────────────────────────
    img = Image.new('RGB', (WIDTH, height), BG)
    draw = ImageDraw.Draw(img)

    # Load fonts (fall back to default if system fonts unavailable)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        font_bold = ImageFont.truetype("arialbd.ttf", 16)
        font_header = ImageFont.truetype("arialbd.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 11)
        font_rate = ImageFont.truetype("arialbd.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
        font_bold = font
        font_header = font
        font_small = font
        font_rate = font

    # ── Header ──────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (WIDTH, HEADER_HEIGHT)], fill=HEADER_BG)
    draw.text((PADDING, 18), "Mortgage Rate Comparison", fill=HEADER_TEXT, font=font_header)

    subtitle_parts = [datetime.now().strftime("%B %d, %Y at %I:%M %p EST")]
    if zip_code:
        subtitle_parts.append(f"ZIP: {zip_code}")
    draw.text((PADDING, 50), "  |  ".join(subtitle_parts), fill=HEADER_SUB, font=font)

    y = HEADER_HEIGHT + PADDING

    # ── Branding ────────────────────────────────────────────────────
    if branding_text:
        draw.text((PADDING, y), branding_text, fill=TEXT, font=font_bold)
        y += LINE_HEIGHT + 10

    # ── Rate Tables ─────────────────────────────────────────────────
    for product in products:
        product_rates = by_product.get(product, [])
        if not product_rates:
            continue

        label = PRODUCT_DISPLAY_NAMES.get(product, product)

        # Section header with background
        draw.rectangle([(PADDING - 4, y - 2), (WIDTH - PADDING + 4, y + LINE_HEIGHT)], fill=SECTION_BG)
        draw.line([(PADDING, y - 2), (WIDTH - PADDING, y - 2)], fill=DIVIDER, width=1)
        draw.text((PADDING + 4, y + 2), label.upper(), fill=HEADER_BG, font=font_bold)
        y += LINE_HEIGHT + 6

        # Find best non-benchmark rate
        best_lender = None
        for r in product_rates:
            if not r.get('is_benchmark') and not r.get('stale'):
                best_lender = r['lender']
                break

        # Rate rows
        for r in product_rates:
            color = TEXT
            suffix = ""

            if r.get('is_benchmark'):
                color = BENCHMARK_COLOR
                suffix = "  (benchmark)"
            elif r.get('stale'):
                color = STALE_COLOR
                suffix = "  [stale]"
            elif r['lender'] == best_lender:
                color = BEST_COLOR
                suffix = "  BEST"

            rate_str = f"{r['rate']:.3f}%"
            apr_str = f"  ({r['apr']:.3f}% APR)" if r.get('apr') else ""

            # Lender name (left-aligned)
            prefix = ">>>" if r['lender'] == best_lender else "   "
            draw.text((PADDING, y), f"{prefix} {r['lender']}", fill=color, font=font_rate)

            # Rate (right-aligned area)
            rate_text = f"{rate_str}{apr_str}{suffix}"
            draw.text((WIDTH // 2 + 20, y), rate_text, fill=color, font=font_rate)

            y += LINE_HEIGHT

        y += LINE_HEIGHT // 2

    # ── Disclaimer ──────────────────────────────────────────────────
    y += 10
    draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill=DIVIDER, width=1)
    y += 8

    disclaimer = (
        f"Publicly advertised rates as of {datetime.now().strftime('%m/%d/%Y %I:%M %p EST')}. "
        f"Not personalized quotes. Contact lenders for official rates."
    )

    # Word wrap
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

    # ── Encode ──────────────────────────────────────────────────────
    buffer = io.BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    return base64.b64encode(buffer.getvalue()).decode()
