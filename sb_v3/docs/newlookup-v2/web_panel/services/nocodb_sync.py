from __future__ import annotations

"""
Сервис синхронизации Seller CRM с NocoDB
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import SellerOrder, SellerCCOrder, Seller, SellerBank, SellerCCItem
from shared.nocodb.client import NocoDBClient

logger = logging.getLogger(__name__)

# Маппинг полей: наше имя -> имя колонки в NocoDB (Title Case по умолчанию)
DEFAULT_FIELD_MAP = {
    "internal_id": "InternalId",       # composite: bank_123 или cc_456
    "order_type": "OrderType",
    "order_id": "OrderId",
    "seller_id": "SellerId",
    "seller_name": "SellerName",
    "item_name": "ItemName",
    "buyer_user_id": "BuyerUserId",
    "status": "Status",
    "price_for_buyer": "PriceForBuyer",
    "price_for_seller": "PriceForSeller",
    "quantity": "Quantity",
    "created_at": "CreatedAt",
    "admin_approved_at": "AdminApprovedAt",
    "taken_at": "TakenAt",
    "completed_at": "CompletedAt",
}


def _sync_state_path() -> Path:
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "nocodb_sync_state.json"


def _load_sync_state() -> dict:
    path = _sync_state_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load NocoDB sync state: {e}")
        return {}


def _save_sync_state(state: dict) -> None:
    path = _sync_state_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _order_to_record(
    order: SellerOrder | SellerCCOrder,
    order_type: str,
    seller_name: str,
    item_name: str,
    field_map: dict,
) -> dict:
    """Преобразует заказ в запись для NocoDB"""
    internal_id = f"{order_type}_{order.id}"
    created_at = order.created_at.isoformat() if order.created_at else None
    admin_approved_at = order.admin_approved_at.isoformat() if getattr(order, "admin_approved_at", None) and order.admin_approved_at else None
    taken_at = order.taken_at.isoformat() if getattr(order, "taken_at", None) and order.taken_at else None
    completed_at = order.completed_at.isoformat() if getattr(order, "completed_at", None) and order.completed_at else None

    raw = {
        "internal_id": internal_id,
        "order_type": order_type,
        "order_id": order.id,
        "seller_id": order.seller_id,
        "seller_name": seller_name,
        "item_name": item_name,
        "buyer_user_id": order.buyer_user_id,
        "status": order.status,
        "price_for_buyer": float(order.price_for_buyer),
        "price_for_seller": float(order.price_for_seller),
        "quantity": order.quantity,
        "created_at": created_at,
        "admin_approved_at": admin_approved_at,
        "taken_at": taken_at,
        "completed_at": completed_at,
    }
    return {field_map.get(k, k): v for k, v in raw.items() if field_map.get(k, k)}


class NocoDBSyncService:
    """Синхронизация заказов Seller CRM в NocoDB"""

    def __init__(
        self,
        base_url: str,
        api_token: str,
        table_id: str,
        *,
        field_map: Optional[dict] = None,
    ):
        self.client = NocoDBClient(base_url=base_url, api_token=api_token)
        self.table_id = table_id
        self.field_map = field_map or DEFAULT_FIELD_MAP.copy()

    async def sync_orders(self, db: AsyncSession) -> dict:
        """
        Синхронизирует все заказы (bank + cc) в NocoDB.
        Возвращает статистику: created, updated, errors.
        """
        state = _load_sync_state()
        stats = {"created": 0, "updated": 0, "errors": 0, "skipped": 0}

        # Bank orders
        bank_result = await db.execute(
            select(SellerOrder).order_by(SellerOrder.created_at.desc()).limit(500)
        )
        bank_orders = bank_result.scalars().all()

        for order in bank_orders:
            try:
                seller_res = await db.execute(select(Seller).where(Seller.id == order.seller_id))
                seller = seller_res.scalar_one_or_none()
                bank_res = await db.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
                bank = bank_res.scalar_one_or_none()
                seller_name = (seller.display_name or seller.username or "?") if seller else "?"
                item_name = bank.bank_name if bank else "?"

                record = _order_to_record(order, "bank", seller_name, item_name, self.field_map)
                internal_id = f"bank_{order.id}"
                nc_id = state.get(internal_id)

                if nc_id:
                    await self.client.update_record(self.table_id, nc_id, record)
                    stats["updated"] += 1
                else:
                    result = await self.client.create_record(self.table_id, record)
                    rid = result.get("Id") or result.get("id")
                    if rid is not None:
                        state[internal_id] = str(rid)
                        stats["created"] += 1
                    else:
                        stats["errors"] += 1
            except Exception as e:
                logger.exception(f"NocoDB sync error for bank order {order.id}: {e}")
                stats["errors"] += 1

        # CC orders
        cc_result = await db.execute(
            select(SellerCCOrder).order_by(SellerCCOrder.created_at.desc()).limit(500)
        )
        cc_orders = cc_result.scalars().all()

        for order in cc_orders:
            try:
                seller_res = await db.execute(select(Seller).where(Seller.id == order.seller_id))
                seller = seller_res.scalar_one_or_none()
                item_res = await db.execute(select(SellerCCItem).where(SellerCCItem.id == order.seller_cc_item_id))
                item = item_res.scalar_one_or_none()
                seller_name = (seller.display_name or seller.username or "?") if seller else "?"
                item_name = item.item_name if item else "?"

                record = _order_to_record(order, "cc", seller_name, item_name, self.field_map)
                internal_id = f"cc_{order.id}"
                nc_id = state.get(internal_id)

                if nc_id:
                    await self.client.update_record(self.table_id, nc_id, record)
                    stats["updated"] += 1
                else:
                    result = await self.client.create_record(self.table_id, record)
                    rid = result.get("Id") or result.get("id")
                    if rid is not None:
                        state[internal_id] = str(rid)
                        stats["created"] += 1
                    else:
                        stats["errors"] += 1
            except Exception as e:
                logger.exception(f"NocoDB sync error for cc order {order.id}: {e}")
                stats["errors"] += 1

        _save_sync_state(state)
        return stats

    async def test_connection(self) -> bool:
        return await self.client.test_connection()
