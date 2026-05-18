"""Admin authentication and management service"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models import Admin
from web_panel.auth import get_password_hash, verify_password
from web_panel.config import web_panel_config


async def ensure_first_admin(session: AsyncSession) -> Optional[Admin]:
    """
    If admins table is empty, create first owner-level admin from env.
    Existing admins remain authoritative in the DB.
    Returns the seeded admin or None.
    """
    username = web_panel_config.admin_username
    password = web_panel_config.admin_password
    if not username or not password:
        return None

    if password.startswith("$2b$"):
        password_hash = password
    else:
        password_hash = get_password_hash(password)

    # If this admin already exists, keep the DB password authoritative.
    existing_by_username = await session.execute(
        select(Admin).where(Admin.username == username)
    )
    admin = existing_by_username.scalar_one_or_none()
    if admin:
        return admin

    # No admin with this username — create if table is empty
    result = await session.execute(select(Admin).limit(1))
    if result.scalar_one_or_none():
        return None  # Other admins exist but username doesn't match
    admin = Admin(
        username=username,
        password_hash=password_hash,
        role="owner",
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def get_admin_by_username(session: AsyncSession, username: str) -> Optional[Admin]:
    result = await session.execute(
        select(Admin)
        .options(selectinload(Admin.role_obj))
        .options(selectinload(Admin.uploader_catalog_permissions))
        .where(Admin.username == username, Admin.is_active == True)
    )
    return result.scalar_one_or_none()


async def verify_admin_password(session: AsyncSession, username: str, password: str) -> Optional[Admin]:
    admin = await get_admin_by_username(session, username)
    if not admin:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin
