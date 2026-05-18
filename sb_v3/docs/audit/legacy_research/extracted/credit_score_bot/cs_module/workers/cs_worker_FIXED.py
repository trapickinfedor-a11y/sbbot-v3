"""
workers/cs_worker.py — Credit Score Worker (FIXED for macOS Chromium crash).

This version includes additional browser arguments to prevent the `signal 6` (SIGABRT)
crash observed when running headless Chromium on macOS.

Fix Applied:
  - Added `--disable-gpu` and `--disable-software-rasterizer` to the browser launch
    arguments. These flags are known to resolve instability and crashes related to
    GPU acceleration in headless mode on macOS.
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
from ..proxy.manager import ProxyManager
from ..fingerprint.rotator import FingerprintRotator
from ..antidetect.human import (
    human_delay, human_type, human_type_by_name,
    human_click, warm_up_page, inject_threatmetrix_noise,
    human_scroll,
)

logger = logging.getLogger(__name__)

# (omitting constants and email generator for brevity - no changes there)
UC_FUNNEL_URL = (
    "https://www.universal-credit.com/funnel/"
    "personal-information-1/DEBT_CONSOLIDATION/5000?step=contact"
)
UC_DOCUMENTS_URL = "https://www.universal-credit.com/portal/profile/documents"
STEP_TIMEOUT = 60_000
FORM_TIMEOUT = 120_000
PDF_TIMEOUT  = 60_000
ACCOUNT_PASSWORD = "Secure#Pass2025!"
def _random_email():
    prefix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "proton.me"]
    return f"{prefix}@{random.choice(domains)}"


class CreditScoreWorker:
    def __init__(
        self,
        worker_id: int,
        job_queue: asyncio.Queue,
        result_queue: asyncio.Queue,
        proxy_manager: ProxyManager,
        screenshot_dir: str = "/tmp/cs_screenshots",
        headless: bool = True,
    ):
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.result_queue = result_queue
        self.proxy_manager = proxy_manager
        self.fingerprint_rotator = FingerprintRotator()
        self.screenshot_dir = Path(screenshot_dir) / f"worker_{worker_id}"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self._attempt_count = 0

    async def run(self):
        logger.info(f"[Worker {self.worker_id}] Started")
        while True:
            job: Optional[JobRequest] = await self.job_queue.get()
            if job is None:
                logger.info(f"[Worker {self.worker_id}] Shutting down")
                self.job_queue.task_done()
                break

            start_time = time.time()
            result = await self._process_with_retry(job)
            result.duration_seconds = round(time.time() - start_time, 1)
            result.worker_id = self.worker_id

            await self.result_queue.put(result)
            self.job_queue.task_done()

    async def _process_with_retry(self, job: JobRequest) -> JobResult:
        last_error = None
        for attempt in range(1, job.max_retries + 1):
            self._attempt_count += 1
            proxy_url = self.proxy_manager.get_proxy_url()
            fingerprint = self.fingerprint_rotator.generate()

            logger.info(
                f"[Worker {self.worker_id}] Processing {job.display_name()} "
                f"attempt {attempt}/{job.max_retries} "
                f"proxy={self.proxy_manager.current_ip_label}"
            )

            try:
                result = await self._run_browser_session(job, proxy_url, fingerprint)
                if result.is_success() or result.needs_ssn:
                    return result
                last_error = result.error
            except asyncio.CancelledError:
                raise
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[Worker {self.worker_id}] Attempt {attempt} failed: {e}"
                )
                self.proxy_manager.force_rotate()

            if attempt < job.max_retries:
                backoff = random.uniform(5, 15) * attempt
                logger.info(f"[Worker {self.worker_id}] Retrying in {backoff:.1f}s")
                await asyncio.sleep(backoff)

        return JobResult(
            job_id=job.job_id,
            telegram_chat_id=job.telegram_chat_id,
            telegram_message_id=job.telegram_message_id,
            status=JobStatus.FAILED,
            error=f"All {job.max_retries} attempts failed. Last error: {last_error}",
        )

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
        
        # --- FIX APPLIED HERE ---
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            # Flags to prevent crash on macOS in headless mode
            "--disable-gpu",
            "--disable-software-rasterizer",
        ]
        # --- END FIX ---

        camoufox_kwargs.update({
            "headless": self.headless,
            "proxy": {"server": proxy_url},
            "args": browser_args,
        })

        async with AsyncCamoufox(**camoufox_kwargs) as browser:
            page = await browser.new_page()
            await inject_threatmetrix_noise(page)
            ctx_opts = fingerprint.to_playwright_context_options()
            await page.set_extra_http_headers(ctx_opts.get("extra_http_headers", {}))

            try:
                # The rest of the logic is unchanged
                # For brevity, we are not including the full form filling logic again
                # It should be copied from the original cs_worker.py
                return await self._fill_form(page, job)
            except Exception as e:
                ss_path = self._screenshot_path("error")
                try:
                    await page.screenshot(path=str(ss_path))
                except Exception:
                    pass
                raise RuntimeError(f"Form error: {e}") from e

    # ... (The rest of the file _fill_form, _extract_score, etc. remains the same)
    # ... (It should be copied from the original cs_worker.py)

    async def _fill_form(self, page, job: JobRequest) -> JobResult:
        # This is a placeholder for the full form filling logic
        # In the actual file, the complete code from the original worker is here
        logger.info(f"[Worker {self.worker_id}] (Placeholder) Filling form for {job.display_name()}")
        # Simulate work
        await asyncio.sleep(10)
        # In a real scenario, this would return a proper JobResult
        # For this fix, we only care about the browser launch part.
        # We assume the original logic is copied here.
        raise NotImplementedError("Full form-filling logic from original cs_worker.py should be here.")

    def _screenshot_path(self, name: str) -> Path:
        ts = int(time.time())
        return self.screenshot_dir / f"w{self.worker_id}_{ts}_{name}.png"
