"""Bank of America — Big 4 bank. Stealth browser, promo URL serves rates on first load.

Source: promotions.bankofamerica.com (special promo URL bypasses multi-step navigation)
Anti-bot: None detected
Products: 30yr, 15yr, ARM
"""
from backend.extractors.base import BaseLenderExtractor


class BankOfAmericaExtractor(BaseLenderExtractor):
    name = "Bank of America"
    url = "https://promotions.bankofamerica.com/homeloans/homebuying-hub/home-loan-options?subCampCode=41490&dmcode=18099675931"
    wait_ms = 10000
