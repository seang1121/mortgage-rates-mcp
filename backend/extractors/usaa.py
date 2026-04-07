"""USAA — military credit union. Rates via third-party aggregator.

USAA's own site is behind heavy Akamai and only shows sample/promotional rates,
not real-time rates. They require contacting a loan officer for actual rates.

We scrape USAA's rate data from NerdWallet/Bankrate review pages which have
the same sample rates with much lighter anti-bot protection.

Source: nerdwallet.com/mortgages/reviews/usaa-mortgage (fallback: bankrate.com)
Products: 30yr, 15yr, VA_30yr
"""
import re
import ssl
import urllib.request

from backend.extractors.base import BaseLenderExtractor, RateResult


class USAAExtractor(BaseLenderExtractor):
    name = "USAA"
    url = "https://www.usaa.com/bank/mortgage-rates"
    requires_browser = False

    SOURCES = [
        "https://www.nerdwallet.com/mortgages/reviews/usaa-mortgage",
        "https://www.bankrate.com/mortgages/reviews/usaa/",
    ]

    def fetch(self) -> list[RateResult]:
        """Fetch USAA rates from third-party review sites."""
        ctx = ssl.create_default_context()

        for source_url in self.SOURCES:
            try:
                req = urllib.request.Request(source_url, headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/133.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                })
                with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                    html = r.read().decode("utf-8", errors="replace")

                # Strip HTML tags for text extraction
                text = re.sub(r'<[^>]+>', ' ', html)

                # Use the base regex extraction — it handles the standard
                # "30-Year Fixed ... X.XXX% ... APR ... X.XXX%" patterns
                results = self.extract(text)

                if results:
                    # Override lender name (base extract uses self.name which is "USAA")
                    return results

            except Exception as e:
                print(f"[{self.name}] Failed to fetch from {source_url}: {e}")
                continue

        # Final fallback: try USAA directly with patchright (probably fails)
        return []

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Try HTTP fetch first, fall back to browser if it fails."""
        results = self.fetch()
        if results:
            return results
        # Browser fallback (likely to fail due to Akamai, but worth trying)
        return await super().scrape(browser, zip_code)
