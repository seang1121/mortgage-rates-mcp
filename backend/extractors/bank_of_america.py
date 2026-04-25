"""Bank of America — Big 4 bank.

Source: bankofamerica.com/mortgage/mortgage-rates/ (public rate table)
Anti-bot: Light. SPA — needs networkidle and DOM-text scrape, not body innerText.
Products: 30yr, 15yr, ARM, FHA_30yr, VA_30yr

Note: previously used a promo subCampCode URL that stopped serving rates on
first paint (lead-capture form only). Switched to the canonical rates page.
"""
from backend.extractors.base import BaseLenderExtractor, RateResult
from backend.stealth import build_context_options, human_delay, simulate_human


class BankOfAmericaExtractor(BaseLenderExtractor):
    name = "Bank of America"
    url = "https://www.bankofamerica.com/mortgage/mortgage-rates/"
    wait_ms = 8000

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        ctx = None
        try:
            ctx = await browser.new_context(**build_context_options())
            page = await ctx.new_page()

            await human_delay(300, 1200)
            await page.goto(self.url, timeout=30000, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout(self.wait_ms)
            await simulate_human(page)
            await self._try_zip_input(page, zip_code)

            try:
                await page.wait_for_function(
                    "() => /\\d\\.\\d{2,3}\\s*%/.test(document.body.innerText)"
                    " && document.body.innerText.match(/30[- ]?Year/i)",
                    timeout=12000,
                )
            except Exception:
                pass

            text = await page.inner_text("body")
            await ctx.close()
            return self.extract(text)
        except Exception:
            if ctx:
                try:
                    await ctx.close()
                except Exception:
                    pass
            raise
