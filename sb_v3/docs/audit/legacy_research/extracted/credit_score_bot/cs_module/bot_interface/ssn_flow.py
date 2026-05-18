"""
bot_interface/ssn_flow.py — SSN request flow for Telegram bot.

When the parser needs an SSN (e.g. for petalcard.com fallback),
it pauses the job and notifies the bot. The bot asks the user
for their SSN, then resumes the job with the provided value.

Flow:
  1. Parser sets result.needs_ssn = True and result.status = WAITING_SSN
  2. Bot sends SSN request message to user
  3. User replies with SSN
  4. Bot calls ssn_flow.resume_job(job_id, ssn)
  5. Parser resumes processing with SSN
"""

import asyncio
import re
import logging
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

# SSN format: XXX-XX-XXXX or XXXXXXXXX (9 digits)
_SSN_PATTERN = re.compile(r"^\d{3}-?\d{2}-?\d{4}$")


def validate_ssn(raw: str) -> Optional[str]:
    """
    Validate and normalize SSN input.
    Returns formatted SSN (XXX-XX-XXXX) or None if invalid.
    """
    cleaned = raw.strip().replace(" ", "")
    if not _SSN_PATTERN.match(cleaned):
        return None
    # Normalize to XXX-XX-XXXX
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) != 9:
        return None
    return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"


class SSNFlowManager:
    """
    Manages pending SSN requests.
    Maps job_id → asyncio.Future so the worker can await the SSN.
    """

    def __init__(self):
        # job_id -> Future[str]  (str = validated SSN)
        self._pending: dict[str, asyncio.Future] = {}
        # job_id -> chat_id (for cleanup)
        self._chat_map: dict[str, int] = {}

    def create_request(self, job_id: str, chat_id: int) -> asyncio.Future:
        """
        Create a pending SSN request for a job.
        The worker awaits the returned Future.
        """
        loop = asyncio.get_event_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[job_id] = fut
        self._chat_map[job_id] = chat_id
        logger.info(f"[SSNFlow] SSN requested for job {job_id} (chat {chat_id})")
        return fut

    def provide_ssn(self, job_id: str, raw_ssn: str) -> bool:
        """
        Called by the bot when the user provides their SSN.
        Returns True if the SSN was valid and the job was resumed.
        """
        ssn = validate_ssn(raw_ssn)
        if ssn is None:
            logger.warning(f"[SSNFlow] Invalid SSN provided for job {job_id}: {raw_ssn!r}")
            return False

        fut = self._pending.get(job_id)
        if fut is None:
            logger.warning(f"[SSNFlow] No pending SSN request for job {job_id}")
            return False

        if fut.done():
            logger.warning(f"[SSNFlow] Future already done for job {job_id}")
            return False

        fut.set_result(ssn)
        del self._pending[job_id]
        self._chat_map.pop(job_id, None)
        logger.info(f"[SSNFlow] SSN provided for job {job_id}")
        return True

    def cancel_request(self, job_id: str):
        """Cancel a pending SSN request (e.g. user cancelled)."""
        fut = self._pending.pop(job_id, None)
        self._chat_map.pop(job_id, None)
        if fut and not fut.done():
            fut.cancel()
            logger.info(f"[SSNFlow] SSN request cancelled for job {job_id}")

    def has_pending(self, job_id: str) -> bool:
        return job_id in self._pending

    def pending_jobs(self) -> list[str]:
        return list(self._pending.keys())


# Module-level singleton shared between workers and bot handlers
ssn_flow = SSNFlowManager()
