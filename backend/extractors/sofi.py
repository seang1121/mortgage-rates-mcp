"""SoFi — online lender. Competitive rates, tech-forward.

Source: sofi.com/home-loans/mortgage-rates/
Rates are server-rendered into Next.js React component props as `RateBox`
elements with `boxRateText`, `boxAprText`, and `eyeBrowText` (term label).
They never appear in body.innerText, so we parse page.content() HTML.
Products served: 15yr, 30yr (10yr and 20yr ignored — not in our schema).
"""
import re
from backend.extractors.base import BaseLenderExtractor, RateResult
from backend.stealth import build_context_options, human_delay, simulate_human


_RATEBOX_RE = re.compile(
    r'RateBox,\{[^}]{0,500}'
    r'boxAprText:\s*"\s*(?P<apr>\d\.\d{2,3})\s*%[^}]*?'
    r'boxRateText:\s*"\s*(?P<rate>\d\.\d{2,3})\s*%[^}]*?'
    r'eyeBrowText:\s*"\s*(?P<term>\d{1,2})-year',
    re.IGNORECASE,
)

_TERM_TO_PRODUCT = {'15': '15yr', '30': '30yr'}


class SoFiExtractor(BaseLenderExtractor):
    name = "SoFi"
    url = "https://www.sofi.com/home-loans/mortgage-rates/"
    wait_ms = 6000

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        ctx = None
        try:
            ctx = await browser.new_context(**build_context_options())
            page = await ctx.new_page()

            await human_delay(300, 1200)
            await page.goto(self.url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(self.wait_ms)
            await simulate_human(page)

            html = await page.content()
            await ctx.close()
            return self._parse(html)
        except Exception:
            if ctx:
                try:
                    await ctx.close()
                except Exception:
                    pass
            raise

    def _parse(self, html: str) -> list[RateResult]:
        results = []
        seen = set()
        for m in _RATEBOX_RE.finditer(html):
            product = _TERM_TO_PRODUCT.get(m.group('term'))
            if not product or product in seen:
                continue
            rate = float(m.group('rate'))
            apr = float(m.group('apr'))
            if not (2.5 <= rate <= 14.0 and 2.5 <= apr <= 16.0):
                continue
            seen.add(product)
            results.append(RateResult(
                lender=self.name, product=product, rate=rate, apr=apr,
                is_benchmark=False,
            ))
        return results
