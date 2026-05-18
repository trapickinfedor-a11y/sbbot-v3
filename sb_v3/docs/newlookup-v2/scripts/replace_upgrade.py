#!/usr/bin/env python3
"""
Replace 'Upgrade' on universal-credit.com funnel. Retries many times.

Usage:
  python3 scripts/replace_upgrade.py

  REPLACE_WITH="MyBrand" python3 scripts/replace_upgrade.py   # один бренд
  REPLACE_WITH="A,B,C" python3 scripts/replace_upgrade.py     # перебор нескольких
  MAX_RETRIES=50 python3 scripts/replace_upgrade.py           # 50 попыток
  HEADLESS=1 python3 scripts/replace_upgrade.py               # без окна
"""
import asyncio
import os
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("pip install playwright && playwright install chromium")
    sys.exit(1)

URL = "https://www.universal-credit.com/funnel/personal-information-1/CREDIT_CARD/30000"
# REPLACE_WITH: что вставить вместо Upgrade. Можно несколько через запятую — переберёт все
REPLACEMENTS = [s.strip() for s in os.environ.get("REPLACE_WITH", "Universal Credit,MyCredit,QuickLoan").split(",")]
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "20"))


async def replace_on_page(page, replacement: str) -> bool:
    return await page.evaluate(
        """([r]) => {
            const walk = (n) => {
                if (n.nodeType === 3) n.textContent = n.textContent.replace(/Upgrade/g, r);
                else for (const c of n.childNodes) walk(c);
            };
            walk(document.body);
            return document.body.innerText.includes(r);
        }""",
        [replacement],
    )


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=os.environ.get("HEADLESS", "0") == "1")
        page = await browser.new_page()
        for attempt in range(MAX_RETRIES):
            repl = REPLACEMENTS[attempt % len(REPLACEMENTS)]
            try:
                await page.goto(URL, wait_until="domcontentloaded", timeout=12000)
                await page.wait_for_timeout(1500)
                ok = await replace_on_page(page, repl)
                print(f"✓ {attempt+1}/{MAX_RETRIES}: Upgrade → {repl}" if ok else f"✗ {attempt+1}: fail")
            except Exception as e:
                print(f"✗ {attempt+1}: {e}")
            if attempt < MAX_RETRIES - 1:
                await page.reload()
        await asyncio.sleep(5)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
