"""
fingerprint/rotator.py — Browser fingerprint rotator.

Each request gets a fresh, randomized browser profile to defeat
ThreatMetrix device fingerprinting. We use camoufox which already
randomizes most fingerprint parameters. This module adds an extra
layer of randomization on top.

Key fingerprint parameters rotated per request:
  - User-Agent (OS, browser version)
  - Screen resolution
  - Timezone
  - Language / Accept-Language
  - WebGL vendor/renderer strings (via camoufox config)
  - Canvas noise seed
  - Audio context noise seed
  - Hardware concurrency (CPU cores)
  - Device memory
  - Platform string
"""

import random
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data pools for randomization
# ---------------------------------------------------------------------------

_SCREEN_RESOLUTIONS = [
    (1366, 768), (1920, 1080), (1440, 900), (1536, 864),
    (1280, 800), (1600, 900), (1280, 1024), (1024, 768),
    (1680, 1050), (1920, 1200), (2560, 1440), (1360, 768),
]

_TIMEZONES = [
    "America/New_York", "America/Chicago", "America/Denver",
    "America/Los_Angeles", "America/Phoenix", "America/Detroit",
    "America/Indiana/Indianapolis", "America/Boise",
    "America/Anchorage", "Pacific/Honolulu",
]

_LANGUAGES = [
    ["en-US", "en"],
    ["en-US", "en", "es"],
    ["en-US", "en-GB", "en"],
    ["en-US"],
]

_PLATFORMS = ["Win32", "Win32", "Win32", "MacIntel", "Linux x86_64"]

_CPU_CORES = [2, 4, 4, 4, 6, 8, 8, 12, 16]

_DEVICE_MEMORY = [2, 4, 4, 8, 8, 16]

_WEBGL_VENDORS = [
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Intel Inc.", "Intel Iris OpenGL Engine"),
    ("Apple Inc.", "Apple GPU"),
]

# Firefox versions for User-Agent construction
_FF_VERSIONS = ["115.0", "116.0", "117.0", "118.0", "119.0", "120.0", "121.0", "122.0", "123.0"]

_WIN_VERSIONS = [
    "Windows NT 10.0; Win64; x64",
    "Windows NT 10.0; WOW64",
    "Windows NT 6.1; Win64; x64",
]

_MAC_VERSIONS = [
    "Macintosh; Intel Mac OS X 10.15",
    "Macintosh; Intel Mac OS X 11.0",
    "Macintosh; Intel Mac OS X 12.0",
    "Macintosh; Intel Mac OS X 13.0",
]


# ---------------------------------------------------------------------------
# Fingerprint profile dataclass
# ---------------------------------------------------------------------------

@dataclass
class FingerprintProfile:
    user_agent: str
    screen_width: int
    screen_height: int
    timezone: str
    languages: list[str]
    platform: str
    hardware_concurrency: int
    device_memory: int
    webgl_vendor: str
    webgl_renderer: str
    canvas_noise_seed: int
    audio_noise_seed: int
    do_not_track: Optional[str]

    def to_camoufox_config(self) -> dict:
        """
        Convert to camoufox AsyncCamoufox kwargs.
        camoufox accepts: screen, os, locale, timezone, etc.
        """
        # Determine OS from user agent
        if "Windows" in self.user_agent:
            os_type = "windows"
        elif "Macintosh" in self.user_agent:
            os_type = "macos"
        else:
            os_type = "linux"

        return {
            "os": os_type,
            "screen": {"width": self.screen_width, "height": self.screen_height},
            "locale": self.languages[0] if self.languages else "en-US",
            "timezone": self.timezone,
            "fonts": [],  # Use system fonts
            "gfx_features": {
                "webgl_vendor": self.webgl_vendor,
                "webgl_renderer": self.webgl_renderer,
            },
        }

    def to_playwright_context_options(self) -> dict:
        """
        Extra options to pass to browser.new_context() in Playwright.
        """
        return {
            "user_agent": self.user_agent,
            "viewport": {"width": self.screen_width, "height": self.screen_height},
            "locale": self.languages[0] if self.languages else "en-US",
            "timezone_id": self.timezone,
            "extra_http_headers": {
                "Accept-Language": ",".join(self.languages) + ";q=0.9",
                "DNT": self.do_not_track or "1",
            },
        }


# ---------------------------------------------------------------------------
# Rotator
# ---------------------------------------------------------------------------

class FingerprintRotator:
    """
    Generates a fresh, randomized FingerprintProfile for each request.
    Call .generate() to get a new profile.
    """

    def generate(self) -> FingerprintProfile:
        screen = random.choice(_SCREEN_RESOLUTIONS)
        tz = random.choice(_TIMEZONES)
        langs = random.choice(_LANGUAGES)
        platform = random.choice(_PLATFORMS)
        cores = random.choice(_CPU_CORES)
        mem = random.choice(_DEVICE_MEMORY)
        webgl = random.choice(_WEBGL_VENDORS)
        ff_ver = random.choice(_FF_VERSIONS)

        # Build User-Agent based on platform
        if platform == "MacIntel":
            os_str = random.choice(_MAC_VERSIONS)
        elif platform == "Linux x86_64":
            os_str = "X11; Linux x86_64"
        else:
            os_str = random.choice(_WIN_VERSIONS)

        user_agent = f"Mozilla/5.0 ({os_str}; rv:{ff_ver}) Gecko/20100101 Firefox/{ff_ver}"

        return FingerprintProfile(
            user_agent=user_agent,
            screen_width=screen[0],
            screen_height=screen[1],
            timezone=tz,
            languages=langs,
            platform=platform,
            hardware_concurrency=cores,
            device_memory=mem,
            webgl_vendor=webgl[0],
            webgl_renderer=webgl[1],
            canvas_noise_seed=random.randint(1, 999999),
            audio_noise_seed=random.randint(1, 999999),
            do_not_track=random.choice(["1", None, None]),  # mostly no DNT
        )


# Module-level singleton
rotator = FingerprintRotator()
