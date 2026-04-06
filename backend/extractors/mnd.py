"""Mortgage News Daily — real-time national rate index via HTML. No browser needed.

Source: mortgagenewsdaily.com/mortgage-rates
Updated: Multiple times daily
Products: 30yr, 15yr, ARM (varies)
"""
import re
import ssl
import urllib.request

from backend.extractors.base import BaseLenderExtractor, RateResult


class MNDExtractor(BaseLenderExtractor):
    name = "MND Index"
    url = "https://www.mortgagenewsdaily.com/mortgage-rates"
    is_benchmark = True
    requires_browser = False

    def fetch(self) -> list[RateResult]:
        """Fetch rates via plain HTTP + HTML text extraction."""
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                html = r.read().decode("utf-8", errors="replace")

            # Strip HTML tags, keep text content
            text = re.sub(r'<[^>]+>', ' ', html)
            return self.extract(text)
        except Exception as e:
            print(f"[{self.name}] Fetch failed: {e}")
            return []

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Override — no browser needed."""
        return self.fetch()
