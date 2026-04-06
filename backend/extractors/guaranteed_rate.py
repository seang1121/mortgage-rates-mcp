"""Guaranteed Rate — online lender. Clean rate display.

Source: rate.com/mortgage-rates
Anti-bot: Minimal
Products: 30yr, 15yr, ARM
"""
from backend.extractors.base import BaseLenderExtractor


class GuaranteedRateExtractor(BaseLenderExtractor):
    name = "Guaranteed Rate"
    url = "https://www.rate.com/mortgage-rates"
    wait_ms = 10000
