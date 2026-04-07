"""LoanDepot — rates from product-specific Scully-rendered pages. No browser needed.

The main /mortgage-rates page is an Angular SPA behind reCAPTCHA v3.
But the product-specific pages (30yr, 15yr) are pre-rendered by Scully
with rates embedded in the static HTML — accessible via plain HTTP.

Source: loandepot.com/home-loans/fixed-rate-mortgage/*
Anti-bot: None on pre-rendered pages
Products: 30yr, 15yr (ARM/FHA/VA may require JS — scraped as fallback)
"""
import re
import ssl
import urllib.request

from backend.extractors.base import BaseLenderExtractor, RateResult


class LoanDepotExtractor(BaseLenderExtractor):
    name = "LoanDepot"
    url = "https://www.loandepot.com/mortgage-rates"
    requires_browser = False

    # Product-specific pages with Scully pre-rendered rate data
    PRODUCT_PAGES = {
        "30yr": "https://www.loandepot.com/home-loans/fixed-rate-mortgage/30yearmortgagerates",
        "15yr": "https://www.loandepot.com/home-loans/fixed-rate-mortgage/15yearmortgagerates",
    }

    # Rate patterns found in Scully pre-rendered HTML
    RATE_PATTERNS_LOANDEPOT = [
        # "30 years at 5.375% (APR 5.443%)"
        r'(\d+)\s*years?\s*at\s*(\d\.\d{2,3})%\s*\(?(?:APR\s*)?(\d\.\d{2,3})%',
        # "rate of 5.375% and an APR of 5.443%"
        r'rate\s*of\s*(\d\.\d{2,3})%.*?APR\s*of\s*(\d\.\d{2,3})%',
        # "5.375% interest rate / 5.443% APR"
        r'(\d\.\d{2,3})%\s*interest\s*rate\s*/\s*(\d\.\d{2,3})%\s*APR',
    ]

    def fetch(self) -> list[RateResult]:
        """Fetch rates from product-specific pre-rendered pages."""
        results = []
        ctx = ssl.create_default_context()

        for product, page_url in self.PRODUCT_PAGES.items():
            try:
                req = urllib.request.Request(page_url, headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/133.0.0.0 Safari/537.36"
                    )
                })
                with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                    html = r.read().decode("utf-8", errors="replace")

                # Strip HTML tags for text extraction
                text = re.sub(r'<[^>]+>', ' ', html)

                # Try LoanDepot-specific patterns first
                found = False
                for pattern in self.RATE_PATTERNS_LOANDEPOT:
                    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                    if m:
                        groups = m.groups()
                        if len(groups) == 3:
                            # Pattern with term: "30 years at X% (APR Y%)"
                            rate_val = float(groups[1])
                            apr_val = float(groups[2])
                        elif len(groups) == 2:
                            rate_val = float(groups[0])
                            apr_val = float(groups[1])
                        else:
                            continue

                        if 2.5 <= rate_val <= 14.0:
                            results.append(RateResult(
                                lender=self.name,
                                product=product,
                                rate=rate_val,
                                apr=apr_val if 2.5 <= apr_val <= 16.0 else None,
                            ))
                            found = True
                            break

                # Fallback: use base regex extraction
                if not found:
                    base_results = self.extract(text)
                    for r in base_results:
                        if r.product == product:
                            results.append(r)
                            break

            except Exception as e:
                print(f"[{self.name}] Failed to fetch {product}: {e}")
                continue

        return results

    async def scrape(self, browser, zip_code: str) -> list[RateResult]:
        """Override — no browser needed for pre-rendered pages."""
        return self.fetch()
