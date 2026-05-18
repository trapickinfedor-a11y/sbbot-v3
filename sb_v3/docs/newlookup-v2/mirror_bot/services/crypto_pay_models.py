"""
Модели данных для Crypto Pay API
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class CryptoAsset(str, Enum):
    """Поддерживаемые криптовалюты"""
    USDT = "USDT"
    TON = "TON"
    BTC = "BTC"
    ETH = "ETH"
    USDC = "USDC"


class FiatCurrency(str, Enum):
    """Поддерживаемые фиатные валюты"""
    USD = "USD"


class InvoiceStatus(str, Enum):
    """Статусы инвойса"""
    ACTIVE = "active"
    PAID = "paid"
    EXPIRED = "expired"


class CurrencyType(str, Enum):
    """Тип валюты"""
    CRYPTO = "crypto"
    FIAT = "fiat"


class PaidButtonName(str, Enum):
    """Названия кнопок после оплаты"""
    VIEW_ITEM = "viewItem"
    OPEN_CHANNEL = "openChannel"
    OPEN_BOT = "openBot"
    CALLBACK = "callback"


class Invoice(BaseModel):
    """Модель инвойса"""
    invoice_id: int = Field(..., description="Unique ID for this invoice")
    status: InvoiceStatus = Field(..., description="Status of the invoice")
    hash: str = Field(..., description="Hash of the invoice")
    currency_type: Optional[CurrencyType] = Field(None, description="Type of the price")
    asset: Optional[CryptoAsset] = Field(None, description="Cryptocurrency code")
    fiat: Optional[FiatCurrency] = Field(None, description="Fiat currency code")
    amount: str = Field(..., description="Amount of the invoice")
    
    # Accepted assets для fiat invoices
    accepted_assets: Optional[List[CryptoAsset]] = Field(None, description="Assets that can be used for payment")
    
    # Swap information
    swap_to: Optional[CryptoAsset] = Field(None, description="Asset to swap to")
    is_swapped: Optional[bool] = Field(None, description="True if the invoice was swapped")
    swapped_uid: Optional[str] = Field(None, description="Swap UID")
    swapped_to: Optional[CryptoAsset] = Field(None, description="Asset swapped to")
    swapped_rate: Optional[str] = Field(None, description="Swap rate")
    swapped_output: Optional[str] = Field(None, description="Swap output amount")
    swapped_usd_rate: Optional[str] = Field(None, description="Swap USD rate")
    swapped_usd_amount: Optional[str] = Field(None, description="Swap USD amount")
    
    # Payment information
    paid_asset: Optional[CryptoAsset] = Field(None, description="Asset paid by the user")
    paid_amount: Optional[str] = Field(None, description="Amount paid by the user")
    paid_fiat_rate: Optional[str] = Field(None, description="Fiat rate for paid asset")
    paid_usd_rate: Optional[str] = Field(None, description="USD rate for paid asset")
    
    # Fee information
    fee_asset: Optional[CryptoAsset] = Field(None, description="Asset of the fee")
    fee_amount: Optional[str] = Field(None, description="Amount of the fee")
    fee: Optional[str] = Field(None, description="Fee (deprecated)")
    
    # URLs
    bot_invoice_url: str = Field(..., description="URL to pay the invoice via bot")
    mini_app_invoice_url: Optional[str] = Field(None, description="URL to pay via mini app")
    web_app_invoice_url: Optional[str] = Field(None, description="URL to pay via web app")
    pay_url: Optional[str] = Field(None, description="Pay URL (deprecated)")
    
    # Additional fields
    description: Optional[str] = Field(None, description="Description of the invoice")
    created_at: str = Field(..., description="Date created in ISO 8601")
    allow_comments: bool = Field(..., description="True if comments are allowed")
    allow_anonymous: bool = Field(..., description="True if anonymous payment is allowed")
    expiration_date: Optional[str] = Field(None, description="Expiration date in ISO 8601")
    paid_at: Optional[str] = Field(None, description="Date paid in ISO 8601")
    paid_anonymously: Optional[bool] = Field(None, description="True if paid anonymously")
    comment: Optional[str] = Field(None, description="User's comment")
    hidden_message: Optional[str] = Field(None, description="Hidden message")
    payload: Optional[str] = Field(None, description="Payload data")
    paid_btn_name: Optional[PaidButtonName] = Field(None, description="Button name after payment")
    paid_btn_url: Optional[str] = Field(None, description="Button URL after payment")


class Transfer(BaseModel):
    """Модель перевода"""
    transfer_id: int = Field(..., description="Unique ID for this transfer")
    spend_id: Optional[str] = Field(None, description="Unique spend ID")
    user_id: str = Field(..., description="Telegram user ID")
    asset: CryptoAsset = Field(..., description="Cryptocurrency code")
    amount: str = Field(..., description="Amount of the transfer")
    status: Literal["completed"] = Field(..., description="Status of the transfer")
    completed_at: str = Field(..., description="Date completed in ISO 8601")
    comment: Optional[str] = Field(None, description="Comment for the transfer")


class CheckStatus(str, Enum):
    """Статусы чека"""
    ACTIVE = "active"
    ACTIVATED = "activated"


class Check(BaseModel):
    """Модель чека"""
    check_id: int = Field(..., description="Unique ID for this check")
    hash: str = Field(..., description="Hash of the check")
    asset: CryptoAsset = Field(..., description="Cryptocurrency code")
    amount: str = Field(..., description="Amount of the check")
    bot_check_url: str = Field(..., description="URL to activate the check")
    status: CheckStatus = Field(..., description="Status of the check")
    created_at: str = Field(..., description="Date created in ISO 8601")
    activated_at: Optional[str] = Field(None, description="Date activated in ISO 8601")


class Balance(BaseModel):
    """Модель баланса"""
    currency_code: CryptoAsset = Field(..., description="Cryptocurrency code")
    available: str = Field(..., description="Available amount")
    onhold: str = Field(..., description="Amount on hold")


class ExchangeRate(BaseModel):
    """Модель обменного курса"""
    is_valid: bool = Field(..., description="True if rate is up-to-date")
    is_crypto: bool = Field(..., description="True if source is crypto")
    is_fiat: bool = Field(..., description="True if source is fiat")
    source: str = Field(..., description="Source currency")
    target: str = Field(..., description="Target currency")
    rate: str = Field(..., description="Exchange rate")


class AppStats(BaseModel):
    """Модель статистики приложения"""
    volume: float = Field(..., description="Total volume in USD")
    conversion: float = Field(..., description="Conversion rate")
    unique_users_count: int = Field(..., description="Unique users count")
    created_invoice_count: int = Field(..., description="Created invoices count")
    paid_invoice_count: int = Field(..., description="Paid invoices count")
    start_at: str = Field(..., description="Start date in ISO 8601")
    end_at: str = Field(..., description="End date in ISO 8601")


class WebhookUpdate(BaseModel):
    """Модель webhook обновления"""
    update_id: int = Field(..., description="Update ID")
    update_type: Literal["invoice_paid"] = Field(..., description="Update type")
    request_date: str = Field(..., description="Request date in ISO 8601")
    payload: Invoice = Field(..., description="Invoice payload")


class CryptoPayResponse(BaseModel):
    """Базовая модель ответа API"""
    ok: bool = Field(..., description="True if request was successful")
    result: Optional[dict] = Field(None, description="Result data")
    error: Optional[str] = Field(None, description="Error message if ok is False")


class AppInfo(BaseModel):
    """Информация о приложении"""
    app_id: int = Field(..., description="App ID")
    name: str = Field(..., description="App name")
    payment_processing_bot_username: str = Field(..., description="Bot username")

