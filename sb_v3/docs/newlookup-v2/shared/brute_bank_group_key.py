"""Stable unique key for BruteBankGroup (bank_code + attributes)."""
from typing import Optional


def make_brute_group_key(bank_code: str, attributes: Optional[str]) -> str:
    bc = (bank_code or "").strip().lower()
    attr = (attributes or "").strip()
    key = f"{bc}|{attr}" if attr else bc
    return key[:220]
