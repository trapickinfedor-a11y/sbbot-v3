#!/usr/bin/env python3
"""
Universal Credit funnel parser.
Autofills form, goes to rejection -> Adverse Action Notice -> extracts Credit Score.

Fields (Step 1 - Contact):
  first_name, last_name, address, city, state, zip_code, dob
Optional (auto-generated if missing): phone, email, income

Usage:
  python3 scripts/universal_credit_parser.py
  python3 scripts/universal_credit_parser.py --input '{"first_name":"John","last_name":"Doe","address":"123 Main St","city":"NYC","state":"NY","zip_code":"10001","dob":"01/15/1990"}'
  python3 scripts/universal_credit_parser.py -v   # verbose, show raw text
"""
import asyncio
import json
import os
import random
import re
import string
import sys
from typing import Optional

try:
    from playwright.async_api import async_playwright, Page
except ImportError:
    print("pip install playwright && playwright install chromium")
    sys.exit(1)

URL_BASE = "https://www.universal-credit.com/funnel/personal-information-1/CREDIT_CARD/30000"
URL_DOCUMENTS = "https://www.universal-credit.com/portal/product/386786410/documents"

# Реальные US area codes
AREA_CODES = [
    205, 251, 256, 334, 938,  # Alabama
    480, 520, 602, 623, 928,  # Arizona
    209, 213, 310, 323, 408, 415, 424, 442, 510, 530, 559, 562, 619, 626, 628, 657, 661, 669, 707, 714, 747, 760, 805, 818, 831, 858, 909, 916, 925, 949, 951,  # California
    303, 719, 720, 970,  # Colorado
    203, 475, 860, 959,  # Connecticut
    302,  # Delaware
    202,  # DC
    239, 305, 321, 352, 386, 407, 561, 727, 754, 772, 786, 813, 850, 863, 904, 941, 954,  # Florida
    229, 404, 470, 478, 678, 706, 762, 770, 912,  # Georgia
    808,  # Hawaii
    208, 986,  # Idaho
    217, 224, 309, 312, 331, 618, 630, 708, 773, 815, 847, 872,  # Illinois
    219, 260, 317, 574, 765, 812,  # Indiana
    319, 515, 563, 641, 712,  # Iowa
    316, 620, 785, 913,  # Kansas
    270, 364, 502, 606, 859,  # Kentucky
    225, 318, 337, 504, 985,  # Louisiana
    207,  # Maine
    240, 301, 410, 443, 667,  # Maryland
    339, 351, 413, 508, 617, 774, 781, 857, 978,  # Massachusetts
    231, 248, 269, 313, 517, 586, 616, 734, 810, 906, 947, 989,  # Michigan
    218, 320, 507, 612, 651, 763, 952,  # Minnesota
    228, 601, 662, 769,  # Mississippi
    314, 417, 573, 636, 660, 816,  # Missouri
    406,  # Montana
    308, 402, 531,  # Nebraska
    702, 725, 775,  # Nevada
    603,  # New Hampshire
    201, 551, 609, 640, 732, 848, 856, 862, 908, 973,  # New Jersey
    505, 575,  # New Mexico
    212, 315, 332, 347, 516, 518, 585, 607, 631, 646, 680, 716, 718, 838, 845, 914, 917, 929,  # New York
    252, 336, 704, 828, 910, 919, 980, 984,  # North Carolina
    701,  # North Dakota
    216, 220, 234, 326, 330, 380, 419, 440, 513, 567, 614, 740, 937,  # Ohio
    405, 539, 580, 918,  # Oklahoma
    458, 503, 541, 971,  # Oregon
    215, 267, 272, 412, 445, 484, 610, 717, 724, 814, 878,  # Pennsylvania
    401,  # Rhode Island
    803, 839, 843, 854, 864,  # South Carolina
    605,  # South Dakota
    423, 615, 629, 731, 865, 901, 931,  # Tennessee
    210, 214, 254, 281, 325, 346, 361, 409, 430, 432, 469, 512, 682, 713, 726, 737, 806, 817, 830, 832, 903, 915, 936, 940, 956, 972, 979,  # Texas
    385, 435, 801,  # Utah
    802,  # Vermont
    276, 434, 540, 571, 703, 757, 804,  # Virginia
    206, 253, 360, 425, 509, 564,  # Washington
    304, 681,  # West Virginia
    262, 274, 414, 534, 608, 715, 920,  # Wisconsin
    307,  # Wyoming
]


