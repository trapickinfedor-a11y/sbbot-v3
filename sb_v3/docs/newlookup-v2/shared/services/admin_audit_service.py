"""Shared audit logging helpers for admin and moderation actions."""

from html import escape
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Admin, AdminAuditLog
from shared.services.audit_event_service import AuditEventService
from shared.services.log_channel_service import LogChannelService
from shared.services.nocodb_service import NocoDBService


MODERATION_ACTION_MARKERS = (
    "_moderation_approve",
    "_moderation_reject",
    "_moderation_changes_requested",
)

FINANCE_ACTION_MARKERS = (
    "balance",
    "withdrawal",
    "deposit",
    "payout",
)


async def log_admin_action(
    session: AsyncSession,
    *,
    admin_id: Optional[int],
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    actor_label: Optional[str] = None,
) -> AdminAuditLog:
    """Write an audit log entry without forcing an extra commit."""
    entry = AdminAuditLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    session.add(entry)
    await session.flush()

    admin_username = None
    if admin_id:
        result = await session.execute(
            select(Admin.username).where(Admin.id == admin_id)
        )
        admin_username = result.scalar_one_or_none()

    actor_display = actor_label or admin_username or str(admin_id or "system")
    event_type = "login" if action == "login" else f"audit_{action}"
    emoji = "🔐" if action == "login" else "🧾"
    lines = [
        f"{emoji} <b>Action:</b> {escape(str(action))}",
        f"👤 <b>Admin:</b> {escape(actor_display)}",
    ]
    if entity_type:
        lines.append(f"📦 <b>Entity:</b> {escape(str(entity_type))}")
    if entity_id is not None:
        lines.append(f"🆔 <b>Entity ID:</b> {escape(str(entity_id))}")
    if ip_address:
        lines.append(f"🌐 <b>IP:</b> <code>{escape(str(ip_address))}</code>")
    if details:
        lines.append(f"📝 <b>Details:</b> <code>{escape(str(details))}</code>")

    await LogChannelService.send(
        text="\n".join(lines),
        event_type=event_type,
        urgent=action in {
            "login",
            "admin_deactivate",
            "admin_activate",
            "seller_ban",
            "seller_leak_ban",
            "seller_deposit_auto_approved",
        },
        payload={
            "action": action,
            "admin_id": admin_id,
            "admin_username": admin_username,
            "actor_label": actor_label,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
            "ip_address": ip_address,
        },
    )

    if any(marker in action for marker in MODERATION_ACTION_MARKERS):
        NocoDBService.log_moderator_action(
            order_id=(details or {}).get("upload_batch_id") or entity_id,
            moderator_id=admin_id,
            action=action,
            message=(details or {}).get("comment")
            or (details or {}).get("item_name")
            or (details or {}).get("bank_name"),
            extra={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "details": details or {},
                "ip_address": ip_address,
                "actor_label": actor_label,
            },
        )

    if action != "seller_deposit_auto_approved" and any(marker in action for marker in FINANCE_ACTION_MARKERS):
        finance_details = details or {}
        finance_user_id = (
            finance_details.get("user_id")
            or finance_details.get("seller_id")
            or finance_details.get("worker_id")
            or finance_details.get("marketer_id")
            or finance_details.get("owner_user_id")
            or entity_id
        )
        finance_amount = finance_details.get("amount")
        if finance_amount is not None:
            NocoDBService.log_financial_operation(
                user_id=finance_user_id,
                amount=finance_amount,
                payment_method=finance_details.get("payment_method") or finance_details.get("provider"),
                tx_id=finance_details.get("tx_hash")
                or finance_details.get("invoice_id")
                or finance_details.get("payment_id"),
                admin_id=admin_id,
                operation_type=action,
                extra={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "details": finance_details,
                    "ip_address": ip_address,
                    "actor_label": actor_label,
                },
            )
    await AuditEventService.log(
        session,
        event_type=f"admin_{action}",
        source="web_panel" if admin_id else "system",
        actor_type="admin",
        actor_id=admin_id,
        target_type=entity_type,
        target_id=entity_id,
        status="ok",
        payload={
            "action": action,
            "details": details or {},
            "ip_address": ip_address,
            "actor_label": actor_label,
        },
    )
    return entry
