"""
Модели данных для Cryptomus API
Документация: https://doc.cryptomus.com/
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    """Статусы платежей"""
    PAID = "paid"
    PAID_OVER = "paid_over"
    WRONG_AMOUNT = "wrong_amount"
    PROCESS = "process"
    CONFIRM_CHECK = "confirm_check"
    WRONG_AMOUNT_WAITING = "wrong_amount_waiting"
    CHECK = "check"
    FAIL = "fail"
    CANCEL = "cancel"
    SYSTEM_FAIL = "system_fail"
    REFUND_PROCESS = "refund_process"
    REFUND_FAIL = "refund_fail"
    REFUND_PAID = "refund_paid"
    LOCKED = "locked"


class PayoutStatus(str, Enum):
    """Статусы выплат"""
    PAID = "paid"
    PROCESS = "process"
    CHECK = "check"
    FAIL = "fail"
    CANCEL = "cancel"
    WRONG_AMOUNT = "wrong_amount"


class CryptoNetwork(str, Enum):
    """Криптовалютные сети"""
    BTC = "BTC"
    ETH = "ETH"
    TRX = "TRX"  # Tron (USDT TRC20)
    BNB = "BNB"  # BSC
    TON = "TON"
    MATIC = "MATIC"  # Polygon
    USDT = "USDT"
    USDC = "USDC"


@dataclass
class PaymentInfo:
    """Информация о платеже"""
    uuid: str
    order_id: str
    amount: str
    payment_amount: Optional[str] = None
    payer_amount: Optional[str] = None
    discount_percent: Optional[str] = None
    discount: Optional[str] = None
    payer_currency: Optional[str] = None
    currency: str = ""
    merchant_amount: Optional[str] = None
    network: Optional[str] = None
    address: Optional[str] = None
    from_address: Optional[str] = None
    txid: Optional[str] = None
    payment_status: str = ""
    url: str = ""
    expired_at: Optional[int] = None
    status: str = ""
    is_final: bool = False
    additional_data: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaymentInfo":
        """Создание объекта из словаря"""
        # Извлекаем только те поля, которые есть в аннотациях класса
        filtered_data = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**filtered_data)


@dataclass
class StaticWallet:
    """Статический кошелек"""
    wallet_uuid: str
    uuid: str
    address: str
    network: str
    currency: str
    url: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StaticWallet":
        """Создание объекта из словаря"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class PayoutInfo:
    """Информация о выплате"""
    uuid: str
    amount: str
    currency: str
    network: str
    address: str
    from_address: Optional[str]
    txid: Optional[str]
    status: str
    is_final: bool
    balance: Optional[str]
    payer_currency: Optional[str]
    payer_amount: Optional[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PayoutInfo":
        """Создание объекта из словаря"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class Balance:
    """Баланс мерчанта"""
    merchant_uuid: str
    balance: List[Dict[str, Any]]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Balance":
        """Создание объекта из словаря"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class ServiceInfo:
    """Информация о сервисе (валюте)"""
    network: str
    currency: str
    is_available: bool
    limit: Optional[Dict[str, Any]] = None
    commission: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceInfo":
        """Создание объекта из словаря"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class WebhookUpdate:
    """Webhook обновление"""
    type: str  # "payment:paid", "payment:fail", etc.
    uuid: str
    order_id: str
    amount: str
    payment_amount: Optional[str]
    payer_amount: Optional[str]
    discount_percent: Optional[str]
    discount: Optional[str]
    payer_currency: Optional[str]
    currency: str
    merchant_amount: Optional[str]
    network: Optional[str]
    address: Optional[str]
    from_address: Optional[str]
    txid: Optional[str]
    payment_status: str
    url: str
    expired_at: Optional[int]
    status: str
    is_final: bool
    additional_data: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebhookUpdate":
        """Создание объекта из словаря"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

