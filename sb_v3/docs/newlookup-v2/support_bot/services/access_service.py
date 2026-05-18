from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models import Admin, Worker
from shared.services.admin_catalog_access import get_admin_allowed_catalogs
from web_panel.auth import (
    ROLE_ADMIN,
    ROLE_ACCOUNTANT,
    ROLE_FINANCE,
    ROLE_MODERATOR,
    ROLE_OWNER,
    ROLE_SUPPORT,
    ROLE_SUPER_ADMIN,
    ROLE_UPLOADER,
)


SUPPORT_BOT_ACCESS_ROLES = {
    ROLE_SUPPORT,
    ROLE_MODERATOR,
    ROLE_FINANCE,
    ROLE_ACCOUNTANT,
    ROLE_UPLOADER,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

MANUAL_BALANCE_ROLES = {
    ROLE_SUPPORT,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

SELLER_MODERATION_ROLES = {
    ROLE_MODERATOR,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}

ACCOUNTANT_ROLES = {
    ROLE_FINANCE,
    ROLE_ACCOUNTANT,
    ROLE_ADMIN,
    ROLE_OWNER,
    ROLE_SUPER_ADMIN,
}


@dataclass
class SupportBotActor:
    telegram_id: int
    source: str
    role: str
    admin_id: Optional[int] = None
    username: Optional[str] = None
    worker_id: Optional[int] = None
    allowed_catalogs: Optional[list[str]] = None

    @property
    def is_worker(self) -> bool:
        return self.source == "worker"

    @property
    def is_admin_like(self) -> bool:
        return self.source in {"system_admin", "admin"}

    @property
    def can_add_balance(self) -> bool:
        return self.source == "system_admin" or self.role in MANUAL_BALANCE_ROLES

    @property
    def can_moderate_sellers(self) -> bool:
        return self.source == "system_admin" or self.role in SELLER_MODERATION_ROLES

    @property
    def can_manage_finance(self) -> bool:
        return self.source == "system_admin" or self.role in ACCOUNTANT_ROLES

    @property
    def can_upload_catalogs(self) -> bool:
        return self.source == "system_admin" or self.role == ROLE_UPLOADER

    def actor_label(self) -> str:
        if self.source == "admin":
            return f"{self.role}:{self.username or self.telegram_id}"
        if self.source == "worker":
            return f"worker:{self.worker_id or self.telegram_id}"
        return f"system_admin:{self.telegram_id}"


class SupportAccessService:
    @staticmethod
    async def get_admin_actor(session: AsyncSession, telegram_id: int) -> Optional[SupportBotActor]:
        result = await session.execute(
            select(Admin)
            .options(selectinload(Admin.uploader_catalog_permissions))
            .where(
                Admin.telegram_id == telegram_id,
                Admin.is_active == True,
            )
        )
        admin = result.scalar_one_or_none()
        if not admin or admin.role not in SUPPORT_BOT_ACCESS_ROLES:
            return None
        return SupportBotActor(
            telegram_id=telegram_id,
            source="admin",
            role=admin.role,
            admin_id=admin.id,
            username=admin.username,
            allowed_catalogs=get_admin_allowed_catalogs(admin),
        )

    @staticmethod
    async def get_worker_actor(session: AsyncSession, telegram_id: int) -> Optional[SupportBotActor]:
        result = await session.execute(
            select(Worker).where(
                Worker.telegram_id == telegram_id,
                Worker.is_active == True,
                Worker.is_suspended == False,
            )
        )
        worker = result.scalar_one_or_none()
        if not worker:
            return None
        return SupportBotActor(
            telegram_id=telegram_id,
            source="worker",
            role="worker",
            username=worker.username,
            worker_id=worker.id,
        )

    @staticmethod
    def get_system_admin_actor(telegram_id: int) -> SupportBotActor:
        return SupportBotActor(
            telegram_id=telegram_id,
            source="system_admin",
            role=ROLE_SUPER_ADMIN,
            allowed_catalogs=[],
        )
