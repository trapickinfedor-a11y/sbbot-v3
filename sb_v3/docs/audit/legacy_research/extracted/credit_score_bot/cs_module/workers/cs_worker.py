"""
workers/cs_worker.py — Credit Score Worker.

Each worker:
  1. Pulls a JobRequest from the shared queue
  2. Gets a fresh fingerprint profile
  3. Gets the current proxy URL (auto-rotates every 3 attempts)
  4. Launches camoufox browser with anti-detection measures
  5. Fills the universal-credit.com form (3 steps)
  6. Downloads the Adverse Action Notice PDF
  7. Extracts the credit score
  8. Falls back to petalcard.com if needed (requires SSN)
  9. Returns JobResult to the result queue

Anti-detection measures applied per request:
  - New browser fingerprint (UA, screen, timezone, language, WebGL)
  - New proxy IP (rotated every 3 attempts per worker)
  - Human-like typing with per-character delays
  - Bezier-curve mouse movement
  - Page warm-up (random scroll + mouse movement after load)
  - ThreatMetrix noise injection (canvas, audio, WebGL, battery)
  - Random delays between all interactions
"""

import asyncio
import logging
import random
import re
import string
import time
import os
from pathlib import Path
from typing import Optional

from camoufox.async_api import AsyncCamoufox

from ..bot_interface.models import JobRequest, JobResult, JobStatus
from ..bot_interface.ssn_flow import ssn_flow
from aiogram import Bot
from ..proxy.manager import ProxyManager
from ..fingerprint.rotator import FingerprintRotator
from ..antidetect.human import (
    human_delay, human_type, human_type_by_name,
    human_click, warm_up_page, inject_threatmetrix_noise,
    human_scroll,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UC_FUNNEL_URL = (
    "https://www.universal-credit.com/funnel/"
    "personal-information-1/DEBT_CONSOLIDATION/5000?step=contact"
)
UC_DOCUMENTS_URL = "https://www.universal-credit.com/portal/profile/documents"

STEP_TIMEOUT = 60_000      # ms — max time to wait for a step to complete
FORM_TIMEOUT = 120_000     # ms — max time for full form submission
PDF_TIMEOUT  = 60_000      # ms — max time to wait for PDF download

# Password for all created accounts
ACCOUNT_PASSWORD = "Secure#Pass2025!"

# ---------------------------------------------------------------------------
# Email generator
# ---------------------------------------------------------------------------

def _random_email() -> str:
    """Generate a unique throwaway email address."""
    prefix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "proton.me"]
    return f"{prefix}@{random.choice(domains)}"


# ---------------------------------------------------------------------------
# Credit Score Worker
# ---------------------------------------------------------------------------

MAX_RETRIES = 2

