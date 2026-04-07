"""Flagstar Bank (NYCB) — rates via WalletHub proxy. No browser needed.

Flagstar's own site is behind heavy Cloudflare Turnstile that blocks automation.
WalletHub publishes Flagstar's rates with embedded JSON — no anti-bot protection.

Source: wallethub.com/mortgage-rates/flagstar-bank-13003351i
Anti-bot: None on WalletHub
Products: 30yr, 15yr, FHA, ARM (varies)
"""
import json
import re
import ssl
import urllib.request

from backend.extractors.base import BaseLenderExtractor, RateResult


class FlagstarExtractor(BaseLenderExtractor):
    name = "Flagstar"
    url = "https://wallethub.com/mortgage-rates/flagstar-bank-13003351i"
    requires_browser = False

    PRODUCT_MAP = {
        "30 year fixed": "30yr",
        "30-year fixed": "30yr",
        "15 year fixed": "15yr",
        "15-year fixed": "15yr",
        "30 year fha": "FHA_30yr",
        "30-year fha": "FHA_30yr",
        "fha 30": "FHA_30yr",
        "30 year va": "VA_30yr",
        "30-year va": "VA_30yr",
    }

    def fetch(self) -> list[RateResult]:
        """Fetch Flagstar rates from WalletHub's embedded JSON."""
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/133.0.0.0 Safari/537.36"
                )
            })
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                html = r.read().decode("utf-8", errors="replace")

            results = []
            seen = set()

            # Try to find JSON data blocks with rate info
            # WalletHub embeds rate data in JSON-LD or inline script blocks
            for pattern in [
                r'"rate"\s*:\s*(\d+\.?\d*)\s*,\s*"aprEffective"\s*:\s*(\d+\.?\d*)\s*,.*?"product[Nn]ame"\s*:\s*"([^"]+)"',
                r'"product[Nn]ame"\s*:\s*"([^"]+)".*?"rate"\s*:\s*(\d+\.?\d*)\s*,\s*"aprEffective"\s*:\s*(\d+\.?\d*)',
            ]:
                for m in re.finditer(pattern, html, re.DOTALL):
                    groups = m.groups()
                    if len(groups) == 3:
                        # Determine which group is which based on pattern order
                        if groups[0].replace('.', '').isdigit():
                            rate_val, apr_val, product_name = float(groups[0]), float(groups[1]), groups[2]
                        else:
                            product_name, rate_val, apr_val = groups[0], float(groups[1]), float(groups[2])

                        product = self._map_product(product_name)
                        if product and product not in seen:
                            if 2.5 <= rate_val <= 14.0:
                                results.append(RateResult(
                                    lender=self.name,
                                    product=product,
                                    rate=rate_val,
                                    apr=apr_val if 2.5 <= apr_val <= 16.0 else None,
                                ))
                                seen.add(product)

            # Fallback: try regex extraction on stripped text
            if not results:
                text = re.sub(r'<[^>]+>', ' ', html)
                results = self.extract(text)

            return results
        except Exception as e:
            print(f"[{self.name}] WalletHub fetch failed: {e}")
            return []

    def _map_product(self, name: str) -> str | None:
        name_lower = name.lower().strip()
        for pattern, key in self.PRODUCT_MAP.items():
            if pattern in name_lower:
                return key
        if 'arm' in name_lower or 'adjustable' in name_lower:
            return 'ARM'
        return None

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Override — no browser needed."""
        return self.fetch()
