"""Audit logging compatibility wrapper."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.admin_audit_service import log_admin_action


async def log_action(
    session: AsyncSession,
    admin_id: Optional[int],
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    """Write an audit log entry."""
    return await log_admin_action(
        session,
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
