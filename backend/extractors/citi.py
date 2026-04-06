"""Citi — Big 4 bank. Stealth browser, standard rate page.

Source: citi.com/mortgage/purchase-rates
Anti-bot: Minimal
Products: 30yr, 15yr, ARM
"""
from backend.extractors.base import BaseLenderExtractor


class CitiExtractor(BaseLenderExtractor):
    name = "Citi"
    url = "https://www.citi.com/mortgage/purchase-rates"
    wait_ms = 10000
