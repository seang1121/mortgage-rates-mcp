"""Lender extractor registry — 19 lenders + 2 benchmarks across 3 tiers."""
from backend.extractors.base import BaseLenderExtractor, RateResult

# Tier 1 — Direct API/JSON (no browser, instant, most reliable)
from backend.extractors.freddie_mac import FreddieMacExtractor
from backend.extractors.mnd import MNDExtractor
from backend.extractors.pennymac import PennyMacExtractor
from backend.extractors.citizens import CitizensExtractor
from backend.extractors.wells_fargo import WellsFargoExtractor

# Tier 2 — Stealth browser, low protection
from backend.extractors.bank_of_america import BankOfAmericaExtractor
from backend.extractors.citi import CitiExtractor
from backend.extractors.navy_federal import NavyFederalExtractor
from backend.extractors.sofi import SoFiExtractor
from backend.extractors.us_bank import USBankExtractor
from backend.extractors.guaranteed_rate import GuaranteedRateExtractor
from backend.extractors.truist import TruistExtractor
from backend.extractors.mr_cooper import MrCooperExtractor

# Tier 3 — Stealth browser, heavy anti-bot (Akamai, Cloudflare, reCAPTCHA)
from backend.extractors.chase import ChaseExtractor
from backend.extractors.rocket_mortgage import RocketMortgageExtractor
from backend.extractors.pnc import PNCExtractor
from backend.extractors.usaa import USAAExtractor
from backend.extractors.flagstar import FlagstarExtractor
# LoanDepot dropped — reCAPTCHA v3 blocks automation, no alternative source for live rates


TIER1_EXTRACTORS = [
    FreddieMacExtractor(),
    MNDExtractor(),
    PennyMacExtractor(),
    CitizensExtractor(),
    WellsFargoExtractor(),
    FlagstarExtractor(),      # via WalletHub JSON
    PNCExtractor(),           # via MortgageHog Next.js JSON API
    # USAA disabled — third-party sources return outdated review data, not current rates
    # Re-enable when we find a reliable data source or bypass Akamai TLS
]

TIER2_EXTRACTORS = [
    BankOfAmericaExtractor(),
    CitiExtractor(),
    NavyFederalExtractor(),
    SoFiExtractor(),
    USBankExtractor(),
    GuaranteedRateExtractor(),
    TruistExtractor(),
    MrCooperExtractor(),
]

TIER3_EXTRACTORS = [
    ChaseExtractor(),
    RocketMortgageExtractor(),
]

ALL_EXTRACTORS = TIER1_EXTRACTORS + TIER2_EXTRACTORS + TIER3_EXTRACTORS

# Convenience: total count for health checks and reporting
TOTAL_LENDER_COUNT = len([e for e in ALL_EXTRACTORS if not e.is_benchmark])
TOTAL_BENCHMARK_COUNT = len([e for e in ALL_EXTRACTORS if e.is_benchmark])

__all__ = [
    'BaseLenderExtractor', 'RateResult',
    'TIER1_EXTRACTORS', 'TIER2_EXTRACTORS', 'TIER3_EXTRACTORS',
    'ALL_EXTRACTORS', 'TOTAL_LENDER_COUNT', 'TOTAL_BENCHMARK_COUNT',
]