def gen_income() -> int:
    return random.randint(20000, 35000)


def gen_phone() -> str:
    ac = random.choice(AREA_CODES)
    nxx = random.randint(200, 999)
    xxxx = random.randint(1000, 9999)
    return f"({ac}) {nxx}-{xxxx}"


def gen_email() -> str:
    domains = ["mail.com", "gmail.com", "yahoo.com", "outlook.com"]
    name = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{name}@{random.choice(domains)}"


def parse_cs_from_html(html: str) -> Optional[int]:
    """Извлечь Credit Score из HTML страницы documents."""
    # Паттерны: FICO 650, Credit Score: 650, "score": 650
    patterns = [
        r"(?:FICO|fico|credit\s*score)[:\s]*(\d{3})",
        r"(?:score|Score)[:\s]*(\d{3})",
        r"\"score\"[:\s]*(\d{3})",
        r"\b(\d{3})\s*(?:point|pts?\b)",
    ]
    for p in patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 300 <= val <= 850:
                return val
    return None


async def step_contact(page: Page, data: dict) -> bool:
    """Step 1: Basic info (First Name, Last Name, Address, City, State, Zip, DOB)."""
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(1500)

    # Закрыть cookie overlay если есть
    try:
        await page.locator("button:has-text('Accept'), button:has-text('Accept All'), [aria-label='Accept']").first.click(timeout=2000)
    except Exception:
        pass

    # Заполняем поля по label/name
    await page.get_by_label("First Name", exact=True).fill(data["first_name"])
    await page.get_by_label("Last Name", exact=True).fill(data["last_name"])

    addr = page.get_by_label("Home Address", exact=False)
    await addr.fill(data["address"])
    await page.wait_for_timeout(1200)
    # Address autocomplete: Tab или Enter для выбора первого варианта
    try:
        opts = page.locator("[role='option']")
        if await opts.count() > 0:
            await opts.first.click(timeout=2000)
        else:
            await page.keyboard.press("Tab")
    except Exception:
        await page.keyboard.press("Tab")

    await page.get_by_label("City", exact=True).fill(data["city"])
    await page.get_by_label("State", exact=True).fill(data["state"])
    await page.get_by_label("Zip Code", exact=True).fill(data["zip_code"])
    await page.get_by_label("Date of Birth", exact=False).fill(data["dob"])

    # Phone и Email если есть на странице
    try:
        phone_loc = page.get_by_label("Primary Phone", exact=False).or_(page.get_by_label("Phone", exact=False))
        if await phone_loc.count() > 0:
            await phone_loc.first.fill(data.get("phone", gen_phone()))
    except Exception:
        pass
    try:
        email_loc = page.get_by_label("Email", exact=False)
        if await email_loc.count() > 0:
            await email_loc.first.fill(data.get("email", gen_email()))
    except Exception:
        pass

    await page.wait_for_timeout(300)
    await page.get_by_role("button", name="Continue").click()
    return True


async def step_income(page: Page, data: dict) -> bool:
    """Step: Income (если есть)."""
    try:
        income_loc = page.get_by_label("Individual Annual Income", exact=False).or_(page.get_by_label("Annual Income", exact=False))
        if await income_loc.count() > 0:
            income = data.get("income", gen_income())
            await income_loc.first.fill(str(income))
            await page.wait_for_timeout(300)
            await page.get_by_role("button", name="Continue").click()
            return True
    except Exception:
        pass
    return False


