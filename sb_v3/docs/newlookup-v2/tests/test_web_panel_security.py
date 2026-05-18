import hashlib
import hmac
import json
import time
import unittest
from typing import Optional
from urllib.parse import quote

from pydantic import ValidationError

from shared.utils.telegram_auth import validate_telegram_init_data
from web_panel.api.service_prices import PriceUpdate


def _build_init_data(user_payload: dict, bot_token: str, auth_date: Optional[int] = None) -> str:
    auth_date = auth_date or int(time.time())
    user_json = json.dumps(user_payload, separators=(",", ":"))
    pairs = {
        "auth_date": str(auth_date),
        "query_id": "AAEAAAE",
        "user": user_json,
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return "&".join(f"{k}={quote(v)}" for k, v in pairs.items())


class TelegramAuthTests(unittest.TestCase):
    def test_validate_telegram_init_data_accepts_valid_payload(self) -> None:
        bot_token = "123456:token"
        payload = _build_init_data({"id": 1001, "username": "seller"}, bot_token)

        user = validate_telegram_init_data(payload, bot_token)

        self.assertEqual(user["id"], 1001)
        self.assertEqual(user["username"], "seller")

    def test_validate_telegram_init_data_rejects_invalid_hash(self) -> None:
        with self.assertRaises(ValueError):
            validate_telegram_init_data("auth_date=1&user=%7B%7D&hash=broken", "123456:token")

    def test_validate_telegram_init_data_rejects_expired_payload(self) -> None:
        bot_token = "123456:token"
        expired_auth_date = int(time.time()) - 3700
        payload = _build_init_data({"id": 1001}, bot_token, auth_date=expired_auth_date)

        with self.assertRaises(ValueError):
            validate_telegram_init_data(payload, bot_token)


class ServicePriceValidationTests(unittest.TestCase):
    def test_price_update_requires_reason(self) -> None:
        with self.assertRaises(ValidationError):
            PriceUpdate(price=10.0)

    def test_price_update_rejects_negative_price(self) -> None:
        with self.assertRaises(ValidationError):
            PriceUpdate(reason="bad", price=-1.0)
