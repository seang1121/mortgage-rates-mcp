"""Freddie Mac PMMS — national benchmark via free CSV endpoint. No browser needed.

Source: freddiemac.com/pmms (Primary Mortgage Market Survey)
Updated: Weekly on Thursdays
Products: 30yr fixed, 15yr fixed
"""
import ssl
import urllib.request

from backend.extractors.base import BaseLenderExtractor, RateResult


class FreddieMacExtractor(BaseLenderExtractor):
    name = "Freddie Mac (natl avg)"
    url = "https://www.freddiemac.com/pmms/docs/PMMS_history.csv"
    is_benchmark = True
    requires_browser = False

    def fetch(self) -> list[RateResult]:
        """Fetch national average rates via CSV download."""
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                lines = r.read().decode().strip().split("\n")

            # Last row = most recent week's data
            # CSV columns: date, 30yr_rate, 30yr_fees_points, 15yr_rate, 15yr_fees_points, ...
            last = lines[-1].split(",")
            results = []

            if len(last) >= 2 and last[1].strip():
                results.append(RateResult(
                    lender=self.name, product="30yr",
                    rate=float(last[1].strip()), apr=None, is_benchmark=True
                ))

            if len(last) >= 4 and last[3].strip():
                results.append(RateResult(
                    lender=self.name, product="15yr",
                    rate=float(last[3].strip()), apr=None, is_benchmark=True
                ))

            return results
        except Exception as e:
            print(f"[{self.name}] Fetch failed: {e}")
            return []

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Override — no browser needed."""
        return self.fetch()