async def run_funnel(
    input_data: dict,
    *,
    headless: Optional[bool] = None,
    proxy: Optional[dict] = None,
    user_agent: Optional[str] = None,
    locale: Optional[str] = None,
    timezone_id: Optional[str] = None,
    viewport: Optional[dict] = None,
    extra_http_headers: Optional[dict] = None,
) -> dict:
    """Основной flow: fill -> rejection -> documents -> parse CS."""
    if headless is None:
        headless = os.environ.get("HEADLESS", "0") == "1"

    data = {
        "first_name": input_data.get("first_name", "Thomas"),
        "last_name": input_data.get("last_name", "Dickson"),
        "address": input_data.get("address", "334 Earp Street"),
        "city": input_data.get("city", "Philadelphia"),
        "state": input_data.get("state", "PA"),
        "zip_code": input_data.get("zip_code", "19147"),
        "dob": input_data.get("dob", "05/12/1998"),
        "phone": input_data.get("phone", gen_phone()),
        "email": input_data.get("email", gen_email()),
        "income": input_data.get("income", gen_income()),
    }

    result = {"success": False, "credit_score": None, "raw_text": "", "error": None}

    async with async_playwright() as p:
        launch_kwargs = {"headless": headless}
        if proxy:
            launch_kwargs["proxy"] = proxy

        browser = await p.chromium.launch(**launch_kwargs)

        context_kwargs = {
            "viewport": viewport or {"width": 1280, "height": 800},
        }
        if user_agent:
            context_kwargs["user_agent"] = user_agent
        if locale:
            context_kwargs["locale"] = locale
        if timezone_id:
            context_kwargs["timezone_id"] = timezone_id
        if extra_http_headers:
            context_kwargs["extra_http_headers"] = extra_http_headers

        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        try:
            await page.goto(URL_BASE, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)

            # Step 1: contact
            await step_contact(page, data)
            await page.wait_for_timeout(3000)

            # Возможен step income
            if "income" in (await page.content()).lower() or "annual" in (await page.content()).lower():
                await step_income(page, data)
                await page.wait_for_timeout(3000)

            # Повторяем Continue пока не дойдём до rejection или documents
            for _ in range(10):
                url = page.url
                html = await page.content()
                if "unable to approve" in html or "unable to approve you" in html:
                    break
                if "386786410" in url or "documents" in url:
                    break
                try:
                    await page.get_by_role("button", name="Continue").click()
                    await page.wait_for_timeout(3000)
                except Exception:
                    break

            # Ищем ссылку "click here" (Adverse Action)
            try:
                link = page.locator("a:has-text('click here'), a:has-text('click here.')").first
                if await link.count() > 0:
                    await link.click()
                    await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            # Переход напрямую на documents если не попали
            if "386786410" not in page.url:
                await page.goto(URL_DOCUMENTS, wait_until="domcontentloaded", timeout=10000)
                await page.wait_for_timeout(2000)

            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(1500)
            try:
                html = await page.content()
                result["raw_text"] = (await page.locator("body").inner_text())[:2000]
            except Exception:
                html = await page.content()
                result["raw_text"] = html[:2000] if html else ""
            result["credit_score"] = parse_cs_from_html(html)
            result["success"] = result["credit_score"] is not None
        except Exception as e:
            result["error"] = str(e)
        finally:
            await browser.close()

    return result


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    input_str = None
    for i, arg in enumerate(sys.argv):
        if arg == "--input" and i + 1 < len(sys.argv):
            input_str = sys.argv[i + 1]
            break
    input_str = input_str or os.environ.get("INPUT_DATA", "{}")
    try:
        input_data = json.loads(input_str)
    except json.JSONDecodeError:
        input_data = {}
    result = asyncio.run(run_funnel(input_data))
    if verbose and result.get("raw_text"):
        print("--- RAW TEXT (first 500 chars) ---", file=sys.stderr)
        print(result["raw_text"][:500], file=sys.stderr)
        print("--- END ---", file=sys.stderr)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
