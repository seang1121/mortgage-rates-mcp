"""Wells Fargo — Big 4 bank. Stealth browser, standard rate page.

Source: wellsfargo.com/mortgage/rates/
Anti-bot: Minimal
Products: 30yr, 15yr, ARM
"""
from backend.extractors.base import BaseLenderExtractor


class WellsFargoExtractor(BaseLenderExtractor):
    name = "Wells Fargo"
    url = "https://www.wellsfargo.com/mortgage/rates/"
    wait_ms = 10000
