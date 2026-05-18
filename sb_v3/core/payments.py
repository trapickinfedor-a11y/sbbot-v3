"""
payments.py — Payment integrations: CryptoBot (Telegram) and Heleket (crypto)

CryptoBot: https://t.me/CryptoBot — Telegram-native crypto payments
Heleket:   https://heleket.com    — Crypto payment gateway

Usage:
    from payments import CryptoBotPayment, HeleketPayment
"""

import aiohttp
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Optional, Dict, Any

logger = logging.getLogger("sbbot.payments")

# ─── Supported deposit amounts ────────────────────────────────────────────────
DEPOSIT_AMOUNTS = [5, 10, 20, 50, 100, 200]

# ─── CryptoBot ────────────────────────────────────────────────────────────────
CRYPTOBOT_API = "https://pay.crypt.bot/api"

# Supported assets in CryptoBot
CRYPTOBOT_ASSETS = ["USDT", "TON", "BTC", "ETH", "LTC", "BNB", "TRX", "USDC"]


class CryptoBotPayment:
    """
    CryptoBot payment integration.
    Docs: https://help.crypt.bot/crypto-pay-api
    """

    def __init__(self, token: str):
        self.token = token

    def _headers(self) -> Dict[str, str]:
        return {
            "Crypto-Pay-API-Token": self.token,
            "Content-Type": "application/json",
        }

    async def create_invoice(
        self,
        amount: float,
        asset: str = "USDT",
        description: str = "Balance top-up",
        payload: str = "",
        expires_in: int = 3600,
    ) -> Optional[Dict]:
        """
        Create a payment invoice.
        Returns: {invoice_id, pay_url, amount, asset, status, ...}
        """
        data = {
            "asset": asset,
            "amount": str(round(amount, 2)),
            "description": description,
            "payload": payload,
            "expires_in": expires_in,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{CRYPTOBOT_API}/createInvoice",
                    headers=self._headers(),
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    result = await resp.json()
                    if result.get("ok"):
                        inv = result["result"]
                        return {
                            "invoice_id": str(inv["invoice_id"]),
                            "pay_url": inv["pay_url"],
                            "amount": float(inv["amount"]),
                            "asset": inv["asset"],
                            "status": inv["status"],
                            "created_at": inv.get("created_at"),
                        }
                    else:
                        logger.error(f"[CryptoBot] createInvoice error: {result}")
                        return None
        except Exception as e:
            logger.error(f"[CryptoBot] createInvoice exception: {e}")
            return None

    async def get_invoice(self, invoice_id: str) -> Optional[Dict]:
        """Check invoice status."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{CRYPTOBOT_API}/getInvoices",
                    headers=self._headers(),
                    params={"invoice_ids": invoice_id},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    result = await resp.json()
                    if result.get("ok"):
                        items = result["result"].get("items", [])
                        if items:
                            inv = items[0]
                            return {
                                "invoice_id": str(inv["invoice_id"]),
                                "status": inv["status"],  # active | paid | expired
                                "amount": float(inv["amount"]),
                                "asset": inv["asset"],
                                "paid_at": inv.get("paid_at"),
                                "pay_url": inv.get("pay_url"),
                            }
            return None
        except Exception as e:
            logger.error(f"[CryptoBot] getInvoice exception: {e}")
            return None

    async def get_balance(self) -> Optional[Dict[str, float]]:
        """Get CryptoBot app balance."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{CRYPTOBOT_API}/getBalance",
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    result = await resp.json()
                    if result.get("ok"):
                        return {
                            item["currency_code"]: float(item["available"])
                            for item in result["result"]
                        }
            return None
        except Exception as e:
            logger.error(f"[CryptoBot] getBalance exception: {e}")
            return None

    def verify_webhook(self, token: str, body: str, signature: str) -> bool:
        """Verify CryptoBot webhook signature."""
        secret = hashlib.sha256(token.encode()).digest()
        expected = hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


# ─── Heleket ─────────────────────────────────────────────────────────────────
HELEKET_API = "https://api.heleket.com/v1"

# Supported currencies in Heleket
HELEKET_CURRENCIES = [
    "USDT", "BTC", "ETH", "LTC", "TRX", "BNB", "USDC",
    "DOGE", "XRP", "SOL", "MATIC", "TON",
]


class HeleketPayment:
    """
    Heleket crypto payment gateway integration.
    Docs: https://heleket.com/api-docs
    """

    def __init__(self, api_key: str, merchant_id: str):
        self.api_key = api_key
        self.merchant_id = merchant_id

    def _headers(self) -> Dict[str, str]:
        return {
            "merchant": self.merchant_id,
            "sign": self.api_key,
            "Content-Type": "application/json",
        }

    def _sign(self, data: Dict) -> str:
        """Generate HMAC-MD5 signature for Heleket request."""
        sorted_data = dict(sorted(data.items()))
        data_str = json.dumps(sorted_data, separators=(',', ':'), ensure_ascii=False)
        signature = hmac.new(
            self.api_key.encode(),
            data_str.encode(),
            hashlib.md5
        ).hexdigest()
        return signature

    async def create_invoice(
        self,
        amount: float,
        currency: str = "USDT",
        order_id: str = None,
        description: str = "Balance top-up",
        url_callback: str = None,
        url_return: str = None,
    ) -> Optional[Dict]:
        """
        Create a Heleket payment invoice.
        Returns: {uuid, url, amount, currency, status, ...}
        """
        if not order_id:
            order_id = str(uuid.uuid4())

        data = {
            "amount": str(round(amount, 2)),
            "currency": currency,
            "order_id": order_id,
            "description": description,
        }
        if url_callback:
            data["url_callback"] = url_callback
        if url_return:
            data["url_return"] = url_return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{HELEKET_API}/payment",
                    headers=self._headers(),
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    result = await resp.json()
                    if result.get("state") == 0:
                        r = result.get("result", {})
                        return {
                            "invoice_id": r.get("uuid") or order_id,
                            "pay_url": r.get("url"),
                            "amount": float(r.get("amount", amount)),
                            "currency": r.get("currency", currency),
                            "status": r.get("payment_status", "pending"),
                            "order_id": order_id,
                        }
                    else:
                        logger.error(f"[Heleket] createInvoice error: {result}")
                        return None
        except Exception as e:
            logger.error(f"[Heleket] createInvoice exception: {e}")
            return None

    async def get_invoice(self, invoice_id: str) -> Optional[Dict]:
        """Check Heleket invoice status."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{HELEKET_API}/payment/{invoice_id}",
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    result = await resp.json()
                    if result.get("state") == 0:
                        r = result.get("result", {})
                        return {
                            "invoice_id": r.get("uuid", invoice_id),
                            "status": r.get("payment_status", "pending"),
                            "amount": float(r.get("amount", 0)),
                            "currency": r.get("currency"),
                            "pay_url": r.get("url"),
                        }
            return None
        except Exception as e:
            logger.error(f"[Heleket] getInvoice exception: {e}")
            return None

    def verify_webhook(self, body: Dict, signature: str) -> bool:
        """Verify Heleket webhook signature."""
        expected = self._sign(body)
        return hmac.compare_digest(expected, signature)


# ─── BTCPayServer ─────────────────────────────────────────────────────────────
BTCPAY_CRYPTO = ["BTC", "USDT", "USDC", "ETH", "LTC", "DOGE"]
BTCPAY_DEFAULT_PAYMENT_SPEED = "MediumTolerance"


class BTCPayPayment:
    """
    BTCPayServer payment integration.
    Docs: https://docs.btcpayserver.org/API/Greenfield/v1/
    """

    def __init__(self, base_url: str, api_key: str, store_id: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.store_id = store_id

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"token {self.api_key}",
        }

    async def create_invoice(
        self,
        amount: float,
        currency: str = "USD",
        description: str = "Balance top-up",
        metadata: Dict[str, Any] = None,
    ) -> Optional[Dict]:
        """
        Create BTCPayServer invoice via Greenfield API.
        Returns: {invoice_id, pay_url, status, amount, currency}
        """
        data = {
            "amount": str(round(amount, 2)),
            "currency": currency,
            "metadata": metadata or {},
            "checkout": {
                "paymentMethods": [],
                "speedPolicy": BTCPAY_DEFAULT_PAYMENT_SPEED,
                "defaultPaymentMethod": "",
            },
        }
        if description:
            data["metadata"]["buyerName"] = description
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/stores/{self.store_id}/invoices",
                    headers=self._headers(),
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return {
                            "invoice_id": result["id"],
                            "pay_url": f"{self.base_url}/invoice?id={result['id']}",
                            "amount": float(result.get("amount", amount)),
                            "currency": result.get("currency", currency),
                            "status": result.get("status", "pending"),
                            "created_at": result.get("createdTime"),
                            "expires_at": result.get("expirationTime"),
                            "monitoring": result.get("monitoring"),
                        }
                    else:
                        body = await resp.text()
                        logger.error(f"[BTCPay] createinvoice error {resp.status}: {body}")
                        return None
        except Exception as e:
            logger.error(f"[BTCPay] createinvoice exception: {e}")
            return None

    async def get_invoice(self, invoice_id: str) -> Optional[Dict]:
        """Check invoice status."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/stores/{self.store_id}/invoices/{invoice_id}",
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return {
                            "invoice_id": result["id"],
                            "status": result.get("status", "pending"),
                            "payment_status": result.get("paymentStatus", "pending"),
                            "amount": float(result.get("amount", 0)),
                            "currency": result.get("currency"),
                            "pay_url": f"{self.base_url}/invoice?id={result['id']}",
                            "paid_at": result.get("monitoringExpiration"),
                        }
                    return None
        except Exception as e:
            logger.error(f"[BTCPay] get_invoice exception: {e}")
            return None


# ─── Payment manager ─────────────────────────────────────────────────────────

class PaymentManager:
    """
    Unified payment manager — wraps CryptoBot, Heleket, BTCPayServer.
    """

    def __init__(self):
        self._cryptobot: Optional[CryptoBotPayment] = None
        self._heleket: Optional[HeleketPayment] = None
        self._btcpay: Optional[BTCPayPayment] = None

    def setup_cryptobot(self, token: str):
        if token:
            self._cryptobot = CryptoBotPayment(token)
            logger.info("[Payments] CryptoBot configured")

    def setup_heleket(self, api_key: str, merchant_id: str):
        if api_key and merchant_id:
            self._heleket = HeleketPayment(api_key, merchant_id)
            logger.info("[Payments] Heleket configured")

    def setup_btcpay(self, base_url: str, api_key: str, store_id: str):
        if base_url and api_key and store_id:
            self._btcpay = BTCPayPayment(base_url, api_key, store_id)
            logger.info(f"[Payments] BTCPayServer configured: {base_url}")

    @property
    def has_cryptobot(self) -> bool:
        return self._cryptobot is not None

    @property
    def has_heleket(self) -> bool:
        return self._heleket is not None

    @property
    def has_btcpay(self) -> bool:
        return self._btcpay is not None

    @property
    def available_providers(self) -> list[str]:
        providers = []
        if self.has_cryptobot:
            providers.append("cryptobot")
        if self.has_heleket:
            providers.append("heleket")
        if self.has_btcpay:
            providers.append("btcpay")
        return providers

    async def create_invoice(
        self,
        provider: str,
        amount: float,
        user_id: int,
        currency: str = "USDT",
        description: str = "Balance top-up",
    ) -> Optional[Dict]:
        """Create invoice via specified provider."""
        payload = f"uid:{user_id}:ts:{int(time.time())}"

        if provider == "cryptobot" and self._cryptobot:
            return await self._cryptobot.create_invoice(
                amount=amount,
                asset=currency,
                description=description,
                payload=payload,
            )
        elif provider == "heleket" and self._heleket:
            order_id = f"uid{user_id}_{int(time.time())}"
            return await self._heleket.create_invoice(
                amount=amount,
                currency=currency,
                order_id=order_id,
                description=description,
            )
        elif provider == "btcpay" and self._btcpay:
            metadata = {"userId": str(user_id), "orderId": f"uid{user_id}_{int(time.time())}"}
            return await self._btcpay.create_invoice(
                amount=amount,
                currency=currency,
                description=description,
                metadata=metadata,
            )
        return None

    async def check_invoice(self, provider: str, invoice_id: str) -> Optional[Dict]:
        """Check invoice status."""
        if provider == "cryptobot" and self._cryptobot:
            return await self._cryptobot.get_invoice(invoice_id)
        elif provider == "heleket" and self._heleket:
            return await self._heleket.get_invoice(invoice_id)
        elif provider == "btcpay" and self._btcpay:
            return await self._btcpay.get_invoice(invoice_id)
        return None


# Singleton
payment_manager = PaymentManager()


# ─── Keyboard helpers ─────────────────────────────────────────────────────────

def get_deposit_keyboard(provider: str = "cryptobot"):
    """
    Returns list of (label, callback_data) for deposit amount buttons.
    Used in bot.py to build InlineKeyboard.
    """
    buttons = []
    for amount in DEPOSIT_AMOUNTS:
        buttons.append((f"💵 ${amount}", f"deposit:{provider}:{amount}:USDT"))
    return buttons


def get_provider_keyboard(available: list[str]):
    """Returns provider selection buttons."""
    labels = {
        "cryptobot": "🤖 CryptoBot (Telegram)",
        "heleket": "🔐 Heleket (Crypto)",
    }
    return [(labels[p], f"provider:{p}") for p in available if p in labels]
