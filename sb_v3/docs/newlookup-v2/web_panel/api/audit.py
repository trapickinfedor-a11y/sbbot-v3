from __future__ import annotations

"""
API для просмотра логов аудита в web admin panel.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Admin, AdminAuditLog, AuditLog as UniversalAuditLog, Product, ProductActionLog
from web_panel.auth import require_audit_access
from web_panel.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

CRITICAL_AUDIT_GROUPS = {"withdrawal", "balance_change", "moderation"}
WITHDRAWAL_ENTITIES = {
    "seller_withdrawal",
    "seller_withdrawal_task",
    "marketer_withdrawal",
    "bot_owner_withdrawal",
    "worker_withdrawal",
    "worker_withdrawal_task",
}
MODERATION_ENTITIES = {
    "seller",
    "seller_bank",
    "seller_cc_item",
    "seller_nfc_item",
    "seller_otp_item",
    "seller_selfreg_cc_item",
    "seller_check_item",
    "brute_bank_item",
}


class AuditLogResponse(BaseModel):
    id: int
    stream: str = "admin"
    admin_id: Optional[int]
    admin_username: Optional[str]
    actor_display: str
    action: str
    action_group: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    details: Optional[dict]
    ip_address: Optional[str]
    source: str
    created_at: str


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class ProductActionLogResponse(BaseModel):
    id: int
    product_id: Optional[int]
    product_name: Optional[str]
    actor_type: str
    actor_id: Optional[int]
    action: str
    product_age_days: Optional[int]
    details: Optional[dict]
    created_at: str


def _classify_audit_action(action: str, entity_type: Optional[str]) -> str:
    action_lower = (action or "").lower()
    entity_type = entity_type or ""

    if "withdrawal" in action_lower or "payout" in action_lower or entity_type in WITHDRAWAL_ENTITIES:
        return "withdrawal"
    if "balance" in action_lower or "deposit" in action_lower:
        return "balance_change"
    if "moderation" in action_lower:
        return "moderation"
    if entity_type in MODERATION_ENTITIES and (
        "approve" in action_lower
        or "reject" in action_lower
        or "ban" in action_lower
        or "unban" in action_lower
        or "changes" in action_lower
        or "suspend" in action_lower
    ):
        return "moderation"
    if action_lower == "login":
        return "access"
    if action_lower.startswith("admin_"):
        return "admin"
    return "other"


def _parse_date(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {value}") from exc
    if end_of_day:
        return parsed + timedelta(days=1)
    return parsed


def _normalize_details(details: Optional[dict]) -> dict:
    return details if isinstance(details, dict) else {}


def _extract_source(audit_log: AdminAuditLog) -> str:
    details = _normalize_details(audit_log.details)
    explicit_source = details.get("source")
    if explicit_source:
        return str(explicit_source)
    if audit_log.admin_id:
        return "web_panel"
    if details.get("actor_telegram_id"):
        return "bot"
    if details.get("auto_blocked") or details.get("automatic"):
        return "automation"
    return "system"


def _actor_display(audit_log: AdminAuditLog, admin_username: Optional[str]) -> str:
    if admin_username:
        return admin_username
    details = _normalize_details(audit_log.details)
    source = _extract_source(audit_log)
    actor_telegram_id = details.get("actor_telegram_id")
    if actor_telegram_id is not None:
        return f"{source}:{actor_telegram_id}"
    if audit_log.admin_id is not None:
        return f"admin:{audit_log.admin_id}"
    return source


def _matches_search(audit_log: AdminAuditLog, admin_username: Optional[str], search_term: str) -> bool:
    haystack = " ".join(
        [
            str(audit_log.action or ""),
            str(audit_log.entity_type or ""),
            str(audit_log.entity_id or ""),
            str(admin_username or ""),
            str(_extract_source(audit_log)),
            str(audit_log.details or ""),
        ]
    ).lower()
    return search_term in haystack


def _matches_universal_search(audit_log: UniversalAuditLog, search_term: str) -> bool:
    haystack = " ".join(
        [
            str(audit_log.event_type or ""),
            str(audit_log.source or ""),
            str(audit_log.actor_type or ""),
            str(audit_log.actor_id or ""),
            str(audit_log.target_type or ""),
            str(audit_log.target_id or ""),
            str(audit_log.payload or ""),
        ]
    ).lower()
    return search_term in haystack


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action_group: Optional[str] = Query(None, description="withdrawal | balance_change | moderation | access | admin | other"),
    critical_only: bool = Query(False),
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    admin_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    search: Optional[str] = Query(None),
    stream: str = Query("all", description="all | admin | universal"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_audit_access()),
):
    """Список записей аудита."""
    start_date = _parse_date(date_from)
    end_date = _parse_date(date_to, end_of_day=True)

    # PERF-1 FIX: Hard limit to prevent memory exhaustion
    # Max 1000 rows total to prevent OOM (was 5000)
    MAX_AUDIT_ROWS = 1000
    fetch_limit = min(offset + limit + 500, MAX_AUDIT_ROWS)
    
    logger.info(
        "Audit logs requested: limit=%d, offset=%d, fetch_limit=%d",
        limit, offset, fetch_limit
    )

    stmt = (
        select(AdminAuditLog, Admin.username)
        .outerjoin(Admin, AdminAuditLog.admin_id == Admin.id)
        .order_by(desc(AdminAuditLog.created_at), desc(AdminAuditLog.id))
    )
    if entity_type:
        stmt = stmt.where(AdminAuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AdminAuditLog.action == action)
    if admin_id is not None:
        stmt = stmt.where(AdminAuditLog.admin_id == admin_id)
    if start_date:
        stmt = stmt.where(AdminAuditLog.created_at >= start_date)
    if end_date:
        stmt = stmt.where(AdminAuditLog.created_at < end_date)
    stmt = stmt.limit(fetch_limit)  # FIX: Use capped limit
    result = await db.execute(stmt)
    rows = result.all()

    filtered: list[AuditLogResponse] = []
    search_term = (search or "").strip().lower()
    if stream in {"all", "admin"}:
        for audit_log, admin_username in rows:
            audit_group = _classify_audit_action(audit_log.action, audit_log.entity_type)
            if critical_only and audit_group not in CRITICAL_AUDIT_GROUPS:
                continue
            if action_group and audit_group != action_group:
                continue
            audit_source = _extract_source(audit_log)
            if source and audit_source != source:
                continue
            if search_term and not _matches_search(audit_log, admin_username, search_term):
                continue

            filtered.append(
                AuditLogResponse(
                    id=audit_log.id,
                    stream="admin",
                    admin_id=audit_log.admin_id,
                    admin_username=admin_username,
                    actor_display=_actor_display(audit_log, admin_username),
                    action=audit_log.action,
                    action_group=audit_group,
                    entity_type=audit_log.entity_type,
                    entity_id=audit_log.entity_id,
                    details=audit_log.details,
                    ip_address=audit_log.ip_address,
                    source=audit_source,
                    created_at=audit_log.created_at.isoformat() if audit_log.created_at else "",
                )
            )

    if stream in {"all", "universal"}:
        universal_stmt = select(UniversalAuditLog).order_by(desc(UniversalAuditLog.created_at), desc(UniversalAuditLog.id))
        if entity_type:
            universal_stmt = universal_stmt.where(UniversalAuditLog.target_type == entity_type)
        if action:
            universal_stmt = universal_stmt.where(UniversalAuditLog.event_type == action)
        if start_date:
            universal_stmt = universal_stmt.where(UniversalAuditLog.created_at >= start_date)
        if end_date:
            universal_stmt = universal_stmt.where(UniversalAuditLog.created_at < end_date)
        universal_stmt = universal_stmt.limit(fetch_limit)  # FIX: Use capped limit
        universal_rows = (await db.execute(universal_stmt)).scalars().all()
        for audit_log in universal_rows:
            audit_group = _classify_audit_action(audit_log.event_type, audit_log.target_type)
            if critical_only and audit_group not in CRITICAL_AUDIT_GROUPS:
                continue
            if action_group and audit_group != action_group:
                continue
            if source and audit_log.source != source:
                continue
            if search_term and not _matches_universal_search(audit_log, search_term):
                continue
            filtered.append(
                AuditLogResponse(
                    id=audit_log.id,
                    stream="universal",
                    admin_id=None,
                    admin_username=None,
                    actor_display=f"{audit_log.actor_type or 'system'}:{audit_log.actor_id}" if audit_log.actor_id is not None else (audit_log.actor_type or audit_log.source),
                    action=audit_log.event_type,
                    action_group=audit_group,
                    entity_type=audit_log.target_type,
                    entity_id=int(audit_log.target_id) if audit_log.target_id is not None else None,
                    details=audit_log.payload,
                    ip_address=None,
                    source=audit_log.source,
                    created_at=audit_log.created_at.isoformat() if audit_log.created_at else "",
                )
            )
    filtered.sort(key=lambda item: item.created_at, reverse=True)
    total = len(filtered)
    items = filtered[offset : offset + limit]
    return AuditLogListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + limit < total,
    )


@router.get("/product-actions", response_model=List[ProductActionLogResponse])
async def list_product_action_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_audit_access()),
):
    stmt = (
        select(ProductActionLog, Product.name)
        .outerjoin(Product, ProductActionLog.product_id == Product.id)
        .order_by(desc(ProductActionLog.created_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        ProductActionLogResponse(
            id=row[0].id,
            product_id=row[0].product_id,
            product_name=row[1],
            actor_type=row[0].actor_type,
            actor_id=row[0].actor_id,
            action=row[0].action,
            product_age_days=row[0].product_age_days,
            details=row[0].details,
            created_at=row[0].created_at.isoformat() if row[0].created_at else "",
        )
        for row in rows
    ]
