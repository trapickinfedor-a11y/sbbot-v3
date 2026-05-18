from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 3600,
) -> dict:
    if not bot_token:
        raise ValueError("Bot token is required")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    incoming_hash = parsed.pop("hash", None)
    if not incoming_hash:
        raise ValueError("Missing Telegram hash")

    auth_date = parsed.get("auth_date")
    if auth_date:
        auth_dt = datetime.fromtimestamp(int(auth_date), tz=timezone.utc)
        if auth_dt < datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds):
            raise ValueError("Telegram auth expired")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, incoming_hash):
        raise ValueError("Invalid Telegram signature")

    user_payload = parsed.get("user")
    if not user_payload:
        raise ValueError("Telegram user payload missing")

    return json.loads(user_payload)
