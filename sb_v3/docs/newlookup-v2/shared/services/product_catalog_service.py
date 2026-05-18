from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import ProductCatalogService


DEFAULT_PRODUCT_CATALOG_SERVICES = [
    {
        "category_key": "docs",
        "category_name": "📄 Documents",
        "menu_group": "documents_photo",
        "code": "dl_front_back",
        "name": "DL (Front & Back)",
        "order": 10,
    },
    {
        "category_key": "docs",
        "category_name": "📄 Documents",
        "menu_group": "documents_photo",
        "code": "dl_selfie",
        "name": "DL + Selfie",
        "order": 20,
    },
    {
        "category_key": "docs",
        "category_name": "📄 Documents",
        "menu_group": "documents_photo",
        "code": "passport",
        "name": "Passport",
        "order": 30,
    },
    {
        "category_key": "docs",
        "category_name": "📄 Documents",
        "menu_group": "documents_photo",
        "code": "business_docs",
        "name": "Business Docs",
        "order": 40,
    },
    {
        "category_key": "docs",
        "category_name": "📄 Documents",
        "menu_group": "documents_direct",
        "code": "dl_kyc",
        "name": "DL + KYC",
        "order": 10,
    },
    {
        "category_key": "pros_fullz",
        "category_name": "👤 PROS & FULLZ",
        "menu_group": "fullz_personal",
        "code": "fullz_700plus",
        "name": "700+ CS",
        "order": 10,
    },
    {
        "category_key": "pros_fullz",
        "category_name": "👤 PROS & FULLZ",
        "menu_group": "fullz_personal",
        "code": "fullz_800plus",
        "name": "800+ CS",
        "order": 20,
    },
    {
        "category_key": "pros_fullz",
        "category_name": "👤 PROS & FULLZ",
        "menu_group": "fullz_personal",
        "code": "fullz_under18",
        "name": "Under 18 Old",
        "order": 30,
    },
    {
        "category_key": "pros_fullz",
        "category_name": "👤 PROS & FULLZ",
        "menu_group": "fullz_personal",
        "code": "fullz_immigrant",
        "name": "Immigrant",
        "order": 40,
    },
    {
        "category_key": "pros_fullz",
        "category_name": "👤 PROS & FULLZ",
        "menu_group": "fullz_personal",
        "code": "fullz_zero_bank",
        "name": "Fullz 0 Bank",
        "order": 50,
    },
    {
        "category_key": "pros_fullz",
        "category_name": "👤 PROS & FULLZ",
        "menu_group": "fullz_personal",
        "code": "personal_random",
        "name": "Random",
        "order": 60,
    },
]


class ProductCatalogManager:
    @staticmethod
    async def ensure_defaults(session: AsyncSession) -> None:
        existing_codes = set(
            (
                await session.execute(select(ProductCatalogService.code))
            ).scalars().all()
        )
        created = False
        for item in DEFAULT_PRODUCT_CATALOG_SERVICES:
            if item["code"] in existing_codes:
                continue
            session.add(ProductCatalogService(**item))
            created = True
        if created:
            await session.commit()

    @staticmethod
    async def list_services(
        session: AsyncSession,
        *,
        category_key: Optional[str] = None,
        menu_group: Optional[str] = None,
        active_only: bool = False,
    ) -> List[ProductCatalogService]:
        query = select(ProductCatalogService)
        if category_key:
            query = query.where(ProductCatalogService.category_key == category_key)
        if menu_group:
            query = query.where(ProductCatalogService.menu_group == menu_group)
        if active_only:
            query = query.where(ProductCatalogService.is_active == True)
        query = query.order_by(ProductCatalogService.category_key, ProductCatalogService.menu_group, ProductCatalogService.order, ProductCatalogService.id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_service(session: AsyncSession, code: str) -> Optional[ProductCatalogService]:
        result = await session.execute(
            select(ProductCatalogService).where(ProductCatalogService.code == code)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_categories_payload(session: AsyncSession, active_only: bool = True) -> Dict[str, dict]:
        services = await ProductCatalogManager.list_services(session, active_only=active_only)
        payload: Dict[str, dict] = {}
        for service in services:
            if service.category_key not in payload:
                display_name = (
                    getattr(service, "category_name", None)
                    or service.category_key.replace("_", " ").title()
                )
                payload[service.category_key] = {
                    "name": display_name,
                    "services": {},
                }
            payload[service.category_key]["services"][service.code] = service.name
        return payload

    @staticmethod
    def format_service_label(code: str) -> str:
        return code.replace("_", " ").title()

    @staticmethod
    def compute_age_days(created_at: Optional[datetime]) -> Optional[int]:
        if not created_at:
            return None
        return max(0, (datetime.now(timezone.utc) - created_at).days)
