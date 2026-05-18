from __future__ import annotations

"""
NocoDB REST API v2 клиент
https://docs.nocodb.com/developer-resources/rest-apis/
"""

import logging
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class NocoDBClient:
    """Асинхронный клиент для NocoDB API v2"""

    def __init__(
        self,
        base_url: str,
        api_token: str,
        *,
        timeout: float = 30.0,
    ):
        """
        Args:
            base_url: URL инстанса NocoDB (например https://app.nocodb.com)
            api_token: API токен (xc-token)
            timeout: Таймаут запросов в секундах
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._headers = {
            "xc-token": api_token,
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v2{path}"

    async def list_records(
        self,
        table_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
        where: Optional[str] = None,
    ) -> dict:
        """
        GET /tables/{tableId}/records
        Возвращает список записей.
        """
        params = {"limit": limit, "offset": offset}
        if where:
            params["where"] = where
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                self._url(f"/tables/{table_id}/records"),
                headers=self._headers,
                params=params,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def create_record(self, table_id: str, data: dict[str, Any]) -> dict:
        """
        POST /tables/{tableId}/records
        Создаёт запись. Возвращает созданную запись с Id.
        """
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                self._url(f"/tables/{table_id}/records"),
                headers=self._headers,
                json=data,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def create_records_bulk(
        self, table_id: str, records: list[dict[str, Any]]
    ) -> list[dict]:
        """
        POST /tables/{tableId}/records (bulk)
        Создаёт несколько записей. NocoDB поддерживает массив в body.
        """
        if not records:
            return []
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                self._url(f"/tables/{table_id}/records"),
                headers=self._headers,
                json=records,
            ) as resp:
                resp.raise_for_status()
                result = await resp.json()
                return result if isinstance(result, list) else [result]

    async def update_record(
        self, table_id: str, record_id: str | int, data: dict[str, Any]
    ) -> dict:
        """
        PATCH /tables/{tableId}/records/{recordId}
        Обновляет запись.
        """
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.patch(
                self._url(f"/tables/{table_id}/records/{record_id}"),
                headers=self._headers,
                json=data,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def delete_record(self, table_id: str, record_id: str | int) -> None:
        """
        DELETE /tables/{tableId}/records/{recordId}
        """
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.delete(
                self._url(f"/tables/{table_id}/records/{record_id}"),
                headers=self._headers,
            ) as resp:
                resp.raise_for_status()

    async def test_connection(self) -> bool:
        """Проверка подключения — запрос метаданных"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    self._url("/meta/bases"),
                    headers=self._headers,
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.warning(f"NocoDB connection test failed: {e}")
            return False
