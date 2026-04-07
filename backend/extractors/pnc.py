"""PNC Bank — Top 10 US bank. Akamai protection, rates behind interactive form.

Source: pnc.com/.../mortgage-rates.html
Anti-bot: Akamai Bot Manager
Strategy: Fill the rate form with default values (home value, down payment,
          credit score, ZIP), submit, then extract from the populated rate table.
Products: 30yr, 15yr, ARM (10yr, 20yr also available)
"""
from backend.extractors.base import BaseLenderExtractor, RateResult


class PNCExtractor(BaseLenderExtractor):
    name = "PNC"
    url = "https://www.pnc.com/en/personal-banking/borrowing/home-lending/mortgage-loans/mortgage-rates.html"
    wait_ms = 15000

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Fill PNC's rate calculator form and extract results."""
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
            await page.goto(self.url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(self.wait_ms)

            # Fill form fields (PNC uses a rate calculator with inputs)
            form_fields = [
                ('input[name*="homeValue" i], input[id*="homeValue" i], input[aria-label*="home value" i]', '400000'),
                ('input[name*="downPayment" i], input[id*="downPayment" i], input[aria-label*="down payment" i]', '80000'),
                ('input[name*="zip" i], input[id*="zip" i], input[aria-label*="zip" i]', zip_code),
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
                'button:has-text("See")',
                'button:has-text("Get")',
                'button:has-text("Calculate")',
                'button:has-text("View")',
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
