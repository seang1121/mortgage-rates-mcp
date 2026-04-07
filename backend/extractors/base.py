"""Base class for all lender extractors + RateResult data model."""
from dataclasses import dataclass, asdict
from typing import Optional
import re


# Human-readable product names for API responses
PRODUCT_DISPLAY_NAMES = {
    '30yr': '30-Year Fixed',
    '15yr': '15-Year Fixed',
    'ARM': 'Adjustable Rate (ARM)',
    'FHA_30yr': 'FHA 30-Year Fixed',
    'VA_30yr': 'VA 30-Year Fixed',
}

# All valid product keys
VALID_PRODUCTS = set(PRODUCT_DISPLAY_NAMES.keys())


@dataclass
class RateResult:
    """A single rate extracted from a lender's website."""
    lender: str
    product: str           # '30yr', '15yr', 'ARM', 'FHA_30yr', 'VA_30yr'
    rate: float            # Base interest rate (e.g., 6.500)
    apr: Optional[float] = None  # Annual percentage rate including fees
    is_benchmark: bool = False   # True for Freddie Mac / MND

    @property
    def display_product(self) -> str:
        return PRODUCT_DISPLAY_NAMES.get(self.product, self.product)

    def to_dict(self) -> dict:
        return {
            'lender': self.lender,
            'product': self.product,
            'product_name': self.display_product,
            'rate': self.rate,
            'apr': self.apr,
            'is_benchmark': self.is_benchmark,
        }


class BaseLenderExtractor:
    """Abstract base for lender-specific rate extractors.

    Subclasses must set `name` and `url`. Override `extract()` for custom
    parsing logic or `scrape()` for custom browser interaction.
    """
    name: str = ""
    url: str = ""
    is_benchmark: bool = False
    requires_browser: bool = True
    wait_ms: int = 10000

    # ── Regex patterns for fallback extraction ──────────────────────

    # Product label patterns — match how lenders describe their products
    PRODUCT_LABELS = {
        '30yr': r'30[- ]?[Yy]ear(?:\s*[Ff]ixed)?',
        '15yr': r'15[- ]?[Yy]ear(?:\s*[Ff]ixed)?',
        'ARM': r'(?:7/6|7/1|5/1|10/6)\s*(?:ARM|Adj)',
        'FHA_30yr': r'FHA\s*30[- ]?[Yy]ear',
        'VA_30yr': r'VA\s*30[- ]?[Yy]ear',
    }

    # Rate+APR extraction patterns (tried in order, first match wins)
    RATE_PATTERNS = [
        # "30-Year Fixed ... 6.500% ... APR: 6.738%"
        r'{label}.*?(\d\.\d{{2,3}})%.*?(?:APR|apr)[:\s]*(\d\.\d{{2,3}})%',
        # "30-Year Fixed    6.500%    6.738%"  (tab/space separated)
        r'{label}[\t\s]+(\d\.\d{{2,3}})%[\t\s]+(\d\.\d{{2,3}})%',
        # "30-Year Fixed is 6.500% (6.738% APR)"
        r'{label}.*?is\s+(\d\.\d{{2,3}})%\s*\((\d\.\d{{2,3}})%\s*APR\)',
        # "30-Year Fixed ... Rate ... 6.500% ... APR ... 6.738%" (Mr. Cooper style)
        r'{label}.*?Rate.*?(\d\.\d{{2,3}})%.*?APR.*?(\d\.\d{{2,3}})%',
    ]

    # Rate-only fallback (no APR captured)
    RATE_ONLY_PATTERN = r'{label}[^\d]*?(\d\.\d{{2,3}})%'

    # ── Extraction ──────────────────────────────────────────────────

    def extract(self, page_content: str) -> list[RateResult]:
        """Extract rates from page text. Override for lender-specific logic.

        The default implementation uses regex patterns. Subclasses can override
        to use CSS selectors, JSON parsing, or any other method, and fall back
        to this via super().extract(text) if their method finds nothing.
        """
        return self._regex_extract(page_content)

    def _regex_extract(self, text: str) -> list[RateResult]:
        """Fallback regex extraction — works across most lender page formats."""
        results = []
        for product, label_pattern in self.PRODUCT_LABELS.items():
            found = False

            # Try each rate+APR pattern
            for pattern_template in self.RATE_PATTERNS:
                pattern = pattern_template.format(label=label_pattern)
                m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if m:
                    rate_val = float(m.group(1))
                    apr_val = float(m.group(2))
                    # Basic sanity: rate and APR must be in realistic range
                    if 2.5 <= rate_val <= 14.0 and 2.5 <= apr_val <= 16.0:
                        results.append(RateResult(
                            lender=self.name, product=product,
                            rate=rate_val, apr=apr_val,
                            is_benchmark=self.is_benchmark
                        ))
                        found = True
                        break

            # Fallback: rate only (no APR)
            if not found:
                pattern = self.RATE_ONLY_PATTERN.format(label=label_pattern)
                m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if m:
                    rate_val = float(m.group(1))
                    if 2.5 <= rate_val <= 14.0:
                        results.append(RateResult(
                            lender=self.name, product=product,
                            rate=rate_val, apr=None,
                            is_benchmark=self.is_benchmark
                        ))

        return results

    # ── Browser scraping ────────────────────────────────────────────

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Scrape this lender's page using patchright stealth browser.

        Override for lenders that need custom interaction (form fill,
        button clicks, CDP fallback, etc.).
        """
        try:
            ctx = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/133.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = await ctx.new_page()
            await page.goto(self.url, timeout=25000, wait_until="domcontentloaded")
            await page.wait_for_timeout(self.wait_ms)

            # Auto-detect and fill ZIP code fields
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
        """Auto-detect ZIP code input fields and fill + submit them."""
        for sel in [
            'input[name*="zip" i]',
            'input[placeholder*="ZIP" i]',
            'input[placeholder*="zip" i]',
            'input[id*="zip" i]',
            'input[aria-label*="zip" i]',
        ]:
            el = await page.query_selector(sel)
            if el:
                await el.fill(zip_code)
                await page.wait_for_timeout(500)
                # Try to find and click submit/update button
                for btn_sel in [
                    'button[type="submit"]',
                    'button:has-text("Update")',
                    'button:has-text("Get")',
                    'button:has-text("View")',
                    'button:has-text("See")',
                    'button:has-text("Search")',
                    'input[type="submit"]',
                ]:
                    btn = await page.query_selector(btn_sel)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(5000)
                        break
                break
