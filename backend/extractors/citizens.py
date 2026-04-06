"""Citizens Bank — static JSON file with regionalized rates. No browser needed.

Source: citizensbank.com/assets/CB_resources/json/rates/Mortgage.json
Updated: Daily (timestamped in JSON response)
Products: Conforming Fixed (30yr, 15yr), ARM, Jumbo

Rates are regionalized by state code (RI, CT, OH, etc.).
The JSON file is a static asset — no auth, no JS rendering needed.
"""
import json
import ssl
import urllib.request

from backend.extractors.base import BaseLenderExtractor, RateResult


class CitizensExtractor(BaseLenderExtractor):
    name = "Citizens Bank"
    url = "https://www.citizensbank.com/assets/CB_resources/json/rates/Mortgage.json"
    requires_browser = False

    # Map Citizens product descriptions to our standard keys
    PRODUCT_MAP = {
        "30 year fixed rate": "30yr",
        "20 year fixed rate": "30yr",
        "15 year fixed rate": "15yr",
        "10 year fixed rate": "15yr",
    }

    def fetch(self, region: str = "RI") -> list[RateResult]:
        """Fetch rates from static JSON file.

        Args:
            region: State code for regionalized rates (e.g., 'RI', 'OH', 'CT').
                    Defaults to 'RI' (Rhode Island, Citizens HQ).
        """
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                data = json.loads(r.read().decode())

            results = []
            seen_products = set()

            for brand_entry in data:
                for region_data in brand_entry.get("BrandData", []):
                    if region_data.get("RegionCode") != region:
                        continue

                    groups_wrapper = region_data.get("RegionData", {}).get("GROUPS", [])
                    for group_set in groups_wrapper:
                        for group in group_set.get("GROUP", []):
                            group_name = group.get("NAME", "")

                            # Only grab Purchase rates (not Refinance)
                            if "Purchase" not in group_name:
                                continue

                            for product in group.get("PRODUCT", []):
                                # Citizens uses 'DESCR' (uppercase) for product description
                                descr = (product.get("DESCR") or product.get("Descr") or "").strip()
                                std_product = self._map_product(descr)
                                if not std_product or std_product in seen_products:
                                    continue

                                rate_str = (product.get("RATE") or "").replace("%", "").strip()
                                apr_str = (product.get("APR") or "").replace("%", "").strip()

                                try:
                                    rate_val = float(rate_str)
                                    apr_val = float(apr_str) if apr_str else None
                                    results.append(RateResult(
                                        lender=self.name,
                                        product=std_product,
                                        rate=rate_val,
                                        apr=apr_val,
                                    ))
                                    seen_products.add(std_product)
                                except (ValueError, TypeError):
                                    continue

            return results
        except Exception as e:
            print(f"[{self.name}] Fetch failed: {e}")
            return []

    def _map_product(self, descr: str) -> str | None:
        """Map Citizens product description to standard product key."""
        descr_lower = descr.lower()

        # Check explicit mappings
        for pattern, key in self.PRODUCT_MAP.items():
            if pattern in descr_lower:
                return key

        # ARM detection
        if 'arm' in descr_lower or 'adjustable' in descr_lower:
            return 'ARM'

        return None

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Override — no browser needed."""
        return self.fetch()
