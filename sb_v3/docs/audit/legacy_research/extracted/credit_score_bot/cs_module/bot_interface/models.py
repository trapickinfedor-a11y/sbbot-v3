"""
bot_interface/models.py — Data models for Telegram bot integration.

JobRequest  — what the bot sends to the parser module
JobResult   — what the parser module returns to the bot
JobStatus   — enum for tracking job state
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class JobStatus(Enum):
    PENDING    = "pending"      # In queue, not yet started
    RUNNING    = "running"      # Currently being processed by a worker
    WAITING_SSN = "waiting_ssn" # Paused — waiting for user to provide SSN
    SUCCESS    = "success"      # Score obtained successfully
    FAILED     = "failed"       # All retries exhausted, no score
    CANCELLED  = "cancelled"    # Cancelled by user


@dataclass
class JobRequest:
    """
    A single credit score lookup request submitted by the Telegram bot.
    """
    # Telegram context
    telegram_chat_id: int           # Chat ID to send result back to
    telegram_message_id: int        # Original message ID (for reply)
    telegram_user_id: int           # User who submitted the request

    # Applicant personal data
    first_name: str
    last_name: str
    street: str
    city: str
    state: str                      # 2-letter code, e.g. "CA"
    zip_code: str
    dob: str                        # MM/DD/YYYY
    annual_income: str = "32000"

    # Optional — may be provided later via SSN request flow
    ssn: Optional[str] = None       # XXX-XX-XXXX format

    # Email for account creation (auto-generated if not provided)
    email: Optional[str] = None

    # Internal tracking
    job_id: str = field(default_factory=lambda: f"job_{int(time.time()*1000)}")
    created_at: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3

    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def full_address(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"


@dataclass
class JobResult:
    """
    Result returned by the parser module to the Telegram bot.
    """
    job_id: str
    telegram_chat_id: int
    telegram_message_id: int

    status: JobStatus
    credit_score: Optional[int] = None
    source: Optional[str] = None        # "universal-credit.com" | "petalcard.com"
    pdf_path: Optional[str] = None      # Local path to downloaded PDF

    error: Optional[str] = None
    worker_id: Optional[int] = None
    proxy_ip: Optional[str] = None
    duration_seconds: Optional[float] = None

    # SSN request flow
    needs_ssn: bool = False             # True if SSN is required to proceed

    def is_success(self) -> bool:
        return self.status == JobStatus.SUCCESS and self.credit_score is not None

    def summary(self) -> str:
        if self.is_success():
            return (
                f"✅ Credit Score: **{self.credit_score}**\n"
                f"Source: {self.source}\n"
                f"Worker: #{self.worker_id}"
            )
        elif self.needs_ssn:
            return "🔑 SSN required to proceed. Please provide SSN."
        else:
            return f"❌ Failed: {self.error or 'Unknown error'}"
