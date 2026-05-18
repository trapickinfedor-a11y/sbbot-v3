"""Seed remaining tables that failed in the first run."""
import sys, os, asyncio, random, string
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/newlookup.db")
os.environ.setdefault("TASKS_DATABASE_URL", "sqlite+aiosqlite:///./data/tasks.db")

from shared.database.session import init_db, async_session_maker
from shared.database.models import *
from sqlalchemy import select, func

US_STATES = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
BANK_NAMES = ["Chase", "Bank of America", "Wells Fargo", "Citi", "Capital One"]

def rnd_date(days_back=90):
    return datetime.utcnow() - timedelta(days=random.randint(0, days_back), hours=random.randint(0, 23))

def rnd_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase, k=n))

def rnd_price(lo=5, hi=500):
    return Decimal(str(round(random.uniform(lo, hi), 2)))


async def seed_remaining():
    await init_db()
    async with async_session_maker() as s:
        # Menu Categories (skip existing)
        menu_cats = [
            ("lookup", "lookup", "SSN / DL / MVR Lookup", 0, 0),
            ("banks_cat", "banks", "Banks Catalog", 1, 0),
            ("cc_cat", "cc", "Credit Cards", 1, 1),
            ("education_cat", "education", "Education & Manuals", 2, 0),
            ("accounts_cat", "accounts", "Accounts & Subs", 2, 1),
            ("documents_cat", "documents", "Documents", 3, 0),
        ]
        added = 0
        for code, route, label, row, pos in menu_cats:
            exists = (await s.execute(select(MirrorMenuCategory).where(MirrorMenuCategory.code == code))).scalar_one_or_none()
            if not exists:
                s.add(MirrorMenuCategory(code=code, route_key=route, label_en=label, label_ru=label, row_index=row, position=pos, is_active=True))
                added += 1
        await s.flush()
        print(f"✅ MenuCategories: {added} new")

        # Automation stuff (skip if exists)
        proxy_count = (await s.execute(select(func.count()).select_from(AutomationProxy))).scalar() or 0
        if proxy_count == 0:
            proxy = AutomationProxy(name="US Residential Proxy", host="proxy.example.com", port=8080, proxy_type="http", country="us", is_active=True, is_default=True)
            s.add(proxy)
            await s.flush()
            s.add(AutomationApiKey(provider="lookup_api", name="Primary Key", key_value="ak_test_" + rnd_str(32), balance=Decimal("450.00"), daily_limit=1000, is_active=True))
            s.add(AutomationConfig(service_code="lookup_credit", is_enabled=True, worker_count=10, max_retries=3, active_proxy_id=proxy.id))
            await s.flush()
            print("✅ Automation: added")
        else:
            print("✅ Automation: already exists")

        # Seller Disputes (skip if exists)
        disp_count = (await s.execute(select(func.count()).select_from(SellerOrderDispute))).scalar() or 0
        if disp_count == 0:
            so_ids = (await s.execute(select(SellerOrder.id).limit(5))).scalars().all()
            user_ids = (await s.execute(select(User.user_id).limit(10))).scalars().all()
            for i, so_id in enumerate(so_ids[:3]):
                s.add(SellerOrderDispute(order_id=so_id, opened_by=random.choice(user_ids), reason=random.choice(["not_working", "wrong_data", "scam"]), description=f"Dispute #{i}: item not as described", status=random.choice(["open", "resolved"]), created_at=rnd_date(15)))
            await s.flush()
            print("✅ SellerDisputes: 3")
        else:
            print("✅ SellerDisputes: already exists")

        # Worker Violations
        viol_count = (await s.execute(select(func.count()).select_from(WorkerViolation))).scalar() or 0
        if viol_count == 0:
            worker_ids = (await s.execute(select(Worker.id).limit(10))).scalars().all()
            order_ids = (await s.execute(select(Order.id).limit(20))).scalars().all()
            if worker_ids:
                for i in range(5):
                    s.add(WorkerViolation(worker_id=random.choice(worker_ids), order_id=random.choice(order_ids) if order_ids else None, violation_type=random.choice(["contact_leak", "phone_number", "url_leak"]), original_text="Contact me at test@example.com", filtered_text="Contact me at [FILTERED]", created_at=rnd_date(30)))
                await s.flush()
                print("✅ WorkerViolations: 5")
            else:
                print("⚠️ No workers found, skipping violations")
        else:
            print("✅ WorkerViolations: already exists")

        # PricingConfig
        pc_count = (await s.execute(select(func.count()).select_from(PricingConfig))).scalar() or 0
        if pc_count == 0:
            for key, val, desc in [("seller_markup_default", 20.0, "Default seller markup %"), ("min_deposit", 10.0, "Minimum deposit"), ("max_withdrawal", 5000.0, "Max withdrawal per day")]:
                s.add(PricingConfig(key=key, value_type="number", value_number=Decimal(str(val)), description=desc))
            await s.flush()
            print("✅ PricingConfig: 3")
        else:
            print("✅ PricingConfig: already exists")

        # KnowledgeBase
        kb_count = (await s.execute(select(func.count()).select_from(KnowledgeBaseArticle))).scalar() or 0
        if kb_count == 0:
            for i in range(10):
                s.add(KnowledgeBaseArticle(title=f"Guide: {random.choice(['Orders', 'Deposits', 'Workers', 'Sellers', 'Bots'])} #{i}", body=f"Step-by-step guide #{i}.\n\n1. Open dashboard.\n2. Navigate.\n3. Complete.", keywords="help,guide,faq", category=random.choice(["general", "financial", "technical"]), audience=random.choice(["user", "worker", "all"]), views=random.randint(10, 500), helpful_votes=random.randint(0, 50), is_active=True))
            await s.flush()
            print("✅ KnowledgeBase: 10")
        else:
            print("✅ KnowledgeBase: already exists")

        # SystemSettings
        ss_count = (await s.execute(select(func.count()).select_from(SystemSetting))).scalar() or 0
        if ss_count < 4:
            for key, val, desc in [("test_maintenance_mode", "false", "Maintenance mode"), ("test_min_order", "5", "Min order"), ("test_auto_close_hours", "72", "Auto-close tickets")]:
                try:
                    s.add(SystemSetting(key=key, value=val, description=desc))
                    await s.flush()
                except Exception:
                    await s.rollback()
            print("✅ SystemSettings: added")
        else:
            print("✅ SystemSettings: already exists")

        # ProductCatalogServices
        pcs_count = (await s.execute(select(func.count()).select_from(ProductCatalogService))).scalar() or 0
        if pcs_count == 0:
            for cat, grp, code, name in [("docs", "documents_photo", "dl_front_back", "DL Front+Back"), ("docs", "documents_photo", "dl_selfie", "DL+Selfie"), ("pros_fullz", "fullz_personal", "fullz_standard", "Standard Fullz")]:
                s.add(ProductCatalogService(category_key=cat, menu_group=grp, code=code, name=name, is_active=True))
            await s.flush()
            print("✅ ProductCatalogServices: 3")
        else:
            print("✅ ProductCatalogServices: already exists")

        # MarketerActivityLogs
        mal_count = (await s.execute(select(func.count()).select_from(MarketerActivityLog))).scalar() or 0
        if mal_count == 0:
            mktr_ids = (await s.execute(select(Marketer.id).limit(5))).scalars().all()
            for i in range(20):
                s.add(MarketerActivityLog(marketer_id=random.choice(mktr_ids), action=random.choice(["earning", "withdrawal_request", "withdrawal_approved"]), amount=rnd_price(5, 200), details=f"Activity #{i}", created_at=rnd_date(30)))
            await s.flush()
            print("✅ MarketerActivityLogs: 20")
        else:
            print("✅ MarketerActivityLogs: already exists")

        # NFC/OTP/Check items
        nfc_count = (await s.execute(select(func.count()).select_from(SellerNFCItem))).scalar() or 0
        if nfc_count == 0:
            seller_ids = (await s.execute(select(Seller.id).limit(8))).scalars().all()
            for i in range(3):
                sl = random.choice(seller_ids)
                s.add(SellerNFCItem(seller_id=sl, item_name=f"Apple Pay {random.choice(BANK_NAMES)} #{i}", nfc_type=random.choice(["ap", "gp"]), bank_name=random.choice(BANK_NAMES), country="US", state=random.choice(US_STATES), seller_price=rnd_price(100, 500), buyer_price=rnd_price(150, 700), data_file_path=f"/data/nfc/nfc_{i}.dat", moderation_status="approved", is_active=True))
            for i in range(3):
                sl = random.choice(seller_ids)
                s.add(SellerOTPItem(seller_id=sl, item_name=f"OTP {random.choice(BANK_NAMES)} #{i}", bank_name=random.choice(BANK_NAMES), balance=rnd_price(1000, 50000), has_fullz=random.random() > 0.5, sms_access_type=random.choice(["seller_mediated", "account_access"]), seller_price=rnd_price(100, 800), buyer_price=rnd_price(150, 1000), moderation_status="approved", is_active=True))
            for i in range(3):
                sl = random.choice(seller_ids)
                s.add(SellerCheckItem(seller_id=sl, item_name=f"Check {random.choice(BANK_NAMES)} #{i}", check_type=random.choice(["personal", "business"]), bank_name=random.choice(BANK_NAMES), amount=rnd_price(500, 10000), state=random.choice(US_STATES), scan_file_path=f"/data/checks/check_{i}.png", seller_price=rnd_price(50, 300), buyer_price=rnd_price(80, 500), moderation_status="approved", is_active=True))
            await s.flush()
            print("✅ NFC/OTP/Check: 3+3+3")
        else:
            print("✅ NFC/OTP/Check: already exists")

        await s.commit()
        print("\n🎉 Remaining data seeded!")


if __name__ == "__main__":
    asyncio.run(seed_remaining())
