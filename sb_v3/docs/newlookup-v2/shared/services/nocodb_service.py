from __future__ import annotations

import asyncio
import logging
import weakref
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from shared.config.settings import global_settings
from shared.nocodb.client import NocoDBClient

logger = logging.getLogger(__name__)


def _to_iso(value: datetime | str | None) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return datetime.now(timezone.utc).isoformat()


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return _to_iso(value)
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items() if v is not None}
    if isinstance(value, (list, tuple, set)):
        return [_serialize(item) for item in value]
    return value


def _compact(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: _serialize(value) for key, value in payload.items() if value is not None}


class NocoDBService:
    _pending_tasks: weakref.WeakSet[asyncio.Task[None]] = weakref.WeakSet()
    _TABLE_ATTRS = {
        "order_messages": "nocodb_order_messages_table_id",
        "moderator_actions": "nocodb_moderator_actions_table_id",
        "seller_buyer_chat": "nocodb_seller_buyer_chat_table_id",
        "support_tickets": "nocodb_support_tickets_table_id",
        "financial_operations": "nocodb_financial_operations_table_id",
        "file_operations": "nocodb_file_operations_table_id",
        "errors": "nocodb_errors_table_id",
        "seller_uploads": "nocodb_seller_uploads_table_id",
        "event_log": "nocodb_event_log_table_id",
    }

    @classmethod
    def enabled(cls) -> bool:
        return global_settings.nocodb_enabled

    @classmethod
    def _table_id(cls, table_key: str) -> str:
        return getattr(global_settings, cls._TABLE_ATTRS[table_key], "")

    @classmethod
    def _client(cls) -> NocoDBClient | None:
        if not cls.enabled():
            return None
        return NocoDBClient(
            base_url=global_settings.nocodb_api_url,
            api_token=global_settings.nocodb_api_token,
        )

    @classmethod
    async def _append_record(cls, table_key: str, payload: dict[str, Any]) -> None:
        client = cls._client()
        table_id = cls._table_id(table_key)
        if not client or not table_id:
            return
        try:
            await client.create_record(table_id, _compact(payload))
        except Exception as exc:
            logger.warning("Failed to append NocoDB %s log: %s", table_key, exc)

    @classmethod
    def _schedule(cls, table_key: str, payload: dict[str, Any]) -> None:
        if not cls.enabled():
            return
        if not cls._table_id(table_key):
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("Skipping NocoDB log without running event loop: %s", table_key)
            return
        task = loop.create_task(cls._append_record(table_key, payload))
        cls._pending_tasks.add(task)

    @classmethod
    def log_order_message(
        cls,
        *,
        order_id: int | None,
        worker_id: int | None,
        message: str | None,
        files: list[dict] | list[str] | None = None,
        timestamp: datetime | str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        cls._schedule(
            "order_messages",
            {
                "order_id": order_id,
                "worker_id": worker_id,
                "message": message,
                "files": files or [],
                "timestamp": _to_iso(timestamp),
                "metadata": extra or {},
            },
        )

    @classmethod
    def log_moderator_action(
        cls,
        *,
        order_id: int | None,
        moderator_id: int | None,
        action: str,
        message: str | None = None,
        timestamp: datetime | str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        cls._schedule(
            "moderator_actions",
            {
                "order_id": order_id,
                "moderator_id": moderator_id,
                "action": action,
                "message": message,
                "timestamp": _to_iso(timestamp),
                "metadata": extra or {},
            },
        )

    @classmethod
    def log_seller_buyer_chat(
        cls,
        *,
        order_id: int | None,
        seller_id: int | None,
        buyer_id: int | None,
        message: str | None,
        files: list[dict] | list[str] | None = None,
        timestamp: datetime | str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        cls._schedule(
            "seller_buyer_chat",
            {
                "order_id": order_id,
                "seller_id": seller_id,
                "buyer_id": buyer_id,
                "message": message,
                "files": files or [],
                "timestamp": _to_iso(timestamp),
                "metadata": extra or {},
            },
        )

    @classmethod
    def log_support_ticket(
        cls,
        *,
        ticket_id: int | None,
        user_id: int | None,
        message: str | None = None,
        support_reply: str | None = None,
        files: list[dict] | list[str] | None = None,
        timestamp: datetime | str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        cls._schedule(
            "support_tickets",
            {
                "ticket_id": ticket_id,
                "user_id": user_id,
                "message": message,
                "support_reply": support_reply,
                "files": files or [],
                "timestamp": _to_iso(timestamp),
                "metadata": extra or {},
            },
        )

    @classmethod
    def log_financial_operation(
        cls,
        *,
        user_id: int | None,
        amount: Any,
        payment_method: str | None,
        tx_id: Any = None,
        admin_id: int | None = None,
        operation_type: str | None = None,
        timestamp: datetime | str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        cls._schedule(
            "financial_operations",
            {
                "user_id": user_id,
                "amount": amount,
                "payment_method": payment_method,
                "tx_id": tx_id,
                "admin_id": admin_id,
                "operation_type": operation_type,
                "timestamp": _to_iso(timestamp),
                "metadata": extra or {},
            },
        )

    @classmethod
    def log_file_operation(
        cls,
        *,
        user_id: int | None,
        action: str,
        file_id: Any,
        category: str | None,
        timestamp: datetime | str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        cls._schedule(
            "file_operations",
            {
                "user_id": user_id,
                "action": action,
                "file_id": file_id,
                "category": category,
                "timestamp": _to_iso(timestamp),
                "metadata": extra or {},
            },
        )

    @classmethod
    def log_error(
        cls,
        *,
        user_id: int | None,
        error_type: str,
        context: dict[str, Any] | str,
        timestamp: datetime | str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        cls._schedule(
            "errors",
            {
                "user_id": user_id,
                "error_type": error_type,
                "context": context if isinstance(context, str) else _compact(context),
                "timestamp": _to_iso(timestamp),
                "metadata": extra or {},
            },
        )

    @classmethod
    def log_seller_upload(
        cls,
        *,
        seller_id: int | None,
        category: str | None,
        status: str,
        error_reason: str | None = None,
        timestamp: datetime | str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        cls._schedule(
            "seller_uploads",
            {
                "seller_id": seller_id,
                "category": category,
                "status": status,
                "error_reason": error_reason,
                "timestamp": _to_iso(timestamp),
                "metadata": extra or {},
            },
        )

    @classmethod
    def log_event(
        cls,
        *,
        event_type: str,
        actor_type: str | None = None,
        actor_id: Any = None,
        target_type: str | None = None,
        target_id: Any = None,
        status: str | None = None,
        payload: dict[str, Any] | None = None,
        timestamp: datetime | str | None = None,
    ) -> None:
        cls._schedule(
            "event_log",
            {
                "event_type": event_type,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "target_type": target_type,
                "target_id": target_id,
                "status": status or "ok",
                "payload": payload or {},
                "timestamp": _to_iso(timestamp),
            },
        )
