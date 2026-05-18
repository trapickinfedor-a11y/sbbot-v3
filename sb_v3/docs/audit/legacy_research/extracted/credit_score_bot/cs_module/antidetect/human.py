"""
antidetect/human.py — Human-like browser behavior simulation.

ThreatMetrix and similar systems analyze:
  - Typing speed and rhythm
  - Mouse movement patterns
  - Time between interactions
  - Scroll behavior
  - Focus/blur events

This module provides async helpers that mimic realistic human behavior
to minimize detection probability.
"""

import asyncio
import random
import math
from typing import Optional


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------

async def human_delay(min_ms: float = 300, max_ms: float = 1200):
    """Random delay simulating human reaction time."""
    delay = random.uniform(min_ms, max_ms) / 1000
    await asyncio.sleep(delay)


async def typing_delay(char: str):
    """
    Per-character typing delay.
    Spaces and punctuation are slightly slower (shift key, etc.).
    """
    if char in " \t\n":
        base = random.uniform(80, 200)
    elif char in "!@#$%^&*()_+-=[]{}|;':\",./<>?":
        base = random.uniform(100, 250)
    else:
        base = random.uniform(50, 180)

    # Occasional "thinking pause" (1 in 15 chars)
    if random.random() < 0.07:
        base += random.uniform(300, 800)

    await asyncio.sleep(base / 1000)


async def human_type(page, selector: str, text: str, clear_first: bool = True):
    """
    Type text into a field with realistic per-character delays.
    Simulates natural typing rhythm including occasional mistakes and corrections.
    """
    el = await page.query_selector(selector)
    if el is None:
        raise ValueError(f"Element not found: {selector}")

    await el.click()
    await human_delay(200, 500)

    if clear_first:
        await el.triple_click()
        await asyncio.sleep(0.1)

    for char in text:
        await el.type(char, delay=0)
        await typing_delay(char)

    # Small pause after finishing the field
    await human_delay(100, 400)


async def human_type_by_name(page, name: str, text: str, clear_first: bool = True):
    """Type into a field identified by name attribute."""
    await human_type(page, f"[name='{name}']", text, clear_first)


# ---------------------------------------------------------------------------
# Mouse movement helpers
# ---------------------------------------------------------------------------

async def bezier_mouse_move(page, x1: float, y1: float, x2: float, y2: float, steps: int = 20):
    """
    Move mouse from (x1,y1) to (x2,y2) along a Bezier curve.
    This looks much more natural than a straight line.
    """
    # Random control points for the Bezier curve
    cx1 = x1 + random.uniform(-100, 100)
    cy1 = y1 + random.uniform(-50, 50)
    cx2 = x2 + random.uniform(-100, 100)
    cy2 = y2 + random.uniform(-50, 50)

    for i in range(steps + 1):
        t = i / steps
        # Cubic Bezier formula
        bx = (1-t)**3 * x1 + 3*(1-t)**2*t * cx1 + 3*(1-t)*t**2 * cx2 + t**3 * x2
        by = (1-t)**3 * y1 + 3*(1-t)**2*t * cy1 + 3*(1-t)*t**2 * cy2 + t**3 * y2

        # Add tiny jitter
        bx += random.uniform(-1, 1)
        by += random.uniform(-1, 1)

        await page.mouse.move(bx, by)
        await asyncio.sleep(random.uniform(0.005, 0.025))


async def human_click(page, selector: str, move_first: bool = True):
    """
    Click an element with realistic mouse movement.
    """
    el = await page.query_selector(selector)
    if el is None:
        raise ValueError(f"Element not found: {selector}")

    box = await el.bounding_box()
    if box is None:
        await el.click()
        return

    # Target: slightly randomized within the element bounds
    target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
    target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

    if move_first:
        # Start from a random position on screen
        start_x = random.uniform(100, 800)
        start_y = random.uniform(100, 600)
        await bezier_mouse_move(page, start_x, start_y, target_x, target_y)

    await human_delay(50, 200)
    await page.mouse.click(target_x, target_y)
    await human_delay(100, 300)


# ---------------------------------------------------------------------------
# Scroll helpers
# ---------------------------------------------------------------------------

async def human_scroll(page, direction: str = "down", amount: Optional[int] = None):
    """
    Scroll the page in a human-like manner (variable speed, small increments).
    """
    if amount is None:
        amount = random.randint(200, 600)

    sign = 1 if direction == "down" else -1
    steps = random.randint(3, 8)
    per_step = (amount * sign) / steps

    for _ in range(steps):
        await page.mouse.wheel(0, per_step + random.uniform(-20, 20))
        await asyncio.sleep(random.uniform(0.05, 0.15))


# ---------------------------------------------------------------------------
# Page interaction warm-up
# ---------------------------------------------------------------------------

async def warm_up_page(page):
    """
    Perform a brief "warm-up" after page load:
    small scroll, random mouse movement, slight pause.
    This makes the session look more human to ThreatMetrix.
    """
    await human_delay(800, 2000)

    # Random mouse movement across the page
    for _ in range(random.randint(2, 5)):
        x = random.uniform(100, 1200)
        y = random.uniform(100, 700)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.4))

    # Slight scroll down then back
    await human_scroll(page, "down", random.randint(50, 150))
    await asyncio.sleep(random.uniform(0.3, 0.8))
    await human_scroll(page, "up", random.randint(30, 100))
    await human_delay(500, 1500)


# ---------------------------------------------------------------------------
# ThreatMetrix fingerprint injection
# ---------------------------------------------------------------------------

async def inject_threatmetrix_noise(page):
    """
    Inject JavaScript to add noise to fingerprint-sensitive APIs
    that ThreatMetrix probes. Must be called before page navigation
    via page.add_init_script().
    """
    script = """
    (() => {
        // Canvas noise
        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {
            const ctx = this.getContext('2d');
            if (ctx) {
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    data[i]     = data[i]     ^ (Math.floor(Math.random() * 3));
                    data[i + 1] = data[i + 1] ^ (Math.floor(Math.random() * 3));
                    data[i + 2] = data[i + 2] ^ (Math.floor(Math.random() * 3));
                }
                ctx.putImageData(imageData, 0, 0);
            }
            return origToDataURL.apply(this, args);
        };

        // AudioContext noise
        const origGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function(channel) {
            const data = origGetChannelData.call(this, channel);
            for (let i = 0; i < data.length; i += 100) {
                data[i] += Math.random() * 0.0001 - 0.00005;
            }
            return data;
        };

        // WebGL noise — randomize readPixels slightly
        const origReadPixels = WebGLRenderingContext.prototype.readPixels;
        WebGLRenderingContext.prototype.readPixels = function(...args) {
            origReadPixels.apply(this, args);
            if (args[6]) {
                const pixels = args[6];
                for (let i = 0; i < pixels.length; i += 4) {
                    pixels[i] ^= Math.floor(Math.random() * 2);
                }
            }
        };

        // Battery API — return fake data
        if (navigator.getBattery) {
            navigator.getBattery = () => Promise.resolve({
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 0.85 + Math.random() * 0.1,
                addEventListener: () => {},
                removeEventListener: () => {},
            });
        }

        // Permissions — always return 'prompt' to avoid fingerprinting
        if (navigator.permissions) {
            const origQuery = navigator.permissions.query.bind(navigator.permissions);
            navigator.permissions.query = (params) => {
                if (['notifications', 'push', 'midi', 'camera', 'microphone'].includes(params.name)) {
                    return Promise.resolve({ state: 'prompt', onchange: null });
                }
                return origQuery(params);
            };
        }
    })();
    """
    await page.add_init_script(script)
