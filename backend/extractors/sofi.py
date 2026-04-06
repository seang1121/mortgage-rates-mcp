"""SoFi — online lender. Competitive rates, tech-forward.

Source: sofi.com/home-loans/mortgage-rates/
Anti-bot: Minimal
Products: 30yr, 15yr, ARM
"""
from backend.extractors.base import BaseLenderExtractor


class SoFiExtractor(BaseLenderExtractor):
    name = "SoFi"
    url = "https://www.sofi.com/home-loans/mortgage-rates/"
    wait_ms = 10000
