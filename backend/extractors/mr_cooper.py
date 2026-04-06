"""Mr. Cooper — largest mortgage servicer in US. Async rate table rendering.

Source: mrcooper.com/get-started/rates
Anti-bot: Minimal
Products: 30yr, 15yr, ARM
Note: Uses "Rate ... X.XXX% ... APR ... X.XXX%" format (handled by base regex Pattern 4)
"""
from backend.extractors.base import BaseLenderExtractor


class MrCooperExtractor(BaseLenderExtractor):
    name = "Mr. Cooper"
    url = "https://www.mrcooper.com/get-started/rates?internal_ref=rates_home"
    wait_ms = 12000  # extra time for async rate table rendering
