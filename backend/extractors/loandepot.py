"""LoanDepot — online lender. Angular SPA with reCAPTCHA v3 protection.

Source: loandepot.com/mortgage-rates
Anti-bot: reCAPTCHA v3 (score-based, no checkbox)
Strategy: Patchright stealth browser should pass reCAPTCHA v3 score check
          since it mimics real browser behavior. The page is Angular + Scully
          (SSR with client-side hydration), so we need to wait for JS rendering.
Products: 30yr, 15yr, ARM, FHA, VA
"""
from backend.extractors.base import BaseLenderExtractor


class LoanDepotExtractor(BaseLenderExtractor):
    name = "LoanDepot"
    url = "https://www.loandepot.com/mortgage-rates"
    wait_ms = 15000  # Angular hydration + reCAPTCHA scoring needs time
