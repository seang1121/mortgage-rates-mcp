"""Wells Fargo — Big 4 bank. Direct JSON API, no browser needed.

Source: Wells Fargo internal rates API (homelending-tools/v1/rates/purchase)
Anti-bot: None on API — requires 4 custom headers (client ID + request metadata)
Products: 30yr, 15yr, ARM, VA_30yr
"""
import json
import ssl
import urllib.request
import uuid
from datetime import datetime, timezone

from backend.extractors.base import BaseLenderExtractor, RateResult


# Wells Fargo rates API base
_API_BASE = (
    "https://connect.secure.wellsfargo.com"
    "/xapi/product-service-research/homelending-tools/v1/rates"
)


class WellsFargoExtractor(BaseLenderExtractor):
    name = "Wells Fargo"
    url = "https://www.wellsfargo.com/mortgage/rates/"
    requires_browser = False

    def _build_headers(self) -> dict:
        """Build required headers for the Wells Fargo rates API."""
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://www.wellsfargo.com/mortgage/rates/",
            "Origin": "https://www.wellsfargo.com",
            "X-WF-CLIENT-ID": "WU",
            "X-REQUEST-ID": str(uuid.uuid4()),
            "X-CORRELATION-ID": str(uuid.uuid4()),
            "X-WF-REQUEST-DATE": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
        }

    def _map_product(self, product_name: str) -> str | None:
        """Map Wells Fargo product name to our standardized product key."""
        name = product_name.lower()

        if 'arm' in name or 'adjustable' in name:
            return 'ARM'
        if 'va' in name and '30' in name:
            return 'VA_30yr'
        if 'fha' in name and '30' in name:
            return 'FHA_30yr'
        if '15' in name and 'fixed' in name:
            return '15yr'
        if '30' in name and 'fixed' in name:
            return '30yr'

        return None

    def fetch(self) -> list[RateResult]:
        """Fetch rates directly from Wells Fargo's JSON API."""
        results = []
        ctx = ssl.create_default_context()
        seen_products: set[str] = set()

        for endpoint in ("purchase",):
            try:
                url = f"{_API_BASE}/{endpoint}"
                req = urllib.request.Request(url, headers=self._build_headers())
                with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                    body = json.loads(r.read().decode())

                if not body.get("meta", {}).get("success"):
                    print(f"[{self.name}] API returned success=false")
                    continue

                data = body.get("data", {})
                product_list = data.get("product_list", [])

                for item in product_list:
                    product = self._map_product(item.get("product_name", ""))
                    if not product or product in seen_products:
                        continue

                    rate = item.get("interest_rate")
                    apr = item.get("apr")
                    if rate is None:
                        continue

                    rate_val = float(rate)
                    apr_val = float(apr) if apr is not None else None

                    # Sanity check
                    if not (2.5 <= rate_val <= 14.0):
                        continue
                    if apr_val is not None and not (2.5 <= apr_val <= 16.0):
                        apr_val = None

                    results.append(RateResult(
                        lender=self.name,
                        product=product,
                        rate=rate_val,
                        apr=apr_val,
                    ))
                    seen_products.add(product)

            except Exception as e:
                print(f"[{self.name}] API fetch failed ({endpoint}): {e}")
                continue

        return results

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Override — no browser needed, uses direct API."""
        return self.fetch()
