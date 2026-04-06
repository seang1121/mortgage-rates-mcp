"""US Bank — national bank. Standard rate page.

Source: usbank.com/home-loans/mortgage/mortgage-rates.html
Anti-bot: Minimal
Products: 30yr, 15yr, ARM
"""
from backend.extractors.base import BaseLenderExtractor


class USBankExtractor(BaseLenderExtractor):
    name = "US Bank"
    url = "https://www.usbank.com/home-loans/mortgage/mortgage-rates.html"
    wait_ms = 10000
