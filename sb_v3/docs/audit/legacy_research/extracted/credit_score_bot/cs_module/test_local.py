"""
test_local.py — Минимальный тест для локальной проверки.

Запускает ОДИН запрос без Telegram-бота и без 9proxy.
Используйте реальные данные человека, у которого есть кредитная история в США.

Запуск:
    cd cs_module
    python test_local.py

Что проверяет:
  1. Браузер запускается без краша (signal 6 fix)
  2. Форма на universal-credit.com заполняется
  3. PDF скачивается
  4. Кредитный скор извлекается из PDF
"""

import asyncio
import sys
import os
import logging
import time
import re
import random
import string
from pathlib import Path
from typing import Optional

# ─── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("test_local")

# ─── Playwright / Camoufox ──────────────────────────────────────────────────
try:
    from camoufox.async_api import AsyncCamoufox
except ImportError:
    print("ERROR: camoufox not installed. Run: pip install camoufox && camoufox install")
    sys.exit(1)

# ─── PDF extraction ─────────────────────────────────────────────────────────
try:
    import pdfminer
    from pdfminer.high_level import extract_text as pdf_extract_text
    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False
    logger.warning("pdfminer.six not installed — PDF text extraction will use fallback")

# ─── Config ─────────────────────────────────────────────────────────────────

# ╔══════════════════════════════════════════════════════════╗
# ║  ЗАПОЛНИТЕ ЭТИ ПОЛЯ ПЕРЕД ЗАПУСКОМ                      ║
# ╚══════════════════════════════════════════════════════════╝
TEST_PROFILE = {
    "first_name":    "Annette",
    "last_name":     "Solano",
    "street":        "10047 E S6",
    "city":          "Littlerock",
    "state":         "CA",
    "zip_code":      "93543",
    "dob":           "01/26/1991",
    "annual_income": "35000",
}

# Прокси: оставьте None чтобы работать без прокси
PROXY_URL = None
# PROXY_URL = "http://user-country-us-session-abc123:pass@gate.9proxy.com:7777"

# Папка для скриншотов и PDF
OUTPUT_DIR = Path("./test_output")

# ─── Helpers ────────────────────────────────────────────────────────────────

def random_email():
    prefix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{prefix}@gmail.com"


async def human_delay(min_ms=300, max_ms=1200):
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)


async def slow_type(page, selector, text):
    el = await page.query_selector(selector)
    if not el:
        raise RuntimeError(f"Element not found: {selector}")
    await el.click()
    await human_delay(200, 500)
    await el.triple_click()
    for char in text:
        await el.type(char, delay=0)
        await asyncio.sleep(random.uniform(50, 150) / 1000)
    await human_delay(100, 300)


# ─── Main test ──────────────────────────────────────────────────────────────

