"""Chase — Big 4 bank. Akamai Bot Manager protection.

Source: chase.com/personal/mortgage/mortgage-rates
Anti-bot: Akamai Bot Manager (heavy)
Strategy: Use simpler AEM endpoint for more predictable DOM structure.
          Falls back to CDP connection if standard scrape fails.
Products: 30yr, 15yr, ARM, FHA, VA
"""
from backend.extractors.base import BaseLenderExtractor, RateResult


class ChaseExtractor(BaseLenderExtractor):
    name = "Chase"
    # AEM structured endpoint — simpler DOM than the Next.js main page
    url = "https://www.chase.com/content/chase-ux/en/structured/module/home-lending/mortgage-rates-purchase1-foryextonly.html"
    wait_ms = 12000

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Try AEM endpoint first, then main page, then CDP fallback."""
        # Attempt 1: AEM structured endpoint (simpler DOM)
        results = await super().scrape(browser, zip_code)
        if results:
            return results

        # Attempt 2: Main page
        self.url = "https://www.chase.com/personal/mortgage/mortgage-rates"
        self.wait_ms = 15000
        results = await super().scrape(browser, zip_code)
        if results:
            return results

        # Attempt 3: CDP fallback (connect to running OpenClaw browser)
        return await self._try_cdp_fallback(zip_code)

    async def _try_cdp_fallback(self, zip_code: str) -> list[RateResult]:
        """Connect to OpenClaw browser via CDP for heavy anti-bot bypass."""
        try:
            from patchright.async_api import async_playwright
            async with async_playwright() as pw:
                cdp_browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:18800")
                context = cdp_browser.contexts[0] if cdp_browser.contexts else await cdp_browser.new_context()
                page = await context.new_page()

                await page.goto(
                    "https://www.chase.com/personal/mortgage/mortgage-rates",
                    timeout=20000, wait_until="domcontentloaded"
                )
                await page.wait_for_timeout(3000)

                # Fill ZIP and submit
                await self._try_zip_input(page, zip_code)

                # Wait for rate table to render
                try:
                    await page.wait_for_function(
                        "() => { const t = document.querySelector('table'); return t && t.innerText.includes('%'); }",
                        timeout=10000
                    )
                except Exception:
                    pass

                # Extract rate data from DOM
                table_text = await page.evaluate("""() => {
                    const el = document.querySelector('table') ||
                               document.querySelector('[class*="rate"]') ||
                               document.querySelector('[data-testid*="rate"]');
                    return el ? el.innerText : document.body.innerText;
                }""")

                await page.close()
                if table_text and "%" in table_text:
                    return self.extract(table_text)
        except Exception:
            pass
        return []
