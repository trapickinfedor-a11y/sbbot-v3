from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class GuaranteePolicy:
    minutes: int
    label: str
    report_requires_video: bool = False
    allows_return: bool = True
    requires_reveal_confirmation: bool = True


def format_guarantee_window(minutes: int) -> str:
    if minutes % (24 * 60) == 0:
        hours = minutes // 60
        return "24 hours" if hours == 24 else f"{hours} hours"
    if minutes % 60 == 0:
        hours = minutes // 60
        return "1 hour" if hours == 1 else f"{hours} hours"
    if minutes == 1:
        return "1 minute"
    return f"{minutes} minutes"


def get_seller_guarantee_policy(
    *,
    product_type: str | None = None,
    product_subtype: str | None = None,
    bank_name: str | None = None,
) -> GuaranteePolicy:
    normalized_type = (product_type or "").strip().lower()
    normalized_subtype = (product_subtype or "").strip().lower()
    normalized_bank_name = (bank_name or "").strip().lower()

    if normalized_type == "nfc":
        return GuaranteePolicy(minutes=60, label="NFC")
    if normalized_subtype == "log":
        return GuaranteePolicy(minutes=6 * 60, label="Logs")
    if normalized_type == "enrol" or normalized_type == "enroll":
        return GuaranteePolicy(minutes=60, label="Enroll")
    if normalized_subtype == "selfreg_cc":
        return GuaranteePolicy(minutes=48 * 60, label="Selfregs CC")
    if normalized_subtype == "checks" or "check" in normalized_bank_name or "cheque" in normalized_bank_name:
        return GuaranteePolicy(
            minutes=60,
            label="Checks",
            allows_return=False,
            requires_reveal_confirmation=False,
        )
    if normalized_type == "otp" or normalized_subtype == "otp_card":
        return GuaranteePolicy(minutes=60, label="OTP Card")
    if normalized_subtype == "selfreg" or "selfreg ba" in normalized_bank_name:
        return GuaranteePolicy(minutes=48 * 60, label="Selfregs BA")
    if normalized_type == "cc" or "debit" in normalized_bank_name:
        return GuaranteePolicy(minutes=15, label="CC / Debit", report_requires_video=True)
    if normalized_subtype == "brute":
        return GuaranteePolicy(minutes=15, label="Brute", report_requires_video=True)

    return GuaranteePolicy(minutes=15, label="Default")


def get_product_guarantee_policy(*, category: str, service: str, file_type: str | None = None) -> GuaranteePolicy:
    normalized_category = (category or "").strip().lower()
    normalized_service = (service or "").strip().lower()
    normalized_file_type = (file_type or "").strip().lower()

    if normalized_category == "docs":
        return GuaranteePolicy(minutes=60, label="Documents")
    if normalized_category == "pros_fullz":
        return GuaranteePolicy(minutes=3 * 60, label="PROS & FULLZ")
    if normalized_file_type == "zip":
        return GuaranteePolicy(minutes=2 * 60, label="ZIP delivery")
    return GuaranteePolicy(minutes=60, label=normalized_service or normalized_category or "product")


def is_guarantee_active(guarantee_until: datetime | None, *, now: datetime | None = None) -> bool:
    if guarantee_until is None:
        return False
    current_time = now or datetime.now(timezone.utc)
    return guarantee_until >= current_time