async def run_test():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    email = random_email()
    password = "TestPass#2025!"

    logger.info("=" * 60)
    logger.info("TEST: universal-credit.com form fill + PDF extraction")
    logger.info(f"Profile: {TEST_PROFILE['first_name']} {TEST_PROFILE['last_name']}")
    logger.info(f"Email: {email}")
    logger.info(f"Proxy: {PROXY_URL or 'None (direct)'}")
    logger.info("=" * 60)

    # ── Browser launch ───────────────────────────────────────────
    launch_kwargs = {
        "headless": True,
        "os": "windows",
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-gpu",                   # Fix for macOS crash
            "--disable-software-rasterizer",   # Fix for macOS crash
        ],
    }
    if PROXY_URL:
        launch_kwargs["proxy"] = {"server": PROXY_URL}

    logger.info("Launching browser...")
    t0 = time.time()

    async with AsyncCamoufox(**launch_kwargs) as browser:
        page = await browser.new_page()
        logger.info(f"Browser launched in {time.time() - t0:.1f}s")

        # ── Step 1: Navigate ─────────────────────────────────────
        url = (
            "https://www.universal-credit.com/funnel/"
            "personal-information-1/DEBT_CONSOLIDATION/5000?step=contact"
        )
        logger.info(f"Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await page.screenshot(path=str(OUTPUT_DIR / "01_page_loaded.png"))
        logger.info("Page loaded. Screenshot saved: 01_page_loaded.png")
        await human_delay(1000, 2000)

        # ── Step 1: Fill personal info ───────────────────────────
        logger.info("Filling Step 1: personal info...")
        await slow_type(page, "[name='borrowerFirstName']", TEST_PROFILE["first_name"])
        await slow_type(page, "[name='borrowerLastName']", TEST_PROFILE["last_name"])

        # Address geosuggest
        addr_field = await page.query_selector(
            "[name='borrowerStreet'], #geosuggest__input--borrowerStreet, [id*='geosuggest']"
        )
        if addr_field:
            await addr_field.click()
            await human_delay(300, 600)
            await addr_field.fill("")
            search = f"{TEST_PROFILE['street']} {TEST_PROFILE['zip_code']}"
            for char in search:
                await addr_field.type(char, delay=0)
                await asyncio.sleep(random.uniform(50, 150) / 1000)
            await asyncio.sleep(2)
            suggestions = await page.query_selector_all(
                ".geosuggest__suggests li, [class*='suggest'] li"
            )
            if suggestions:
                await suggestions[0].click()
                logger.info(f"Address suggestion selected ({len(suggestions)} found)")
            else:
                logger.warning("No address suggestions found")
            await human_delay(500, 1000)

        # DOB
        dob_field = await page.query_selector("[name='borrowerDateOfBirth']")
        if dob_field:
            await slow_type(page, "[name='borrowerDateOfBirth']", TEST_PROFILE["dob"])

        await page.screenshot(path=str(OUTPUT_DIR / "02_step1_filled.png"))
        logger.info("Step 1 filled. Screenshot: 02_step1_filled.png")

        # Continue
        btn = await page.query_selector("button:has-text('Continue'), button[type='submit']")
        if btn:
            await btn.click()
        await human_delay(1000, 2000)

        # ── Step 2: Income ───────────────────────────────────────
        logger.info("Filling Step 2: income...")
        await asyncio.sleep(2)
        income_field = await page.query_selector("[name='borrowerIncome']")
        if income_field:
            await slow_type(page, "[name='borrowerIncome']", TEST_PROFILE["annual_income"])
        await page.screenshot(path=str(OUTPUT_DIR / "03_step2_filled.png"))
        logger.info("Step 2 filled. Screenshot: 03_step2_filled.png")

        btn = await page.query_selector("button:has-text('Continue'), button[type='submit']")
        if btn:
            await btn.click()
        await human_delay(1000, 2000)

        # ── Step 3: Create account ───────────────────────────────
        logger.info("Filling Step 3: account creation...")
        await asyncio.sleep(2)
        email_field = await page.query_selector(
            "[name='username'], [name='email'], [type='email']"
        )
        if email_field:
            await slow_type(page, "[name='username'], [name='email'], [type='email']", email)
        pass_field = await page.query_selector("[name='password'], [type='password']")
        if pass_field:
            await slow_type(page, "[name='password'], [type='password']", password)

        checkbox = await page.query_selector("[name='agreements'], [type='checkbox']")
        if checkbox:
            checked = await checkbox.is_checked()
            if not checked:
                await checkbox.click()

        await page.screenshot(path=str(OUTPUT_DIR / "04_step3_filled.png"))
        logger.info("Step 3 filled. Screenshot: 04_step3_filled.png")

        # Submit
        submit_btn = await page.query_selector(
            "button:has-text('Check Your Rate'), button[type='submit']"
        )
        if submit_btn:
            await submit_btn.click()
        logger.info("Form submitted. Waiting for result page...")

        # ── Wait for result ──────────────────────────────────────
        deadline = time.time() + 120
        result_url = None
        while time.time() < deadline:
            url = page.url
            if "adverse-page" in url or "offer-page" in url:
                result_url = url
                break
            await asyncio.sleep(1)

        await page.screenshot(path=str(OUTPUT_DIR / "05_result_page.png"))

        if not result_url:
            logger.error(f"Form did not reach result page. Current URL: {page.url}")
            logger.error("Screenshot saved: 05_result_page.png")
            return

        logger.info(f"Result page reached: {result_url}")

        # ── Navigate to Documents ────────────────────────────────
        logger.info("Navigating to Documents portal...")
        await page.goto(
            "https://www.universal-credit.com/portal/profile/documents",
            wait_until="domcontentloaded",
            timeout=30_000,
        )

        # Wait up to 45s for Adverse Action Notice
        logger.info("Waiting for Adverse Action Notice (up to 45s)...")
        found = False
        for i in range(45):
            await asyncio.sleep(1)
            has_adverse = await page.evaluate(
                "() => Array.from(document.querySelectorAll('*')).some("
                "el => el.textContent && el.textContent.toLowerCase().includes('adverse action'))"
            )
            if has_adverse:
                found = True
                logger.info(f"Adverse Action Notice appeared after {i+1}s")
                break

        await page.screenshot(path=str(OUTPUT_DIR / "06_documents_page.png"))

        if not found:
            logger.error("Adverse Action Notice NOT found in Documents portal")
            logger.error("Screenshot: 06_documents_page.png")
            return

        # ── Download PDF ─────────────────────────────────────────
        logger.info("Intercepting PDF download...")
        pdf_bytes_holder = []

        async def capture_response(response):
            ct = response.headers.get("content-type", "")
            if "pdf" in ct or response.url.endswith(".pdf"):
                try:
                    body = await response.body()
                    if body and body[:4] == b"%PDF":
                        pdf_bytes_holder.append(body)
                        logger.info(f"PDF captured: {len(body)} bytes from {response.url}")
                except Exception as e:
                    logger.warning(f"Failed to capture PDF body: {e}")

        page.on("response", capture_response)

        # Find and click download button
        dl_btn = await page.evaluate_handle("""
            () => {
                const rows = Array.from(document.querySelectorAll('li, tr, [class*="row"], [class*="item"]'));
                for (const row of rows) {
                    if (row.textContent.toLowerCase().includes('adverse action')) {
                        const btn = row.querySelector('a[href], button, [class*="download"]');
                        if (btn) return btn;
                    }
                }
                return null;
            }
        """)

        el = dl_btn.as_element() if dl_btn else None
        if el:
            await el.click()
            logger.info("Download button clicked")
            await asyncio.sleep(8)
        else:
            logger.warning("Download button not found — trying to find any link near 'adverse action'")

        page.remove_listener("response", capture_response)

        if not pdf_bytes_holder:
            logger.error("PDF was NOT downloaded")
            return

        # ── Save PDF ─────────────────────────────────────────────
        pdf_path = OUTPUT_DIR / "adverse_action.pdf"
        pdf_path.write_bytes(pdf_bytes_holder[0])
        logger.info(f"PDF saved: {pdf_path} ({len(pdf_bytes_holder[0])} bytes)")

        # ── Extract score ─────────────────────────────────────────
        score = extract_score(pdf_bytes_holder[0])
        if score:
            logger.info("=" * 60)
            logger.info(f"✅ CREDIT SCORE: {score}")
            logger.info("=" * 60)
        else:
            logger.error("Could not extract credit score from PDF")
            logger.error("Check the PDF manually: test_output/adverse_action.pdf")


def extract_score(pdf_data: bytes) -> Optional[int]:
    """Extract credit score from PDF bytes."""
    text = ""
    if HAS_PDFMINER:
        try:
            import io
            text = pdf_extract_text(io.BytesIO(pdf_data))
        except Exception as e:
            logger.warning(f"pdfminer failed: {e}")

    if not text:
        text = pdf_data.decode("latin-1", errors="replace")

    patterns = [
        r"(?:credit\s+score|fico\s+score|score\s+value)[^\d]*(\d{3})",
        r"(?:your\s+score\s+is)[^\d]*(\d{3})",
        r"\b([5-8]\d{2})\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            score = int(m.group(1))
            if 300 <= score <= 850:
                return score
    return None


if __name__ == "__main__":
    asyncio.run(run_test())
