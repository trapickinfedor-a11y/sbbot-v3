from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

import aiohttp


class BTCPayConfigurationError(RuntimeError):
    pass


@dataclass
class BTCPayInvoice:
    invoice_id: str
    checkout_url: str
    status: str
    raw_payload: dict[str, Any]
    expires_at: Optional[datetime] = None


class BTCPayService:
    @staticmethod
    def _base_url() -> str:
        url = (os.getenv("BTCPAY_SERVER_URL") or "").rstrip("/")
        if not url:
            raise BTCPayConfigurationError("BTCPAY_SERVER_URL is not configured")
        return url

    @staticmethod
    def _store_id() -> str:
        store_id = os.getenv("BTCPAY_STORE_ID", "").strip()
        if not store_id:
            raise BTCPayConfigurationError("BTCPAY_STORE_ID is not configured")
        return store_id

    @staticmethod
    def _api_key() -> str:
        api_key = os.getenv("BTCPAY_API_KEY", "").strip()
        if not api_key:
            raise BTCPayConfigurationError("BTCPAY_API_KEY is not configured")
        return api_key

    @staticmethod
    def _headers() -> dict[str, str]:
        api_key = BTCPayService._api_key()
        return {
            "Authorization": f"token {api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def is_configured() -> bool:
        return all(
            [
                os.getenv("BTCPAY_SERVER_URL"),
                os.getenv("BTCPAY_STORE_ID"),
                os.getenv("BTCPAY_API_KEY"),
            ]
        )

    @staticmethod
    async def _retry_request(
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, Any] | None = None,
        timeout_sec: int = 30,
    ) -> tuple[int, dict[str, Any]]:
        last_exc: BaseException | None = None
        for attempt in range(3):
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    kwargs: dict[str, Any] = {
                        "timeout": aiohttp.ClientTimeout(total=timeout_sec),
                    }
                    if payload is not None:
                        kwargs["json"] = payload
                    async with session.request(method, url, **kwargs) as response:
                        data = await response.json(content_type=None)
                        if response.status < 400:
                            return response.status, data
                        last_exc = RuntimeError(f"HTTP {response.status}: {data}")
                        if attempt < 2:
                            await asyncio.sleep(2 * (2 ** attempt))
                        continue
            except BaseException as exc:
                last_exc = exc
                if attempt < 2:
                    await asyncio.sleep(2 * (2 ** attempt))
        if last_exc:
            raise last_exc
        raise RuntimeError("BTCPay request failed after 3 attempts")

    @staticmethod
    async def create_invoice(
        *,
        amount: Decimal,
        package_code: str,
        seller_id: int,
        seller_telegram_id: int,
        title: str,
        redirect_url: Optional[str] = None,
    ) -> BTCPayInvoice:
        payload = {
            "amount": str(amount),
            "currency": "USD",
            "metadata": {
                "seller_id": seller_id,
                "seller_telegram_id": seller_telegram_id,
                "package_code": package_code,
                "kind": "seller_security_deposit",
            },
            "checkout": {
                "speedPolicy": "HighSpeed",
                "redirectAutomatically": True,
            },
        }
        if title:
            payload["metadata"]["itemDesc"] = title
        if redirect_url:
            payload["checkout"]["redirectURL"] = redirect_url

        url = f"{BTCPayService._base_url()}/api/v1/stores/{BTCPayService._store_id()}/invoices"
        status, data = await BTCPayService._retry_request(
            "POST",
            url,
            headers=BTCPayService._headers(),
            payload=payload,
        )

        invoice_id = str(data.get("id") or data.get("invoiceId") or "")
        checkout_url = str(data.get("checkoutLink") or data.get("url") or "")
        if not invoice_id or not checkout_url:
            raise RuntimeError(f"BTCPay returned incomplete invoice payload: {data}")
        expiration_minutes = int(data.get("expirationMinutes") or 60)
        return BTCPayInvoice(
            invoice_id=invoice_id,
            checkout_url=checkout_url,
            status=str(data.get("status") or "New"),
            raw_payload=data,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes),
        )

    @staticmethod
    async def fetch_invoice(invoice_id: str) -> dict[str, Any]:
        url = f"{BTCPayService._base_url()}/api/v1/stores/{BTCPayService._store_id()}/invoices/{invoice_id}"
        headers = BTCPayService._headers()
        _, data = await BTCPayService._retry_request(
            "GET", url, headers=headers
        )
        return data

    @staticmethod
    def is_paid_status(status: Optional[str]) -> bool:
        normalized = (status or "").strip().lower()
        return normalized in {"settled", "processing", "confirmed", "complete", "paid"}

    @staticmethod
    def parse_webhook_invoice_id(payload: dict[str, Any]) -> Optional[str]:
        for key in ("invoiceId", "invoice_id", "id"):
            value = payload.get(key)
            if value:
                return str(value)
        nested_invoice = payload.get("invoice") or payload.get("data") or payload.get("payload")
        if isinstance(nested_invoice, dict):
            for key in ("id", "invoiceId", "invoice_id"):
                value = nested_invoice.get(key)
                if value:
                    return str(value)
        return None

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, signature: Optional[str]) -> bool:
        secret = os.getenv("BTCPAY_WEBHOOK_SECRET", "").strip()
        if not secret:
            return False
        if not signature:
            return False
        if "=" in signature:
            _, supplied = signature.split("=", 1)
        else:
            supplied = signature
        digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, supplied.strip())

    @staticmethod
    def decode_webhook_body(raw_body: bytes) -> dict[str, Any]:
        return json.loads(raw_body.decode("utf-8"))
