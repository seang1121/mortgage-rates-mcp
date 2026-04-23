"""Rocket Mortgage — #1 retail mortgage lender in the US. Akamai protection.

Source: rocketmortgage.com/mortgage-rates
Anti-bot: Akamai Bot Manager (present but does NOT block SSR content)
Strategy: Rates are server-side rendered in the initial HTML inside
          <sc-rate-card> components with data-ssr attributes:
            - data-ssr-product-code="130" (product identifier)
            - data-ssr-rate (interest rate text)
            - data-ssr-apr (APR text)
          Extract from raw HTML via page.content(), NOT inner_text.
          Inner text strips the attribute context needed to pair
          product names with their rate/APR values.
Products: 30yr (130), 15yr (330), FHA_30yr (930), VA_30yr (830V)
          Also available: 20yr (230), Jumbo (RJ30) — not tracked.
"""
import re
from backend.extractors.base import BaseLenderExtractor, RateResult


# Rocket product codes -> our product keys
ROCKET_PRODUCT_MAP = {
    '130': '30yr',       # 30-year fixed
    '330': '15yr',       # 15-year fixed
    '930': 'FHA_30yr',   # 30-year FHA
    '830V': 'VA_30yr',   # 30-year VA
    # '230': '20yr',     # 20-year fixed — not in our product set
    # 'RJ30': 'jumbo',   # 30-year jumbo — not in our product set
}


class RocketMortgageExtractor(BaseLenderExtractor):
    name = "Rocket Mortgage"
    url = "https://www.rocketmortgage.com/mortgage-rates"
    wait_ms = 8000  # SSR rates load instantly; short wait for Akamai sensor

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Extract rates from SSR HTML using data-ssr attributes."""
        from backend.stealth import build_context_options, human_delay, simulate_human

        try:
            ctx = await browser.new_context(**build_context_options())
            page = await ctx.new_page()

            await human_delay(300, 1000)
            await page.goto(self.url, timeout=25000, wait_until="domcontentloaded")
            await page.wait_for_timeout(self.wait_ms)
            await simulate_human(page)

            # Try DOM-based extraction first (most reliable)
            results = await self._extract_from_dom(page)

            # Fallback: extract from raw HTML source
            if not results:
                html = await page.content()
                results = self._extract_from_html(html)

            # Final fallback: regex on inner text
            if not results:
                text = await page.inner_text("body")
                results = self.extract(text)

            await ctx.close()
            return results
        except Exception:
            try:
                await ctx.close()
            except Exception:
                pass
            return []

    async def _extract_from_dom(self, page) -> list[RateResult]:
        """Use page.evaluate() to pull rate data from DOM elements."""
        try:
            cards = await page.evaluate("""() => {
                const results = [];
                const cards = document.querySelectorAll('sc-rate-card[data-ssr-product-code]');
                for (const card of cards) {
                    const code = card.getAttribute('data-ssr-product-code');
                    const rateEl = card.querySelector('[data-ssr-rate]');
                    const aprEl = card.querySelector('[data-ssr-apr]');
                    if (rateEl && aprEl) {
                        results.push({
                            code: code,
                            rate: rateEl.textContent.trim(),
                            apr: aprEl.textContent.trim()
                        });
                    }
                }
                return results;
            }""")

            results = []
            for card in cards:
                product = ROCKET_PRODUCT_MAP.get(card['code'])
                if not product:
                    continue
                rate_val = self._parse_percent(card['rate'])
                apr_val = self._parse_percent(card['apr'])
                if rate_val and 2.5 <= rate_val <= 14.0:
                    results.append(RateResult(
                        lender=self.name,
                        product=product,
                        rate=rate_val,
                        apr=apr_val if apr_val and 2.5 <= apr_val <= 16.0 else None,
                    ))
            return results
        except Exception:
            return []

    def _extract_from_html(self, html: str) -> list[RateResult]:
        """Parse raw HTML for data-ssr attributes when DOM eval fails."""
        results = []
        # Match each rate card block by product code
        card_pattern = re.compile(
            r'data-ssr-product-code="([^"]+)"'
            r'.*?data-ssr-rate[^>]*>\s*([^<]+)'
            r'.*?data-ssr-apr[^>]*>\s*([^<]+)',
            re.DOTALL,
        )

        for m in card_pattern.finditer(html):
            code = m.group(1)
            product = ROCKET_PRODUCT_MAP.get(code)
            if not product:
                continue

            rate_val = self._parse_percent(m.group(2).strip())
            apr_val = self._parse_percent(m.group(3).strip())

            if rate_val and 2.5 <= rate_val <= 14.0:
                results.append(RateResult(
                    lender=self.name,
                    product=product,
                    rate=rate_val,
                    apr=apr_val if apr_val and 2.5 <= apr_val <= 16.0 else None,
                ))
        return results

    @staticmethod
    def _parse_percent(text: str) -> float | None:
        """Extract numeric value from '6.750%' or '6.75 %' style strings."""
        m = re.search(r'(\d+\.\d+)\s*%', text)
        return float(m.group(1)) if m else None
