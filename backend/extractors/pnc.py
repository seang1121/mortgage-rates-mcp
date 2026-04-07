"""PNC Bank — rates via MortgageHog Next.js JSON API. No browser needed.

PNC's own site is behind Akamai TLS fingerprinting that blocks all automation.
MortgageHog.com serves PNC's actual rates as JSON via their Next.js data endpoint.

Source: mortgagehog.com/_next/data/{buildId}/mortgage-rates/lender/pnc/{term}/{purpose}/{productId}.json
Anti-bot: None on MortgageHog
Products: 30yr, 15yr, FHA_30yr, VA_30yr
"""
import json
import re
import ssl
import urllib.request

from backend.extractors.base import BaseLenderExtractor, RateResult


# PNC product IDs on MortgageHog (discovered via their lender page)
PNC_PRODUCTS = [
    {"term": "30", "purpose": "purchase", "product_id": "f6b88db9-fdb9-466f-85bc-b8cf1b6d54ad",
     "product_key": "30yr", "type": "conventional"},
    {"term": "15", "purpose": "purchase", "product_id": "d1a8f44e-a1b5-4724-a11c-436b7586b085",
     "product_key": "15yr", "type": "conventional"},
    {"term": "30", "purpose": "purchase", "product_id": "b1a10241-cad8-4892-bb3c-1a5bc3da1927",
     "product_key": "FHA_30yr", "type": "fha"},
    {"term": "30", "purpose": "purchase", "product_id": "a1631bcd-885b-473b-8510-74dc2762da5e",
     "product_key": "VA_30yr", "type": "va"},
]


class PNCExtractor(BaseLenderExtractor):
    name = "PNC"
    url = "https://www.pnc.com/en/personal-banking/borrowing/home-lending/mortgage-loans/mortgage-rates.html"
    requires_browser = False

    def _get_build_id(self) -> str | None:
        """Fetch MortgageHog's current Next.js build ID (changes on deploys)."""
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(
                "https://mortgagehog.com/mortgage-rates/lender/pnc",
                headers={"User-Agent": "Mozilla/5.0 Chrome/133.0.0.0"}
            )
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                html = r.read().decode("utf-8", errors="replace")
            m = re.search(r'"buildId":"([^"]+)"', html)
            return m.group(1) if m else None
        except Exception as e:
            print(f"[{self.name}] Failed to get MortgageHog build ID: {e}")
            return None

    def fetch(self) -> list[RateResult]:
        """Fetch PNC rates from MortgageHog's Next.js JSON API."""
        build_id = self._get_build_id()
        if not build_id:
            print(f"[{self.name}] Cannot proceed without build ID")
            return []

        results = []
        ctx = ssl.create_default_context()

        for product in PNC_PRODUCTS:
            try:
                url = (
                    f"https://mortgagehog.com/_next/data/{build_id}"
                    f"/mortgage-rates/lender/pnc/{product['term']}"
                    f"/{product['purpose']}/{product['product_id']}.json"
                )
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 Chrome/133.0.0.0",
                    "Accept": "application/json",
                    "x-nextjs-data": "1",
                })
                with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                    data = json.loads(r.read().decode())

                rate_data = data.get("pageProps", {}).get("rateDefault", {})
                rate = rate_data.get("rate")
                apr = rate_data.get("apr") or rate_data.get("calculatedApr")

                if rate is None:
                    continue

                rate_val = float(rate)
                apr_val = float(apr) if apr else None

                if 2.5 <= rate_val <= 14.0:
                    results.append(RateResult(
                        lender=self.name,
                        product=product["product_key"],
                        rate=rate_val,
                        apr=apr_val if apr_val and 2.5 <= apr_val <= 16.0 else None,
                    ))

            except Exception as e:
                print(f"[{self.name}] Failed to fetch {product['product_key']}: {e}")
                continue

        return results

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Override — no browser needed, uses MortgageHog API."""
        return self.fetch()
