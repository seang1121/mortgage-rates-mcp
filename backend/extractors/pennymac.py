"""PennyMac — Top 5 mortgage servicer. Clean REST JSON API, no browser needed.

Source: quote.pennymac.com/api/v1/rate-sheet/stored/*
Updated: Daily
Products: Conventional (30yr, 15yr), FHA, VA, Jumbo, ARM

PennyMac exposes a fully public JSON API for their rate sheets.
No authentication, no reCAPTCHA, no browser needed.
"""
import json
import ssl
import urllib.request

from backend.extractors.base import BaseLenderExtractor, RateResult


class PennyMacExtractor(BaseLenderExtractor):
    name = "PennyMac"
    url = "https://quote.pennymac.com/api/v1/rate-sheet/stored/conventional-home-loans"
    requires_browser = False

    # All available rate sheet endpoints
    ENDPOINTS = {
        "conventional": "https://quote.pennymac.com/api/v1/rate-sheet/stored/conventional-home-loans",
        "fha": "https://quote.pennymac.com/api/v1/rate-sheet/stored/fha-home-loans",
        "va": "https://quote.pennymac.com/api/v1/rate-sheet/stored/va-purchase",
        "jumbo": "https://quote.pennymac.com/api/v1/rate-sheet/stored/jumbo-loans",
    }

    def fetch(self) -> list[RateResult]:
        """Fetch rates from all PennyMac rate sheet endpoints."""
        results = []
        ctx = ssl.create_default_context()

        for category, endpoint_url in self.ENDPOINTS.items():
            try:
                req = urllib.request.Request(endpoint_url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                })
                with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                    data = json.loads(r.read().decode())

                for rate_item in data.get("bestRates", []):
                    product = self._map_product(rate_item.get("name", ""), category)
                    if not product:
                        continue

                    rate = rate_item.get("rate")
                    apr = rate_item.get("apr")
                    if rate is None:
                        continue

                    results.append(RateResult(
                        lender=self.name,
                        product=product,
                        rate=float(rate),
                        apr=float(apr) if apr else None,
                    ))
            except Exception as e:
                print(f"[{self.name}] Failed to fetch {category}: {e}")
                continue

        # Dedup: keep only the lowest rate per product
        best_by_product = {}
        for r in results:
            if r.product not in best_by_product or r.rate < best_by_product[r.product].rate:
                best_by_product[r.product] = r
        return list(best_by_product.values())

    def _map_product(self, name: str, category: str) -> str | None:
        """Map PennyMac product name to our standardized product key."""
        name_lower = name.lower()

        # ARM detection (any category)
        if 'arm' in name_lower or 'adjustable' in name_lower:
            return 'ARM'

        # Category-specific mapping
        if category == 'fha':
            if '30' in name_lower:
                return 'FHA_30yr'
            return 'FHA_30yr'  # default FHA to 30yr

        if category == 'va':
            if '30' in name_lower:
                return 'VA_30yr'
            return 'VA_30yr'  # default VA to 30yr

        # Conventional + Jumbo
        if '30' in name_lower:
            return '30yr'
        if '15' in name_lower:
            return '15yr'
        if '20' in name_lower:
            return '30yr'  # treat 20yr as 30yr bucket for now

        return None

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Override — no browser needed."""
        return self.fetch()