class CreditScoreWorker:
    """
    Single async worker that processes JobRequest items from a queue.
    """

    def __init__(
        self,
        worker_id: int,
        job_queue: asyncio.Queue,
        result_queue: asyncio.Queue,
        proxy_manager: ProxyManager,
        bot: Bot,
        screenshot_dir: str = "/tmp/cs_screenshots",
        headless: bool = True,
    ):
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.result_queue = result_queue
        self.proxy_manager = proxy_manager
        self.bot = bot
        self.fingerprint_rotator = FingerprintRotator()
        self.screenshot_dir = Path(screenshot_dir) / f"worker_{worker_id}"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self._attempt_count = 0

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self):
        logger.info(f"[Worker {self.worker_id}] Started")
        while True:
            job: Optional[JobRequest] = await self.job_queue.get()
            if job is None:  # Shutdown sentinel
                logger.info(f"[Worker {self.worker_id}] Shutting down")
                self.job_queue.task_done()
                break

            start_time = time.time()
            result = await self._process_with_retry(job)
            result.duration_seconds = round(time.time() - start_time, 1)
            result.worker_id = self.worker_id

            await self.result_queue.put(result)
            self.job_queue.task_done()

    # ------------------------------------------------------------------
    # Retry wrapper
    # ------------------------------------------------------------------

    async def _process_with_retry(self, job: JobRequest) -> JobResult:
        last_error = None
        max_retries = max(1, int(getattr(job, "max_retries", MAX_RETRIES + 1)))

        for attempt in range(1, max_retries + 1):
            self._attempt_count += 1
            proxy_url = self.proxy_manager.get_proxy_url()
            fingerprint = self.fingerprint_rotator.generate()

            logger.info(
                f"[Worker {self.worker_id}] Processing {job.display_name()} "
                f"attempt {attempt}/{max_retries} "
                f"proxy={self.proxy_manager.current_ip_label}"
            )

            try:
                result = await self._run_browser_session(job, proxy_url, fingerprint)
                if result.is_success():
                    self.proxy_manager.on_success()
                    return result
                if result.needs_ssn:
                    self.proxy_manager.on_success()
                    ssn = await self._request_ssn(job, result)
                    if ssn:
                        job.ssn = ssn
                        continue
                    return result

                last_error = result.error or "Unknown error"
                self.proxy_manager.on_failure()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[Worker {self.worker_id}] Attempt {attempt} failed with exception: {e}",
                    exc_info=True,
                )
                self.proxy_manager.force_rotate()

            if attempt < max_retries:
                await self.bot.send_message(
                    job.telegram_chat_id,
                    f"⚠️ Не удалось получить ответ с первого раза. Пробую еще раз... (Попытка {attempt + 1})"
                )
                backoff = random.uniform(5, 15) * attempt
                logger.info(f"[Worker {self.worker_id}] Retrying in {backoff:.1f}s")
                await asyncio.sleep(backoff)

        return JobResult(
            job_id=job.job_id,
            telegram_chat_id=job.telegram_chat_id,
            telegram_message_id=job.telegram_message_id,
            status=JobStatus.FAILED,
            error=f"Could not access the service after multiple attempts. Last error: {last_error or 'Unknown error'}",
        )

    # ------------------------------------------------------------------
    # SSN request flow
    # ------------------------------------------------------------------

    async def _request_ssn(self, job: JobRequest, result: JobResult) -> Optional[str]:
        """
        Pause the job and wait for the user to provide SSN via Telegram.
        Times out after 10 minutes.
        """
        fut = ssn_flow.create_request(job.job_id, job.telegram_chat_id)
        # Notify bot to ask user for SSN
        await self.result_queue.put(JobResult(
            job_id=job.job_id,
            telegram_chat_id=job.telegram_chat_id,
            telegram_message_id=job.telegram_message_id,
            status=JobStatus.WAITING_SSN,
            needs_ssn=True,
        ))
        try:
            ssn = await asyncio.wait_for(fut, timeout=600)  # 10 min
            return ssn
        except asyncio.TimeoutError:
            ssn_flow.cancel_request(job.job_id)
            logger.warning(f"[Worker {self.worker_id}] SSN timeout for job {job.job_id}")
            return None

    # ------------------------------------------------------------------
    # Browser session
    # ------------------------------------------------------------------

    async def _run_browser_session(
        self,
        job: JobRequest,
        proxy_url: str,
        fingerprint,
    ) -> JobResult:
        """
        Launch a fresh browser session, fill the form, and extract the score.
        """
        camoufox_kwargs = fingerprint.to_camoufox_config()

        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-software-rasterizer",
        ]

        camoufox_kwargs.update({
            "headless": self.headless,
            "proxy": {"server": proxy_url},
            "args": browser_args,
        })

        async with AsyncCamoufox(**camoufox_kwargs) as browser:
            page = await browser.new_page()

            # Inject anti-fingerprint noise before any navigation
            await inject_threatmetrix_noise(page)

            # Set extra headers from fingerprint
            ctx_opts = fingerprint.to_playwright_context_options()
            await page.set_extra_http_headers(
                ctx_opts.get("extra_http_headers", {})
            )

            try:
                result = await self._fill_form(page, job)
                return result
            except Exception as e:
                ss_path = self._screenshot_path("error")
                try:
                    await page.screenshot(path=str(ss_path))
                except Exception:
                    pass
                raise RuntimeError(f"Form error: {e}") from e

    # ------------------------------------------------------------------
    # Form filling — Step 1: Contact information
    # ------------------------------------------------------------------

    async def _fill_form(self, page, job: JobRequest) -> JobResult:
        """Navigate to the funnel and fill all 3 steps."""
        email = job.email or _random_email()

        # Navigate to funnel start
        await page.goto(UC_FUNNEL_URL, wait_until="domcontentloaded", timeout=FORM_TIMEOUT)
        await warm_up_page(page)
        await self._screenshot(page, "step1_start")

        # --- Step 1: Personal information ---
        await self._fill_step1(page, job)
        await self._screenshot(page, "step1_filled")
        await self._click_continue(page)

        # Wait for step 2
        await self._wait_for_step(page, "income")
        await self._screenshot(page, "step2_start")

        # --- Step 2: Income ---
        await self._fill_step2(page, job)
        await self._screenshot(page, "step2_filled")
        await self._click_continue(page)

        # Wait for step 3
        await self._wait_for_step(page, "login")
        await self._screenshot(page, "step3_start")

        # --- Step 3: Create account ---
        await self._fill_step3(page, email)
        await self._screenshot(page, "step3_filled")

        # Submit form
        await self._submit_form(page)

        # Wait for result page
        result_url = await self._wait_for_result(page)
        await self._screenshot(page, "result_page")

        logger.info(f"[Worker {self.worker_id}] Result URL: {result_url}")

        # Extract score
        if "adverse-page" in result_url or "offer-page" in result_url:
            return await self._extract_score(page, job)
        else:
            # Still on login step — likely blocked
            return JobResult(
                job_id=job.job_id,
                telegram_chat_id=job.telegram_chat_id,
                telegram_message_id=job.telegram_message_id,
                status=JobStatus.FAILED,
                error=f"Form did not advance past login. URL: {result_url}",
            )

    async def _fill_step1(self, page, job: JobRequest):
        """Fill contact information form."""
        await human_type_by_name(page, "borrowerFirstName", job.first_name)
        await human_type_by_name(page, "borrowerLastName", job.last_name)

        # Address (geosuggest autocomplete)
        await self._fill_address(page, job)

        # Date of birth
        await self._fill_dob(page, job.dob)

        # Phone (optional — field may not appear)
        await self._fill_phone_if_present(page, getattr(job, "phone", None))

    async def _fill_address(self, page, job: JobRequest):
        """Fill the geosuggest address field and select the first suggestion."""
        search_text = f"{job.street} {job.zip_code}"
        addr_sel = "[name='borrowerStreet'], #geosuggest__input--borrowerStreet, [id*='geosuggest']"

        addr_field = await page.query_selector(addr_sel)
        if addr_field is None:
            raise RuntimeError("Address field not found")

        await addr_field.click()
        await human_delay(300, 600)
        await addr_field.fill("")
        await asyncio.sleep(0.2)

        # Type address character by character
        for char in search_text:
            await addr_field.type(char, delay=0)
            await typing_delay_ms(char)

        # Wait for autocomplete suggestions
        await asyncio.sleep(2)

        # Select first suggestion that contains the state
        suggestions = await page.query_selector_all(
            ".geosuggest__suggests li, [class*='suggest'] li, [class*='autocomplete'] li"
        )
        selected = False
        for sug in suggestions:
            text = await sug.inner_text()
            if job.state.upper() in text.upper():
                await sug.click()
                selected = True
                break

        if not selected and suggestions:
            await suggestions[0].click()

        await human_delay(500, 1000)

        # Verify/fill city, state, zip if they appeared as separate fields
        for fname, value in [
            ("borrowerCity", job.city),
            ("borrowerState", job.state),
            ("borrowerZipCode", job.zip_code),
        ]:
            el = await page.query_selector(f"[name='{fname}']")
            if el:
                current = await el.input_value()
                if not current.strip():
                    await human_type(page, f"[name='{fname}']", value)

    async def _fill_dob(self, page, dob: str):
        """Fill date of birth field (MM/DD/YYYY)."""
        # Try single field first
        dob_field = await page.query_selector("[name='borrowerDateOfBirth']")
        if dob_field:
            await human_type(page, "[name='borrowerDateOfBirth']", dob)
            return

        # Fragmented DOB (MM / DD / YYYY)
        parts = dob.split("/")
        if len(parts) == 3:
            mm, dd, yyyy = parts
            labels = ["month", "day", "year"]
            values = [mm, dd, yyyy]
            for label, val in zip(labels, values):
                sel = (
                    f"[aria-label*='{label}' i], "
                    f"[placeholder*='{label}' i], "
                    f"[hint*='{label}' i]"
                )
                el = await page.query_selector(sel)
                if el:
                    await el.click()
                    await human_delay(100, 300)
                    await el.fill(val)
                    await human_delay(100, 200)

    async def _fill_phone_if_present(self, page, phone: Optional[str]):
        """Fill phone number if the field exists (3-fragment or single)."""
        if not phone:
            return
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 10:
            return
        area, first3, last4 = digits[:3], digits[3:6], digits[6:10]

        # Try 3-fragment phone fields
        for hint_text, value in [
            ("area code", area),
            ("first 3", first3),
            ("last 4", last4),
        ]:
            el = await page.evaluate_handle(
                f"""() => Array.from(document.querySelectorAll('input')).find(
                    el => (el.getAttribute('hint') || el.getAttribute('aria-label') || '').toLowerCase().includes('{hint_text}')
                )"""
            )
            try:
                if el:
                    await el.as_element().fill(value)
                    await human_delay(100, 250)
            except Exception:
                pass

        # Fallback: single phone field
        single = await page.query_selector("[name='borrowerPhoneNumber'], [name='phone']")
        if single:
            await human_type(page, "[name='borrowerPhoneNumber'], [name='phone']", digits[:10])

    # ------------------------------------------------------------------
    # Form filling — Step 2: Income
    # ------------------------------------------------------------------

    async def _fill_step2(self, page, job: JobRequest):
        """Fill income information."""
        income_field = await page.query_selector("[name='borrowerIncome']")
        if income_field:
            await human_type(page, "[name='borrowerIncome']", job.annual_income)
        else:
            # Fallback: first number input on page
            inputs = await page.query_selector_all("input[type='number'], input[inputmode='numeric']")
            if inputs:
                await inputs[0].fill(job.annual_income)

    # ------------------------------------------------------------------
    # Form filling — Step 3: Create account
    # ------------------------------------------------------------------

    async def _fill_step3(self, page, email: str):
        """Fill account creation form."""
        await human_type(page, "[name='username'], [name='email'], [type='email']", email)
        await human_delay(300, 700)
        await human_type(page, "[name='password'], [type='password']", ACCOUNT_PASSWORD)
        await human_delay(400, 800)

        # Check agreements checkbox
        checkbox = await page.query_selector(
            "[name='agreements'], [type='checkbox'], [class*='checkbox']"
        )
        if checkbox:
            checked = await checkbox.is_checked()
            if not checked:
                await checkbox.click()
                await human_delay(200, 500)

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    async def _click_continue(self, page):
        """Click the Continue button."""
        btn_sel = (
            "button:has-text('Continue'), "
            "button[type='submit']:has-text('Continue'), "
            "input[type='submit'][value*='Continue' i]"
        )
        btn = await page.query_selector(btn_sel)
        if btn:
            await human_click(page, btn_sel)
        else:
            await page.keyboard.press("Enter")
        await human_delay(500, 1500)

    async def _submit_form(self, page):
        """Click the final 'Check Your Rate' submit button."""
        btn_sel = (
            "button:has-text('Check Your Rate'), "
            "button[type='submit']:has-text('Check'), "
            "button[type='submit']"
        )
        btn = await page.query_selector(btn_sel)
        if btn:
            await human_click(page, btn_sel)
        else:
            await page.keyboard.press("Enter")

        # Wait for ThreatMetrix overlay to appear and pass
        await asyncio.sleep(3)
        overlay = await page.query_selector("#sec-overlay")
        if overlay:
            logger.info(f"[Worker {self.worker_id}] ThreatMetrix overlay detected — waiting...")
            # Wait up to 60s for overlay to disappear
            for _ in range(60):
                await asyncio.sleep(1)
                still_visible = await page.evaluate(
                    "() => { const el = document.getElementById('sec-overlay'); "
                    "return el && el.offsetParent !== null; }"
                )
                if not still_visible:
                    break
            logger.info(f"[Worker {self.worker_id}] Overlay gone — continuing")

    async def _wait_for_step(self, page, step_name: str, timeout: int = STEP_TIMEOUT):
        """Wait until the URL contains the expected step parameter."""
        deadline = time.time() + timeout / 1000
        while time.time() < deadline:
            url = page.url
            if f"step={step_name}" in url:
                return
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Step '{step_name}' did not appear within {timeout}ms. URL: {page.url}")

    async def _wait_for_result(self, page, timeout: int = FORM_TIMEOUT) -> str:
        """Wait for the form to reach a result page (adverse-page or offer-page)."""
        deadline = time.time() + timeout / 1000
        while time.time() < deadline:
            url = page.url
            if "adverse-page" in url or "offer-page" in url:
                return url
            await asyncio.sleep(1)
        return page.url  # Return whatever URL we ended up on

    # ------------------------------------------------------------------
    # Score extraction
    # ------------------------------------------------------------------

    async def _extract_score(self, page, job: JobRequest) -> JobResult:
        """
        Navigate to Documents portal, find Adverse Action Notice,
        download PDF, and extract credit score.
        """
        # Navigate to documents portal
        await page.goto(UC_DOCUMENTS_URL, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(5)

        # Wait for Adverse Action Notice to appear (up to 45s)
        adverse_appeared = False
        for _ in range(45):
            await asyncio.sleep(1)
            has_adverse = await page.evaluate(
                "() => Array.from(document.querySelectorAll('*')).some("
                "el => el.textContent && el.textContent.toLowerCase().includes('adverse action'))"
            )
            if has_adverse:
                adverse_appeared = True
                break

        await self._screenshot(page, "documents_page")

        if not adverse_appeared:
            # Possibly approved — try to find any document download
            logger.warning(f"[Worker {self.worker_id}] Adverse Action Notice not found in Documents")
            return JobResult(
                job_id=job.job_id,
                telegram_chat_id=job.telegram_chat_id,
                telegram_message_id=job.telegram_message_id,
                status=JobStatus.FAILED,
                error="Adverse Action Notice not found in Documents portal",
            )

        # Find and click the download button for Adverse Action Notice
        pdf_data = await self._download_adverse_action_pdf(page)

        if pdf_data is None:
            return JobResult(
                job_id=job.job_id,
                telegram_chat_id=job.telegram_chat_id,
                telegram_message_id=job.telegram_message_id,
                status=JobStatus.FAILED,
                error="Could not download Adverse Action Notice PDF",
            )

        # Save PDF
        pdf_path = self.screenshot_dir / f"adverse_action_{job.job_id}.pdf"
        pdf_path.write_bytes(pdf_data)

        # Extract score from PDF
        score = self._parse_score_from_pdf(pdf_data)

        if score:
            return JobResult(
                job_id=job.job_id,
                telegram_chat_id=job.telegram_chat_id,
                telegram_message_id=job.telegram_message_id,
                status=JobStatus.SUCCESS,
                credit_score=score,
                source="universal-credit.com",
                pdf_path=str(pdf_path),
            )
        else:
            return JobResult(
                job_id=job.job_id,
                telegram_chat_id=job.telegram_chat_id,
                telegram_message_id=job.telegram_message_id,
                status=JobStatus.FAILED,
                error="PDF downloaded but credit score not found in text",
                pdf_path=str(pdf_path),
            )

    async def _download_adverse_action_pdf(self, page) -> Optional[bytes]:
        """
        Click the Adverse Action Notice download button and capture the PDF bytes.
        Uses network response interception to capture the S3 PDF.
        """
        pdf_bytes_holder = []

        async def handle_response(response):
            ct = response.headers.get("content-type", "")
            if "pdf" in ct or response.url.endswith(".pdf"):
                try:
                    body = await response.body()
                    if body and body[:4] == b"%PDF":
                        pdf_bytes_holder.append(body)
                except Exception:
                    pass

        page.on("response", handle_response)

        # Find the download button for Adverse Action Notice
        # Strategy: find the row containing "Adverse Action" text, then find the download icon
        dl_btn = await page.evaluate_handle("""
            () => {
                const rows = Array.from(document.querySelectorAll('li, tr, [class*="row"], [class*="item"], [class*="document"]'));
                for (const row of rows) {
                    if (row.textContent.toLowerCase().includes('adverse action')) {
                        // Find download button/link within this row
                        const btn = row.querySelector('a[href], button, [class*="download"], svg');
                        if (btn) return btn;
                    }
                }
                // Fallback: any download link near "adverse action" text
                const allLinks = Array.from(document.querySelectorAll('a, button'));
                for (const link of allLinks) {
                    const parent = link.closest('li, tr, div');
                    if (parent && parent.textContent.toLowerCase().includes('adverse action')) {
                        return link;
                    }
                }
                return null;
            }
        """)

        el = dl_btn.as_element() if dl_btn else None
        if el:
            # Use context.expect_page for new tab, or just click and intercept response
            try:
                async with page.context.expect_page(timeout=8000) as new_page_info:
                    await el.click()
                new_page = await new_page_info.value
                await new_page.wait_for_load_state("load", timeout=30_000)
                # Check if new page is a PDF
                new_url = new_page.url
                if new_url.endswith(".pdf") or "pdf" in new_url.lower():
                    resp = await page.context.request.get(new_url)
                    body = await resp.body()
                    if body[:4] == b"%PDF":
                        return body
                await new_page.close()
            except Exception:
                pass

            # Fallback: click and wait for network response
            await el.click()
            await asyncio.sleep(5)

            if pdf_bytes_holder:
                return pdf_bytes_holder[0]

        page.remove_listener("response", handle_response)
        return None

    def _parse_score_from_pdf(self, pdf_data: bytes) -> Optional[int]:
        """Extract credit score from PDF bytes using pdfminer or regex."""
        try:
            import io
            from pdfminer.high_level import extract_text
            text = extract_text(io.BytesIO(pdf_data))
        except Exception:
            try:
                # Fallback: raw text extraction
                text = pdf_data.decode("latin-1", errors="replace")
            except Exception:
                return None

        # Patterns for credit score in Adverse Action Notice
        patterns = [
            r"(?:credit\s+score|fico\s+score|score\s+value)[^\d]*(\d{3})",
            r"(?:your\s+score\s+is)[^\d]*(\d{3})",
            r"(?:score)[^\d]*(\d{3})",
            r"\b([5-8]\d{2})\b",  # Typical credit score range 500-899
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                score = int(m.group(1))
                if 300 <= score <= 850:
                    return score
        return None

    # ------------------------------------------------------------------
    # Screenshot helper
    # ------------------------------------------------------------------

    def _screenshot_path(self, name: str) -> Path:
        ts = int(time.time())
        return self.screenshot_dir / f"w{self.worker_id}_{ts}_{name}.png"

    async def _screenshot(self, page, name: str):
        try:
            path = self._screenshot_path(name)
            await page.screenshot(path=str(path), full_page=False)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Typing delay helper (module-level for use in _fill_address)
# ---------------------------------------------------------------------------

async def typing_delay_ms(char: str):
    """Per-character typing delay (same as antidetect.human.typing_delay)."""
    if char in " \t\n":
        base = random.uniform(80, 200)
    elif char in "!@#$%^&*()_+-=[]{}|;':\",./<>?":
        base = random.uniform(100, 250)
    else:
        base = random.uniform(50, 180)
    if random.random() < 0.07:
        base += random.uniform(300, 800)
    await asyncio.sleep(base / 1000)
