"""Rocket Mortgage — #1 retail mortgage lender in the US. Akamai protection.

Source: rocketmortgage.com/mortgage-rates
Anti-bot: Akamai Bot Manager
Strategy: SSR page has rates in initial HTML. Patchright stealth should pass
          Akamai sensor validation. Extra wait time for JS hydration.
Products: 30yr, 15yr, ARM
"""
from backend.extractors.base import BaseLenderExtractor


class RocketMortgageExtractor(BaseLenderExtractor):
    name = "Rocket Mortgage"
    url = "https://www.rocketmortgage.com/mortgage-rates"
    wait_ms = 15000  # extra time for Akamai sensor + JS hydration
