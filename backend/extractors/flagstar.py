"""Flagstar Bank (NYCB) — large mortgage servicer. Cloudflare protection.

Source: flagstar.com/.../mortgage-rates.html
Anti-bot: Cloudflare (managed challenge / Turnstile)
Strategy: Fill the rate form (purchase price, down payment, ZIP, credit score)
          and submit. JS assets are behind Cloudflare but patchright should pass.
Products: 30yr, 15yr, ARM, Jumbo
"""
from backend.extractors.base import BaseLenderExtractor, RateResult


class FlagstarExtractor(BaseLenderExtractor):
    name = "Flagstar"
    url = "https://www.flagstar.com/personal/borrow/home-loans/mortgage-rates.html"
    wait_ms = 15000

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Fill Flagstar's rate form and extract results after Cloudflare."""
        try:
            ctx = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = await ctx.new_page()
            await page.goto(self.url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(self.wait_ms)

            # Fill form fields
            form_fields = [
                ('input[name*="purchasePrice" i], input[id*="purchasePrice" i]', '400000'),
                ('input[name*="downPayment" i], input[id*="downPayment" i]', '80000'),
                ('input[name*="zip" i], input[name*="Zipcode" i], input[id*="zip" i]', zip_code),
            ]

            for selectors, value in form_fields:
                for sel in selectors.split(', '):
                    el = await page.query_selector(sel)
                    if el:
                        await el.fill(value)
                        await page.wait_for_timeout(300)
                        break

            # Submit form
            for btn_sel in [
                'button:has-text("Submit")',
                'button:has-text("See")',
                'button:has-text("Get")',
                'input[type="submit"]',
                'button[type="submit"]',
            ]:
                btn = await page.query_selector(btn_sel)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(8000)
                    break

            text = await page.inner_text("body")
            await ctx.close()
            return self.extract(text)
        except Exception:
            try:
                await ctx.close()
            except Exception:
                pass
            return []
