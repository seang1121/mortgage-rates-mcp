"""USAA — military credit union. Heavy Akamai Bot Manager protection.

Source: usaa.com/bank/mortgage-rates
Anti-bot: Akamai Bot Manager (heavy — redirects with ?akredirect=true)
Strategy: Patchright stealth with extended wait for Akamai sensor validation.
          This is one of the hardest lenders to scrape. May need proxy rotation.
Products: 30yr, 15yr, ARM, VA
"""
from backend.extractors.base import BaseLenderExtractor


class USAAExtractor(BaseLenderExtractor):
    name = "USAA"
    url = "https://www.usaa.com/bank/mortgage-rates"
    wait_ms = 20000  # heavy Akamai — needs extra time for sensor validation
