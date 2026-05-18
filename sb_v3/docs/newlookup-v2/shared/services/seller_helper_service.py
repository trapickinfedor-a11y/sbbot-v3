from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Seller, SellerHelper, SellerHelperAuditLog


class SellerHelperService:
    VALID_ROLES = {"upload_helper", "support_helper", "manager_helper"}
    VALID_STATUSES = {"pending", "active", "blocked", "removed"}

    @staticmethod
    async def list_helpers(session: AsyncSession, seller_id: int, include_removed: bool = False) -> list[SellerHelper]:
        stmt = select(SellerHelper).where(SellerHelper.seller_id == seller_id).order_by(SellerHelper.created_at.desc())
        if not include_removed:
            stmt = stmt.where(SellerHelper.status != "removed")
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_helper(session: AsyncSession, helper_id: int, seller_id: Optional[int] = None) -> Optional[SellerHelper]:
        stmt = select(SellerHelper).where(SellerHelper.id == helper_id)
        if seller_id is not None:
            stmt = stmt.where(SellerHelper.seller_id == seller_id)
        return await session.scalar(stmt)

    @staticmethod
    async def get_pending_invite(session: AsyncSession, telegram_id: int) -> Optional[SellerHelper]:
        return await session.scalar(
            select(SellerHelper).where(
                and_(SellerHelper.telegram_id == telegram_id, SellerHelper.status == "pending")
            )
        )

    @staticmethod
    async def create_invite(
        session: AsyncSession,
        *,
        seller: Seller,
        telegram_id: int,
        username: Optional[str],
        display_name: Optional[str],
        role: str,
    ) -> SellerHelper:
        if role not in SellerHelperService.VALID_ROLES:
            raise ValueError("Invalid helper role")

        helper = await session.scalar(
            select(SellerHelper).where(
                and_(
                    SellerHelper.seller_id == seller.id,
                    SellerHelper.telegram_id == telegram_id,
                )
            )
        )
        if helper:
            helper.username = username or helper.username
            helper.display_name = display_name or helper.display_name
            helper.role = role
            helper.status = "pending"
            helper.blocked_at = None
        else:
            helper = SellerHelper(
                seller_id=seller.id,
                telegram_id=telegram_id,
                username=username,
                display_name=display_name,
                role=role,
                status="pending",
                invited_by=seller.id,
            )
            session.add(helper)
        await session.flush()
        await SellerHelperService.log_action(
            session,
            seller_id=seller.id,
            helper_id=helper.id,
            action="helper_invited",
            object_type="seller_helper",
            object_id=helper.id,
            payload={"role": role, "telegram_id": telegram_id, "username": username},
        )
        await session.commit()
        await session.refresh(helper)
        return helper

    @staticmethod
    async def accept_invite(session: AsyncSession, helper: SellerHelper, *, username: Optional[str], display_name: Optional[str]) -> SellerHelper:
        helper.status = "active"
        helper.username = username or helper.username
        helper.display_name = display_name or helper.display_name
        helper.joined_at = datetime.now(timezone.utc)
        await session.flush()
        await SellerHelperService.log_action(
            session,
            seller_id=helper.seller_id,
            helper_id=helper.id,
            action="helper_accepted_invite",
            object_type="seller_helper",
            object_id=helper.id,
        )
        await session.commit()
        await session.refresh(helper)
        return helper

    @staticmethod
    async def change_status(session: AsyncSession, helper: SellerHelper, *, status: str) -> SellerHelper:
        if status not in SellerHelperService.VALID_STATUSES:
            raise ValueError("Invalid helper status")
        helper.status = status
        helper.blocked_at = datetime.now(timezone.utc) if status == "blocked" else None
        await session.flush()
        await SellerHelperService.log_action(
            session,
            seller_id=helper.seller_id,
            helper_id=helper.id,
            action=f"helper_status_{status}",
            object_type="seller_helper",
            object_id=helper.id,
        )
        await session.commit()
        await session.refresh(helper)
        return helper

    @staticmethod
    async def change_role(session: AsyncSession, helper: SellerHelper, *, role: str) -> SellerHelper:
        if role not in SellerHelperService.VALID_ROLES:
            raise ValueError("Invalid helper role")
        helper.role = role
        await session.flush()
        await SellerHelperService.log_action(
            session,
            seller_id=helper.seller_id,
            helper_id=helper.id,
            action="helper_role_changed",
            object_type="seller_helper",
            object_id=helper.id,
            payload={"role": role},
        )
        await session.commit()
        await session.refresh(helper)
        return helper

    @staticmethod
    async def log_action(
        session: AsyncSession,
        *,
        seller_id: int,
        action: str,
        helper_id: Optional[int] = None,
        object_type: Optional[str] = None,
        object_id: Optional[int] = None,
        payload: Optional[dict] = None,
    ) -> None:
        session.add(
            SellerHelperAuditLog(
                seller_id=seller_id,
                helper_id=helper_id,
                action=action,
                object_type=object_type,
                object_id=object_id,
                payload_json=payload,
            )
        )
