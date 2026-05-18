"""
Cryptomus API Client
Документация: https://doc.cryptomus.com/
"""

import hashlib
import hmac
import base64
import aiohttp
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid as uuid_lib

from .cryptomus_models import (
    PaymentInfo, StaticWallet, PayoutInfo, Balance, ServiceInfo,
    WebhookUpdate, PaymentStatus, PayoutStatus, CryptoNetwork
)


class CryptomusError(Exception):
    """Исключение для ошибок Cryptomus API"""
    pass


class CryptomusAPI:
    """
    Клиент для работы с Cryptomus Merchant API
    
    Пример использования:
        api = CryptomusAPI(
            merchant_id="YOUR_MERCHANT_ID",
            payment_key="YOUR_PAYMENT_KEY",
            payout_key="YOUR_PAYOUT_KEY"
        )
        
        # Создание платежа
        payment = await api.create_payment(
            amount="100.50",
            currency="USD",
            order_id="ORDER_12345"
        )
        
        # Получение баланса
        balance = await api.get_balance()
    """
    
    BASE_URL = "https://api.cryptomus.com/v1"
    
    def __init__(
        self,
        merchant_id: str,
        payment_key: str,
        payout_key: Optional[str] = None
    ):
        """
        Инициализация клиента
        
        Args:
            merchant_id: UUID мерчанта из личного кабинета
            payment_key: API ключ для платежей
            payout_key: API ключ для выплат (опционально)
        """
        self.merchant_id = merchant_id
        self.payment_key = payment_key
        self.payout_key = payout_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получение или создание aiohttp сессии"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Закрытие сессии"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    @staticmethod
    def _generate_sign(data: Dict[str, Any], api_key: str) -> str:
        """
        Генерация подписи для запроса
        
        Args:
            data: Данные запроса (JSON)
            api_key: API ключ
        
        Returns:
            MD5 хеш подписи
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # ВАЖНО: Сортируем данные по ключам и кодируем в JSON БЕЗ пробелов и БЕЗ ensure_ascii
        # Согласно официальной документации Cryptomus
        json_data = json.dumps(data, separators=(',', ':'), sort_keys=True)
        
        # Кодируем в base64
        encoded_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
        
        # Создаем подпись: md5(base64(data) + api_key)
        sign_string = encoded_data + api_key
        sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
        
        return sign
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        use_payout_key: bool = False
    ) -> Dict[str, Any]:
        """
        Выполнение HTTP запроса к API
        
        Args:
            method: HTTP метод (POST, GET)
            endpoint: Endpoint API (например, 'payment')
            data: Данные запроса
            use_payout_key: Использовать ключ для выплат
        
        Returns:
            Parsed JSON response
        
        Raises:
            CryptomusError: При ошибке API
        """
        import logging
        logger = logging.getLogger(__name__)
        
        session = await self._get_session()
        url = f"{self.BASE_URL}/{endpoint}"
        
        # Выбираем нужный ключ
        api_key = self.payout_key if use_payout_key else self.payment_key
        
        if not api_key:
            raise CryptomusError("API key not configured")
        
        # Подготавливаем данные
        request_data = data or {}
        
        # ВАЖНО: Сначала сериализуем в JSON строку (с теми же параметрами, что и для подписи!)
        json_string = json.dumps(request_data, separators=(',', ':'), sort_keys=True)
        
        # Генерируем подпись от этой же строки
        sign = self._generate_sign(request_data, api_key)
        
        headers = {
            "merchant": self.merchant_id,
            "sign": sign,
            "Content-Type": "application/json"
        }
        
        # Отладочная информация
        logger.info(f"Cryptomus API Request: {url}")
        logger.info(f"Merchant ID: {self.merchant_id[:8]}...{self.merchant_id[-4:] if len(self.merchant_id) > 12 else ''}")
        logger.info(f"API Key (first 8): {api_key[:8]}...")
        logger.info(f"JSON (first 150 chars): {json_string[:150]}")
        logger.info(f"Generated sign: {sign}")
        
        try:
            # Передаем JSON как строку через data=, а не json=
            async with session.post(url, headers=headers, data=json_string) as response:
                response_data = await response.json()
            
            # Проверяем статус ответа
            if response_data.get("state") != 0:
                error_msg = response_data.get("message", "Unknown error")
                errors = response_data.get("errors", {})
                logger.error(f"Cryptomus API Error: {error_msg}, Full response: {response_data}")
                raise CryptomusError(f"API Error: {error_msg}, Details: {errors}")
            
            return response_data.get("result", {})
        
        except aiohttp.ClientError as e:
            raise CryptomusError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise CryptomusError(f"Invalid JSON response: {str(e)}")
    
    # ============================================
    # PAYMENT METHODS
    # ============================================
    
    async def create_payment(
        self,
        amount: str,
        currency: str,
        order_id: str,
        url_return: Optional[str] = None,
        url_callback: Optional[str] = None,
        network: Optional[str] = None,
        is_payment_multiple: bool = False,
        lifetime: int = 3600,
        to_currency: Optional[str] = None,
        subtract: int = 0,
        accuracy_payment_percent: int = 5,
        additional_data: Optional[str] = None,
        currencies: Optional[List[str]] = None,
        except_currencies: Optional[List[str]] = None,
        course_source: str = "Binance",
        from_referral_code: Optional[str] = None,
        discount_percent: int = 0,
        is_refresh: bool = True
    ) -> PaymentInfo:
        """
        Создание платежа
        
        Args:
            amount: Сумма платежа
            currency: Валюта (USD, EUR, RUB и т.д.)
            order_id: Уникальный ID заказа в вашей системе
            url_return: URL возврата после оплаты
            url_callback: URL для webhook уведомлений
            network: Конкретная сеть для оплаты
            is_payment_multiple: Разрешить множественные платежи
            lifetime: Время жизни платежа в секундах
            to_currency: В какую криптовалюту конвертировать
            subtract: Вычесть комиссию из суммы (0 или 1)
            accuracy_payment_percent: Точность платежа в процентах
            additional_data: Дополнительные данные
            currencies: Список доступных валют для оплаты
            except_currencies: Исключить валюты
            course_source: Источник курса
            from_referral_code: Реферальный код
            discount_percent: Процент скидки
            is_refresh: Автоматическое обновление курса
        
        Returns:
            PaymentInfo объект
        """
        data: Dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "order_id": order_id,
            "is_payment_multiple": is_payment_multiple,
            "lifetime": lifetime,
            "subtract": subtract,
            "accuracy_payment_percent": accuracy_payment_percent,
            "course_source": course_source,
            "discount_percent": discount_percent,
            "is_refresh": is_refresh
        }
        
        if url_return:
            data["url_return"] = url_return
        if url_callback:
            data["url_callback"] = url_callback
        if network:
            data["network"] = network
        if to_currency:
            data["to_currency"] = to_currency
        if additional_data:
            data["additional_data"] = additional_data
        if currencies:
            data["currencies"] = currencies
        if except_currencies:
            data["except_currencies"] = except_currencies
        if from_referral_code:
            data["from_referral_code"] = from_referral_code
        
        result = await self._request("POST", "payment", data)
        return PaymentInfo.from_dict(result)
    
    async def create_static_wallet(
        self,
        currency: str,
        network: str,
        order_id: str,
        url_callback: Optional[str] = None,
        from_referral_code: Optional[str] = None
    ) -> StaticWallet:
        """
        Создание статического кошелька
        
        Args:
            currency: Валюта кошелька
            network: Сеть блокчейна
            order_id: Уникальный ID заказа
            url_callback: URL для webhook
            from_referral_code: Реферальный код
        
        Returns:
            StaticWallet объект
        """
        data: Dict[str, Any] = {
            "currency": currency,
            "network": network,
            "order_id": order_id
        }
        
        if url_callback:
            data["url_callback"] = url_callback
        if from_referral_code:
            data["from_referral_code"] = from_referral_code
        
        result = await self._request("POST", "wallet", data)
        return StaticWallet.from_dict(result)
    
    async def get_payment_info(self, uuid: Optional[str] = None, order_id: Optional[str] = None) -> PaymentInfo:
        """
        Получение информации о платеже
        
        Args:
            uuid: UUID платежа в системе Cryptomus
            order_id: ID заказа в вашей системе
        
        Returns:
            PaymentInfo объект
        """
        if not uuid and not order_id:
            raise ValueError("Either uuid or order_id must be provided")
        
        data: Dict[str, Any] = {}
        if uuid:
            data["uuid"] = uuid
        if order_id:
            data["order_id"] = order_id
        
        result = await self._request("POST", "payment/info", data)
        return PaymentInfo.from_dict(result)
    
    async def get_payment_history(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получение истории платежей
        
        Args:
            date_from: Дата начала (YYYY-MM-DD)
            date_to: Дата окончания (YYYY-MM-DD)
            cursor: Курсор для пагинации
        
        Returns:
            Dict с items (список платежей) и paginate (данные пагинации)
        """
        data: Dict[str, Any] = {}
        if date_from:
            data["date_from"] = date_from
        if date_to:
            data["date_to"] = date_to
        if cursor:
            data["cursor"] = cursor
        
        result = await self._request("POST", "payment/list", data)
        
        # Преобразуем items в PaymentInfo
        items = [PaymentInfo.from_dict(item) for item in result.get("items", [])]
        
        return {
            "items": items,
            "paginate": result.get("paginate", {})
        }
    
    async def refund_payment(
        self,
        address: str,
        is_subtract: bool = True,
        uuid: Optional[str] = None,
        order_id: Optional[str] = None
    ) -> PaymentInfo:
        """
        Возврат платежа
        
        Args:
            address: Адрес для возврата
            is_subtract: Вычесть комиссию из возврата
            uuid: UUID платежа
            order_id: ID заказа
        
        Returns:
            PaymentInfo объект
        """
        if not uuid and not order_id:
            raise ValueError("Either uuid or order_id must be provided")
        
        data: Dict[str, Any] = {
            "address": address,
            "is_subtract": is_subtract
        }
        
        if uuid:
            data["uuid"] = uuid
        if order_id:
            data["order_id"] = order_id
        
        result = await self._request("POST", "payment/refund", data)
        return PaymentInfo.from_dict(result)
    
    async def resend_webhook(self, uuid: Optional[str] = None, order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Повторная отправка webhook
        
        Args:
            uuid: UUID платежа
            order_id: ID заказа
        
        Returns:
            Dict с результатом
        """
        if not uuid and not order_id:
            raise ValueError("Either uuid or order_id must be provided")
        
        data: Dict[str, Any] = {}
        if uuid:
            data["uuid"] = uuid
        if order_id:
            data["order_id"] = order_id
        
        return await self._request("POST", "payment/resend", data)
    
    async def get_services(self) -> List[ServiceInfo]:
        """
        Получение списка доступных сервисов (валют и сетей)
        
        Returns:
            Список ServiceInfo объектов
        """
        result = await self._request("POST", "payment/services", {})
        return [ServiceInfo.from_dict(item) for item in result]
    
    # ============================================
    # PAYOUT METHODS
    # ============================================
    
    async def create_payout(
        self,
        amount: str,
        currency: str,
        network: str,
        address: str,
        order_id: str,
        url_callback: Optional[str] = None,
        is_subtract: bool = True,
        from_referral_code: Optional[str] = None
    ) -> PayoutInfo:
        """
        Создание выплаты
        
        Args:
            amount: Сумма выплаты
            currency: Валюта
            network: Сеть блокчейна
            address: Адрес получателя
            order_id: Уникальный ID заказа
            url_callback: URL для webhook
            is_subtract: Вычесть комиссию из суммы
            from_referral_code: Реферальный код
        
        Returns:
            PayoutInfo объект
        """
        data: Dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "network": network,
            "address": address,
            "order_id": order_id,
            "is_subtract": is_subtract
        }
        
        if url_callback:
            data["url_callback"] = url_callback
        if from_referral_code:
            data["from_referral_code"] = from_referral_code
        
        result = await self._request("POST", "payout", data, use_payout_key=True)
        return PayoutInfo.from_dict(result)
    
    async def get_payout_info(self, uuid: str) -> PayoutInfo:
        """
        Получение информации о выплате
        
        Args:
            uuid: UUID выплаты
        
        Returns:
            PayoutInfo объект
        """
        data = {"uuid": uuid}
        result = await self._request("POST", "payout/info", data, use_payout_key=True)
        return PayoutInfo.from_dict(result)
    
    async def get_payout_history(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получение истории выплат
        
        Args:
            date_from: Дата начала (YYYY-MM-DD)
            date_to: Дата окончания (YYYY-MM-DD)
            cursor: Курсор для пагинации
        
        Returns:
            Dict с items (список выплат) и paginate (данные пагинации)
        """
        data: Dict[str, Any] = {}
        if date_from:
            data["date_from"] = date_from
        if date_to:
            data["date_to"] = date_to
        if cursor:
            data["cursor"] = cursor
        
        result = await self._request("POST", "payout/list", data, use_payout_key=True)
        
        # Преобразуем items в PayoutInfo
        items = [PayoutInfo.from_dict(item) for item in result.get("items", [])]
        
        return {
            "items": items,
            "paginate": result.get("paginate", {})
        }
    
    async def get_payout_services(self) -> List[ServiceInfo]:
        """
        Получение списка доступных сервисов для выплат
        
        Returns:
            Список ServiceInfo объектов
        """
        result = await self._request("POST", "payout/services", {}, use_payout_key=True)
        return [ServiceInfo.from_dict(item) for item in result]
    
    # ============================================
    # BALANCE
    # ============================================
    
    async def get_balance(self) -> Balance:
        """
        Получение баланса мерчанта
        
        Returns:
            Balance объект
        """
        result = await self._request("POST", "balance", {})
        return Balance.from_dict(result)
    
    # ============================================
    # WEBHOOK VERIFICATION
    # ============================================
    
    @staticmethod
    def verify_webhook_signature(
        data: Dict[str, Any],
        signature: str,
        api_key: str
    ) -> bool:
        """
        Проверка подписи webhook запроса
        
        Args:
            data: Данные webhook (JSON)
            signature: Значение заголовка sign
            api_key: API ключ для проверки
        
        Returns:
            True если подпись валидна
        """
        # Генерируем подпись тем же методом
        expected_sign = CryptomusAPI._generate_sign(data, api_key)
        
        # Сравниваем с полученной подписью
        return hmac.compare_digest(expected_sign, signature)
    
    # ============================================
    # HELPER МЕТОДЫ
    # ============================================
    
    async def create_simple_payment(
        self,
        amount_usd: float,
        order_id: str,
        url_callback: Optional[str] = None
    ) -> PaymentInfo:
        """
        Создание простого платежа в USD
        
        Args:
            amount_usd: Сумма в USD
            order_id: ID заказа
            url_callback: URL для webhook
        
        Returns:
            PaymentInfo объект
        """
        return await self.create_payment(
            amount=str(amount_usd),
            currency="USD",
            order_id=order_id,
            url_callback=url_callback,
            lifetime=3600,  # 1 час
            currencies=["USDT", "BTC", "ETH", "TON", "LTC", "TRX"]  # Популярные валюты
        )
    
    async def check_payment_status(self, order_id: str) -> Optional[str]:
        """
        Проверка статуса платежа по order_id
        
        Args:
            order_id: ID заказа
        
        Returns:
            Статус платежа или None
        """
        try:
            payment = await self.get_payment_info(order_id=order_id)
            return payment.status
        except CryptomusError:
            return None


# ============================================
# CONTEXT MANAGER SUPPORT
# ============================================

class CryptomusAPIContext(CryptomusAPI):
    """Версия клиента с поддержкой async context manager"""
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

