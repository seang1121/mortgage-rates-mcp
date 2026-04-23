"""Stealth browser context factory — realistic fingerprints + human behavior.

Akamai Bot Manager scores sessions on:
  1. TLS fingerprint vs User-Agent correlation
  2. Mouse/scroll/focus behavioral signals
  3. Consistent fingerprint across requests from same IP
  4. Navigator/WebGL/Canvas consistency

Patchright already handles TLS + navigator patching. This module adds:
  - UA rotation matching the actual Chrome channel being used
  - Randomized viewport/timezone/locale
  - Human-like delays and mouse movement injection
  - Per-session fingerprint consistency
"""
import random
import asyncio

# Chrome versions that match patchright's bundled Chromium or system Chrome.
# Keep these within ~3 versions of the actual binary to avoid TLS/UA mismatch.
CHROME_VERSIONS = ["132.0.0.0", "133.0.0.0", "134.0.0.0"]

PLATFORMS = [
    {
        "ua_platform": "Macintosh; Intel Mac OS X 10_15_7",
        "platform": "macOS",
        "sec_ch_ua_platform": '"macOS"',
    },
    {
        "ua_platform": "Windows NT 10.0; Win64; x64",
        "platform": "Windows",
        "sec_ch_ua_platform": '"Windows"',
    },
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1366, "height": 768},
    {"width": 2560, "height": 1440},
]

TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
]


def build_context_options() -> dict:
    """Generate a realistic, internally-consistent browser context config."""
    chrome_ver = random.choice(CHROME_VERSIONS)
    plat = random.choice(PLATFORMS)
    viewport = random.choice(VIEWPORTS)
    tz = random.choice(TIMEZONES)

    ua = (
        f"Mozilla/5.0 ({plat['ua_platform']}) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{chrome_ver} Safari/537.36"
    )

    return {
        "viewport": viewport,
        "user_agent": ua,
        "locale": "en-US",
        "timezone_id": tz,
        "extra_http_headers": {
            "sec-ch-ua": f'"Chromium";v="{chrome_ver.split(".")[0]}", "Google Chrome";v="{chrome_ver.split(".")[0]}", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": plat["sec_ch_ua_platform"],
            "upgrade-insecure-requests": "1",
        },
    }


async def human_delay(min_ms: int = 500, max_ms: int = 2500):
    """Random delay that looks like human think time."""
    await asyncio.sleep(random.randint(min_ms, max_ms) / 1000)


async def simulate_human(page, duration_ms: int = 3000):
    """Inject mouse movements and scroll events that pass behavioral checks.

    Akamai collects mousemove, scroll, click, and focus events via its sensor
    script. A page that loads and extracts text without ANY of these events
    scores as automated. This generates enough noise to look organic.
    """
    steps = random.randint(3, 6)
    viewport = page.viewport_size or {"width": 1920, "height": 1080}

    for _ in range(steps):
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.1, 0.4))

    # Scroll down naturally
    scroll_amount = random.randint(200, 600)
    await page.mouse.wheel(0, scroll_amount)
    await asyncio.sleep(random.uniform(0.3, 0.8))

    # Scroll back up partially
    await page.mouse.wheel(0, -random.randint(50, scroll_amount // 2))
    await asyncio.sleep(random.uniform(0.2, 0.5))
