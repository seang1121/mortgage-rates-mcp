"""Navy Federal Credit Union — largest credit union. Great for VA/military rates.

Source: navyfederal.org/loans-cards/mortgage/mortgage-rates/
Anti-bot: Minimal
Products: 30yr, 15yr, ARM, VA
"""
from backend.extractors.base import BaseLenderExtractor


class NavyFederalExtractor(BaseLenderExtractor):
    name = "Navy Federal CU"
    url = "https://www.navyfederal.org/loans-cards/mortgage/mortgage-rates/"
    wait_ms = 10000
