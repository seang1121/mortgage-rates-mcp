"""Truist — national bank (BB&T + SunTrust merger). Standard rate page.

Source: truist.com/mortgage/current-mortgage-rates
Anti-bot: Minimal
Products: 30yr, 15yr, ARM
"""
from backend.extractors.base import BaseLenderExtractor


class TruistExtractor(BaseLenderExtractor):
    name = "Truist"
    url = "https://www.truist.com/mortgage/current-mortgage-rates"
    wait_ms = 10000
