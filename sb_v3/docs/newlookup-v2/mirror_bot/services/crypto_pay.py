"""
Crypto Pay API Client
Документация: https://help.send.tg/en/articles/10279948-crypto-pay-api
"""

import hashlib
import hmac
import aiohttp
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from .crypto_pay_models import (
    Invoice, Transfer, Check, Balance, ExchangeRate, AppStats,
    CryptoAsset, FiatCurrency, PaidButtonName, AppInfo
)


class CryptoPayError(Exception):
    """Исключение для ошибок Crypto Pay API"""
    pass


class CryptoPayAPI:
    """
    Клиент для работы с Crypto Pay API
    
    Пример использования:
        api = CryptoPayAPI(token="YOUR_API_TOKEN", testnet=False)
        
        # Создание инвойса
        invoice = await api.create_invoice(
            asset=CryptoAsset.USDT,
            amount="10.50",
            description="Payment for service"
        )
        
        # Получение баланса
        balances = await api.get_balance()
    """
    
    def __init__(self, token: str, testnet: bool = False):
        """
        Инициализация клиента
        
        Args:
            token: API токен из @CryptoBot или @CryptoTestnetBot
            testnet: True для использования тестовой сети
        """
        self.token = token
        self.testnet = testnet
        
        if testnet:
            self.base_url = "https://testnet-pay.crypt.bot/api"
        else:
            self.base_url = "https://pay.crypt.bot/api"
        
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
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Выполнение HTTP запроса к API
        
        Args:
            method: HTTP метод (GET, POST)
            endpoint: Endpoint API (например, 'getMe')
            params: Параметры запроса
        
        Returns:
            Parsed JSON response
        
        Raises:
            CryptoPayError: При ошибке API
        """
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}"
        
        headers = {
            "Crypto-Pay-API-Token": self.token,
            "Content-Type": "application/json"
        }
        
        try:
            if method.upper() == "GET":
                async with session.get(url, headers=headers, params=params) as response:
                    data = await response.json()
            else:  # POST
                async with session.post(url, headers=headers, json=params) as response:
                    data = await response.json()
            
            if not data.get("ok", False):
                error_msg = data.get("error", "Unknown error")
                raise CryptoPayError(f"API Error: {error_msg}")
            
            return data.get("result", {})
        
        except aiohttp.ClientError as e:
            raise CryptoPayError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise CryptoPayError(f"Invalid JSON response: {str(e)}")
    
    # ============================================
    # API МЕТОДЫ
    # ============================================
    
    async def get_me(self) -> AppInfo:
        """
        Получение информации о приложении
        
        Returns:
            AppInfo с данными приложения
        """
        result = await self._request("GET", "getMe")
        return AppInfo(**result)
    
    async def create_invoice(
        self,
        amount: str,
        currency_type: str = "crypto",
        asset: Optional[CryptoAsset] = None,
        fiat: Optional[FiatCurrency] = None,
        accepted_assets: Optional[List[CryptoAsset]] = None,
        description: Optional[str] = None,
        hidden_message: Optional[str] = None,
        paid_btn_name: Optional[PaidButtonName] = None,
        paid_btn_url: Optional[str] = None,
        payload: Optional[str] = None,
        allow_comments: bool = True,
        allow_anonymous: bool = True,
        expires_in: Optional[int] = None,
        swap_to: Optional[CryptoAsset] = None
    ) -> Invoice:
        """
        Создание нового инвойса
        
        Args:
            amount: Сумма в виде строки (например, "10.50")
            currency_type: "crypto" или "fiat"
            asset: Криптовалюта (обязательна если currency_type="crypto")
            fiat: Фиатная валюта (обязательна если currency_type="fiat")
            accepted_assets: Список принимаемых криптовалют (для fiat)
            description: Описание платежа
            hidden_message: Скрытое сообщение (показывается после оплаты)
            paid_btn_name: Название кнопки после оплаты
            paid_btn_url: URL кнопки после оплаты
            payload: Дополнительные данные (до 4096 байт)
            allow_comments: Разрешить комментарии
            allow_anonymous: Разрешить анонимную оплату
            expires_in: Время жизни инвойса в секундах
            swap_to: Криптовалюта для свапа
        
        Returns:
            Invoice объект
        """
        params: Dict[str, Any] = {
            "amount": amount,
            "currency_type": currency_type,
            "allow_comments": allow_comments,
            "allow_anonymous": allow_anonymous
        }
        
        if currency_type == "crypto" and asset:
            params["asset"] = asset.value if isinstance(asset, CryptoAsset) else asset
        elif currency_type == "fiat" and fiat:
            params["fiat"] = fiat.value if isinstance(fiat, FiatCurrency) else fiat
        
        if accepted_assets:
            assets_str = ",".join([
                a.value if isinstance(a, CryptoAsset) else a 
                for a in accepted_assets
            ])
            params["accepted_assets"] = assets_str
        
        if description:
            params["description"] = description
        if hidden_message:
            params["hidden_message"] = hidden_message
        if paid_btn_name:
            params["paid_btn_name"] = paid_btn_name.value if isinstance(paid_btn_name, PaidButtonName) else paid_btn_name
        if paid_btn_url:
            params["paid_btn_url"] = paid_btn_url
        if payload:
            params["payload"] = payload
        if expires_in:
            params["expires_in"] = expires_in
        if swap_to:
            params["swap_to"] = swap_to.value if isinstance(swap_to, CryptoAsset) else swap_to
        
        result = await self._request("POST", "createInvoice", params)
        return Invoice(**result)
    
    async def delete_invoice(self, invoice_id: int) -> bool:
        """
        Удаление инвойса
        
        Args:
            invoice_id: ID инвойса
        
        Returns:
            True если успешно удален
        """
        params = {"invoice_id": invoice_id}
        result = await self._request("POST", "deleteInvoice", params)
        return result
    
    async def get_invoices(
        self,
        asset: Optional[CryptoAsset] = None,
        fiat: Optional[FiatCurrency] = None,
        invoice_ids: Optional[List[int]] = None,
        status: Optional[str] = None,
        offset: int = 0,
        count: int = 100
    ) -> List[Invoice]:
        """
        Получение списка инвойсов
        
        Args:
            asset: Фильтр по криптовалюте
            fiat: Фильтр по фиатной валюте
            invoice_ids: Список ID инвойсов
            status: Фильтр по статусу ("active", "paid", "expired")
            offset: Смещение для пагинации
            count: Количество записей (макс 1000)
        
        Returns:
            Список Invoice объектов
        """
        params: Dict[str, Any] = {
            "offset": offset,
            "count": min(count, 1000)
        }
        
        if asset:
            params["asset"] = asset.value if isinstance(asset, CryptoAsset) else asset
        if fiat:
            params["fiat"] = fiat.value if isinstance(fiat, FiatCurrency) else fiat
        if invoice_ids:
            params["invoice_ids"] = ",".join(map(str, invoice_ids))
        if status:
            params["status"] = status
        
        result = await self._request("GET", "getInvoices", params)
        
        items = result.get("items", [])
        return [Invoice(**item) for item in items]
    
    async def transfer(
        self,
        user_id: int,
        asset: CryptoAsset,
        amount: str,
        spend_id: Optional[str] = None,
        comment: Optional[str] = None,
        disable_send_notification: bool = False
    ) -> Transfer:
        """
        Перевод средств пользователю
        
        Args:
            user_id: Telegram User ID получателя
            asset: Криптовалюта
            amount: Сумма для перевода
            spend_id: Уникальный ID для предотвращения дублирования
            comment: Комментарий к переводу
            disable_send_notification: Отключить уведомление
        
        Returns:
            Transfer объект
        """
        params: Dict[str, Any] = {
            "user_id": user_id,
            "asset": asset.value if isinstance(asset, CryptoAsset) else asset,
            "amount": amount,
            "disable_send_notification": disable_send_notification
        }
        
        if spend_id:
            params["spend_id"] = spend_id
        if comment:
            params["comment"] = comment
        
        result = await self._request("POST", "transfer", params)
        return Transfer(**result)
    
    async def get_transfers(
        self,
        asset: Optional[CryptoAsset] = None,
        transfer_ids: Optional[List[int]] = None,
        spend_id: Optional[str] = None,
        offset: int = 0,
        count: int = 100
    ) -> List[Transfer]:
        """
        Получение списка переводов
        
        Args:
            asset: Фильтр по криптовалюте
            transfer_ids: Список ID переводов
            spend_id: Фильтр по spend_id
            offset: Смещение для пагинации
            count: Количество записей (макс 1000)
        
        Returns:
            Список Transfer объектов
        """
        params: Dict[str, Any] = {
            "offset": offset,
            "count": min(count, 1000)
        }
        
        if asset:
            params["asset"] = asset.value if isinstance(asset, CryptoAsset) else asset
        if transfer_ids:
            params["transfer_ids"] = ",".join(map(str, transfer_ids))
        if spend_id:
            params["spend_id"] = spend_id
        
        result = await self._request("GET", "getTransfers", params)
        
        items = result.get("items", [])
        return [Transfer(**item) for item in items]
    
    async def create_check(
        self,
        asset: CryptoAsset,
        amount: str,
        pin_to_user_id: Optional[int] = None,
        pin_to_username: Optional[str] = None
    ) -> Check:
        """
        Создание чека
        
        Args:
            asset: Криптовалюта
            amount: Сумма чека
            pin_to_user_id: Привязать к конкретному пользователю по ID
            pin_to_username: Привязать к конкретному пользователю по username
        
        Returns:
            Check объект
        """
        params: Dict[str, Any] = {
            "asset": asset.value if isinstance(asset, CryptoAsset) else asset,
            "amount": amount
        }
        
        if pin_to_user_id:
            params["pin_to_user_id"] = pin_to_user_id
        if pin_to_username:
            params["pin_to_username"] = pin_to_username
        
        result = await self._request("POST", "createCheck", params)
        return Check(**result)
    
    async def delete_check(self, check_id: int) -> bool:
        """
        Удаление чека
        
        Args:
            check_id: ID чека
        
        Returns:
            True если успешно удален
        """
        params = {"check_id": check_id}
        result = await self._request("POST", "deleteCheck", params)
        return result
    
    async def get_checks(
        self,
        asset: Optional[CryptoAsset] = None,
        check_ids: Optional[List[int]] = None,
        status: Optional[str] = None,
        offset: int = 0,
        count: int = 100
    ) -> List[Check]:
        """
        Получение списка чеков
        
        Args:
            asset: Фильтр по криптовалюте
            check_ids: Список ID чеков
            status: Фильтр по статусу ("active", "activated")
            offset: Смещение для пагинации
            count: Количество записей (макс 1000)
        
        Returns:
            Список Check объектов
        """
        params: Dict[str, Any] = {
            "offset": offset,
            "count": min(count, 1000)
        }
        
        if asset:
            params["asset"] = asset.value if isinstance(asset, CryptoAsset) else asset
        if check_ids:
            params["check_ids"] = ",".join(map(str, check_ids))
        if status:
            params["status"] = status
        
        result = await self._request("GET", "getChecks", params)
        
        items = result.get("items", [])
        return [Check(**item) for item in items]
    
    async def get_balance(self) -> List[Balance]:
        """
        Получение баланса по всем валютам
        
        Returns:
            Список Balance объектов
        """
        result = await self._request("GET", "getBalance")
        return [Balance(**item) for item in result]
    
    async def get_exchange_rates(self) -> List[ExchangeRate]:
        """
        Получение курсов обмена
        
        Returns:
            Список ExchangeRate объектов
        """
        result = await self._request("GET", "getExchangeRates")
        return [ExchangeRate(**item) for item in result]
    
    async def get_currencies(self) -> List[Dict[str, Any]]:
        """
        Получение списка поддерживаемых валют
        
        Returns:
            Список валют с информацией
        """
        result = await self._request("GET", "getCurrencies")
        return result
    
    async def get_stats(
        self,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None
    ) -> AppStats:
        """
        Получение статистики приложения
        
        Args:
            start_at: Начало периода (по умолчанию 30 дней назад)
            end_at: Конец периода (по умолчанию текущая дата)
        
        Returns:
            AppStats объект
        """
        params: Dict[str, Any] = {}
        
        if start_at:
            params["start_at"] = start_at.isoformat()
        if end_at:
            params["end_at"] = end_at.isoformat()
        
        result = await self._request("GET", "getStats", params)
        return AppStats(**result)
    
    # ============================================
    # WEBHOOK VERIFICATION
    # ============================================
    
    @staticmethod
    def verify_webhook_signature(
        token: str,
        body: str,
        signature: str
    ) -> bool:
        """
        Проверка подписи webhook запроса
        
        Args:
            token: API токен
            body: Тело запроса (JSON строка)
            signature: Значение заголовка crypto-pay-api-signature
        
        Returns:
            True если подпись валидна
        """
        # Создаем секретный ключ из токена
        secret = hashlib.sha256(token.encode()).digest()
        
        # Вычисляем HMAC-SHA256
        hmac_hash = hmac.new(
            secret,
            body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Сравниваем с полученной подписью
        return hmac.compare_digest(hmac_hash, signature)
    
    # ============================================
    # HELPER МЕТОДЫ
    # ============================================
    
    async def create_simple_invoice(
        self,
        amount_usd: float,
        description: str = "Payment"
    ) -> Invoice:
        """
        Создание простого инвойса в USD (принимает любую крипту)
        
        Args:
            amount_usd: Сумма в USD
            description: Описание платежа
        
        Returns:
            Invoice объект
        """
        return await self.create_invoice(
            amount=str(amount_usd),
            currency_type="fiat",
            fiat=FiatCurrency.USD,
            description=description,
            accepted_assets=list(CryptoAsset)
        )
    
    async def get_invoice_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """
        Получение конкретного инвойса по ID
        
        Args:
            invoice_id: ID инвойса
        
        Returns:
            Invoice объект или None
        """
        invoices = await self.get_invoices(invoice_ids=[invoice_id])
        return invoices[0] if invoices else None
    
    async def wait_for_payment(
        self,
        invoice_id: int,
        timeout: int = 3600,
        check_interval: int = 5
    ) -> Optional[Invoice]:
        """
        Ожидание оплаты инвойса (polling)
        
        Args:
            invoice_id: ID инвойса
            timeout: Максимальное время ожидания в секундах
            check_interval: Интервал проверки в секундах
        
        Returns:
            Оплаченный Invoice или None если timeout
        """
        import asyncio
        
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            invoice = await self.get_invoice_by_id(invoice_id)
            
            if invoice and invoice.status.value == "paid":
                return invoice
            
            await asyncio.sleep(check_interval)
        
        return None


# ============================================
# CONTEXT MANAGER SUPPORT
# ============================================

class CryptoPayAPIContext(CryptoPayAPI):
    """Версия клиента с поддержкой async context manager"""
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

