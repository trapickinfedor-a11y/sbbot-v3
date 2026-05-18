"""
Seed test data into ALL tables for Admin Panel demo.
Run: cd /path/to/newlookup && python scripts/seed_test_data.py
"""
import sys, os, asyncio, random, string
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/newlookup.db")
os.environ.setdefault("TASKS_DATABASE_URL", "sqlite+aiosqlite:///./data/tasks.db")

from shared.database.session import init_db, async_session_maker
from shared.database.models import *

US_STATES = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI", "NJ", "VA", "WA", "AZ", "MA"]
BANK_NAMES = ["Chase", "Bank of America", "Wells Fargo", "Citi", "Capital One", "US Bank", "PNC", "TD Bank", "Truist", "Fifth Third"]
CATEGORIES = ["SSN", "DL", "MVR", "FULLZ", "PROS_FULLZ", "BACKGROUND_CHECK"]
SERVICES = ["ssn_lookup", "dl_front_back", "mvr_report", "fullz_standard", "pros_fullz_premium", "bg_check"]
CC_BRANDS = ["Visa", "Mastercard", "Amex", "Discover"]
FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

def rnd_date(days_back=90):
    return datetime.utcnow() - timedelta(days=random.randint(0, days_back), hours=random.randint(0, 23), minutes=random.randint(0, 59))

def rnd_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase, k=n))

def rnd_price(lo=5, hi=500):
    return Decimal(str(round(random.uniform(lo, hi), 2)))


async def seed():
    await init_db()
    async with async_session_maker() as s:
        from sqlalchemy import select as sa_select, func
        existing = (await s.execute(sa_select(func.count()).select_from(User))).scalar() or 0
        if existing > 10:
            print(f"⚠️  Database already has {existing} users. Skipping seed to avoid duplicates.")
            print("   Delete data/newlookup.db and restart to re-seed.")
            return

        # ── 1. Mirror Bots ──
        bots = []
        for i, (name, owner) in enumerate([
            ("lookupbot", 100001), ("probot", 100002), ("fastbot", 100003),
            ("premiumbot", 100004), ("elitebot", 100005),
        ], 1):
            b = MirrorBot(bot_token=f"fake:token_{name}_{i}", bot_username=name, owner_user_id=owner, bot_type="user", is_active=True, created_at=rnd_date(180))
            s.add(b)
            bots.append(b)
        await s.flush()
        print(f"✅ MirrorBots: {len(bots)}")

        # ── 2. Marketers ──
        marketers = []
        for i in range(5):
            m = Marketer(telegram_id=300000 + i, username=f"marketer_{i}", display_name=f"Marketer {i}", promo_code=f"PROMO{i:03d}", reward_percent=7.0, user_bonus_percent=3.0, balance=rnd_price(50, 2000), total_earned=rnd_price(500, 10000), total_withdrawn=rnd_price(100, 3000), is_active=True, created_at=rnd_date(120))
            s.add(m)
            marketers.append(m)
        await s.flush()
        print(f"✅ Marketers: {len(marketers)}")

        # ── 3. Users ──
        users = []
        for i in range(50):
            bot = random.choice(bots)
            u = User(user_id=500000 + i, username=f"user_{rnd_str(5)}", mirror_bot_id=bot.id, language=random.choice(["en", "ru", "zh", "es"]), balance=rnd_price(0, 5000), referral_link=f"ref_{rnd_str(12)}", is_banned=random.random() < 0.05, trust_score=random.randint(50, 100), last_active_at=rnd_date(30), marketer_id=random.choice(marketers).id if random.random() < 0.3 else None, created_at=rnd_date(90))
            s.add(u)
            users.append(u)
        await s.flush()
        print(f"✅ Users: {len(users)}")

        # ── 4. Workers ──
        workers = []
        for i in range(10):
            w = Worker(telegram_id=200000 + i, username=f"worker_{i}", categories=random.sample(CATEGORIES, k=random.randint(2, 4)), balance=rnd_price(0, 3000), orders_completed=random.randint(10, 500), is_active=True, total_earned=rnd_price(500, 15000), total_withdrawn=rnd_price(100, 5000), worker_score=round(random.uniform(3.5, 5.0), 2), commission_percent=random.choice([None, 50.0, 70.0, 80.0]), created_at=rnd_date(180))
            s.add(w)
            workers.append(w)
        await s.flush()
        print(f"✅ Workers: {len(workers)}")

        # ── 5. Orders ──
        orders = []
        for i in range(120):
            u = random.choice(users)
            cat = random.choice(CATEGORIES)
            svc = random.choice(SERVICES)
            status = random.choice(["pending", "processing", "completed", "cancelled", "completed", "completed"])
            w = random.choice(workers) if status != "pending" else None
            o = Order(user_id=u.user_id, mirror_bot_id=u.mirror_bot_id, category=cat, service_name=svc, input_data={"name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}", "state": random.choice(US_STATES)}, price=rnd_price(5, 200), status=status, worker_id=w.id if w else None, created_at=rnd_date(60), completed_at=rnd_date(30) if status == "completed" else None)
            s.add(o)
            orders.append(o)
        await s.flush()
        print(f"✅ Orders: {len(orders)}")

        # ── 6. Transactions ──
        txns = []
        for i in range(200):
            u = random.choice(users)
            tx_type = random.choice(["deposit", "purchase", "withdrawal", "commission", "refund"])
            t = Transaction(user_id=u.user_id, account_type="user", account_id=u.user_id, type=tx_type, amount=rnd_price(5, 500), description=f"Test {tx_type} #{i}", status="completed", created_at=rnd_date(60))
            s.add(t)
            txns.append(t)
        await s.flush()
        print(f"✅ Transactions: {len(txns)}")

        # ── 7. Support Tickets ──
        tickets = []
        for i in range(30):
            u = random.choice(users)
            cat = random.choice(["payment", "product", "general", "technical", "financial"])
            st = random.choice(["open", "in_progress", "solved", "closed"])
            tk = SupportTicket(user_id=u.user_id, mirror_bot_id=u.mirror_bot_id, category=cat, subject=f"Test ticket #{i}: {cat}", status=st, priority=random.choice(["LOW", "NORMAL", "HIGH", "CRITICAL"]), created_at=rnd_date(30))
            s.add(tk)
            tickets.append(tk)
        await s.flush()
        for tk in tickets:
            for j in range(random.randint(1, 5)):
                sm = SupportMessage(ticket_id=tk.id, sender_type=random.choice(["user", "admin"]), sender_id=random.randint(100000, 999999), message_text=f"Message {j} for ticket {tk.id}", created_at=rnd_date(15))
                s.add(sm)
        await s.flush()
        print(f"✅ SupportTickets: {len(tickets)}")

        # ── 8. Complaints ──
        for i in range(15):
            c = Complaint(worker_id=random.choice(workers).id, user_id=random.choice(users).user_id, order_id=random.choice(orders).id, reason=random.choice(["ban_request", "invalid_data", "abuse", "other"]), description=f"Test complaint #{i}", status=random.choice(["pending", "reviewed", "resolved", "rejected"]), created_at=rnd_date(30))
            s.add(c)
        await s.flush()
        print("✅ Complaints: 15")

        # ── 9. Sellers ──
        sellers = []
        for i in range(8):
            sl = Seller(telegram_id=400000 + i, username=f"seller_{i}", display_name=f"Seller Pro {i}", seller_type=random.choice(["internal", "external"]), is_approved=True, is_active=True, access_status="active", markup_percent=random.uniform(10, 30), total_orders=random.randint(20, 500), total_earned=rnd_price(1000, 50000), deposit_balance=rnd_price(100, 5000), withdrawable_balance=rnd_price(50, 3000), seller_score=round(random.uniform(3.5, 5.0), 2), created_at=rnd_date(120))
            s.add(sl)
            sellers.append(sl)
        await s.flush()
        print(f"✅ Sellers: {len(sellers)}")

        # ── 10. Seller Banks ──
        seller_banks = []
        for i in range(20):
            sl = random.choice(sellers)
            bn = random.choice(BANK_NAMES)
            sb = SellerBank(seller_id=sl.id, bank_name=bn, bank_code=f"{bn.lower().replace(' ', '_')}_{i}", category=random.choice(["personal", "business", "vcc"]), seller_price=rnd_price(50, 300), buyer_price=rnd_price(80, 500), base_price=rnd_price(40, 250), is_in_stock=True, stock_count=random.randint(1, 20), has_ssn=random.random() > 0.5, has_dob=random.random() > 0.5, state=random.choice(US_STATES), moderation_status=random.choice(["approved", "approved", "pending_moderation", "rejected"]), created_at=rnd_date(60))
            s.add(sb)
            seller_banks.append(sb)
        await s.flush()
        print(f"✅ SellerBanks: {len(seller_banks)}")

        # ── 11. Seller Orders ──
        for i in range(40):
            sl = random.choice(sellers)
            sb = random.choice([x for x in seller_banks if x.seller_id == sl.id] or seller_banks)
            so = SellerOrder(seller_id=sl.id, seller_bank_id=sb.id, buyer_user_id=random.choice(users).user_id, mirror_bot_id=random.choice(bots).id, status=random.choice(["pending_admin", "pending_seller", "completed", "cancelled", "completed", "completed"]), price_for_buyer=rnd_price(80, 500), price_for_seller=rnd_price(50, 300), created_at=rnd_date(30))
            s.add(so)
        await s.flush()
        print("✅ SellerOrders: 40")

        # ── 12. Seller Withdrawals ──
        for i in range(10):
            sw = SellerWithdrawal(seller_id=random.choice(sellers).id, amount=rnd_price(50, 2000), requisites=f"TRC20:T{rnd_str(33)}", status=random.choice(["pending", "approved", "rejected"]), created_at=rnd_date(30))
            s.add(sw)
        await s.flush()
        print("✅ SellerWithdrawals: 10")

        # ── 13. Seller CC Items ──
        for i in range(15):
            sl = random.choice(sellers)
            ci = SellerCCItem(seller_id=sl.id, item_name=f"{random.choice(CC_BRANDS)} {random.choice(['Platinum', 'Gold', 'Classic'])} #{i}", cc_code=f"cc_{rnd_str(6)}_{i}", category_code=random.choice(["us_cc", "eu_cc", "world_cc"]), seller_price=rnd_price(20, 150), buyer_price=rnd_price(30, 250), base_price=rnd_price(15, 120), is_in_stock=True, stock_count=random.randint(1, 10), has_fullz=random.random() > 0.4, card_brand=random.choice(CC_BRANDS), country="US", state=random.choice(US_STATES), moderation_status=random.choice(["approved", "approved", "pending_moderation"]), created_at=rnd_date(30))
            s.add(ci)
        await s.flush()
        print("✅ SellerCCItems: 15")

        # ── 14. Bank Items (catalog) ──
        for i, (bn, cat) in enumerate([(b, c) for b in BANK_NAMES[:6] for c in ["personal", "business"]]):
            bi = BankItem(bank_code=f"{bn.lower().replace(' ', '_')}_{cat}_{i}", name=f"{bn} — {cat.title()}", category=cat, price=rnd_price(30, 300), is_active=True, position=i, created_at=rnd_date(60))
            s.add(bi)
        await s.flush()
        print("✅ BankItems: 12")

        # ── 15. Service Prices ──
        service_data = [
            ("ssn_lookup", "SSN", "SSN Lookup", 15), ("dl_front_back", "DL", "DL Front+Back", 45), ("mvr_report", "MVR", "MVR Report", 35),
            ("fullz_standard", "FULLZ", "Standard Fullz", 25), ("pros_fullz", "PROS_FULLZ", "Pros Fullz", 60), ("bg_check", "BACKGROUND", "Background Check", 55),
            ("credit_report", "CREDIT", "Credit Report", 40), ("bank_statement", "BANK", "Bank Statement", 70), ("tax_return", "TAX", "Tax Return W2", 80),
        ]
        for i, (key, cat, name, price) in enumerate(service_data):
            sp = ServicePrice(key=key, category=cat, display_name=name, price=Decimal(str(price)), bulk_price=Decimal(str(price * 0.8)), is_active=True, position=i)
            s.add(sp)
        await s.flush()
        print(f"✅ ServicePrices: {len(service_data)}")

        # ── 16. CC Catalog ──
        cc_cats = [("us_cc", "US Cards"), ("eu_cc", "EU Cards"), ("world_cc", "World Cards")]
        for code, name in cc_cats:
            s.add(CCCategory(code=code, name=name, is_active=True))
        await s.flush()
        for i in range(8):
            s.add(CCItem(cc_code=f"cc_item_{i}", name=f"{random.choice(CC_BRANDS)} {random.choice(['Standard', 'Gold', 'Platinum'])} #{i}", category_code=random.choice(["us_cc", "eu_cc", "world_cc"]), price=rnd_price(10, 100), is_active=True, position=i))
        await s.flush()
        print("✅ CCCategories: 3, CCItems: 8")

        # ── 17. Education ──
        edu_cats = [("edu_subs", "Subscriptions", "subscription"), ("edu_manuals", "Manuals", "manual")]
        for code, name, itype in edu_cats:
            s.add(EducationCategory(code=code, name=name, item_type=itype, is_active=True))
        await s.flush()
        for i in range(4):
            s.add(EducationSubscription(code=f"sub_{i}", name=f"Pro Course #{i}", category_code="edu_subs", price=rnd_price(20, 200), duration_days=random.choice([7, 14, 30, 90]), is_active=True))
        await s.flush()
        print("✅ Education: 2 cats, 4 subs")

        # ── 18. Accounts ──
        acc_cats = [("bg_accounts", "Background Accounts", "background"), ("lookup_ba", "Lookup BA", "lookup_ba"), ("ai_tools", "AI Tools", "ai"), ("proxy_service", "Proxy Service", "proxy")]
        for code, name, atype in acc_cats:
            s.add(AccountCategory(code=code, name=name, category_type=atype, is_active=True))
        await s.flush()
        for i in range(8):
            cat = random.choice(acc_cats)
            s.add(AccountItem(code=f"acc_{cat[0]}_{i}", name=f"{cat[1]} Plan #{i}", category_code=cat[0], price=rnd_price(10, 150), duration_months=random.choice([1, 3, 6, 12]), is_active=True, position=i))
        await s.flush()
        print("✅ Accounts: 4 cats, 8 items")

        # ── 19. Brute Bank ──
        bb_groups = []
        for i, bn in enumerate(BANK_NAMES[:5]):
            bc = f"brute_{bn.lower().replace(' ', '_')}"
            g = BruteBankGroup(
                group_key=bc,
                bank_code=bc,
                bank_name=bn,
                category=random.choice(["personal", "business"]),
                is_active=True,
                position=i,
            )
            s.add(g)
            bb_groups.append(g)
        await s.flush()
        for i in range(20):
            g = random.choice(bb_groups)
            sl = random.choice(sellers)
            s.add(BruteBankItem(seller_id=sl.id, group_id=g.id, bank_name=g.bank_name, bank_code=g.bank_code, category=g.category, credentials={"login": f"user_{rnd_str(6)}@mail.com", "password": rnd_str(12)}, price=rnd_price(30, 500), base_price=rnd_price(20, 400), buyer_price=rnd_price(40, 600), balance_info=f"${random.randint(500, 50000):,}", state=random.choice(US_STATES), moderation_status=random.choice(["approved", "approved", "pending"]), status=random.choice(["available", "available", "sold"]), is_active=True, created_at=rnd_date(30)))
        await s.flush()
        print("✅ BruteBank: 5 groups, 20 items")

        # ── 20. Another Services ──
        for i in range(5):
            s.add(AnotherServiceButton(text_en=f"Service {i}", text_ru=f"Сервис {i}", url=f"https://example.com/service{i}", button_type="url", position=i, is_active=True))
        await s.flush()
        print("✅ AnotherServices: 5")

        # ── 21. Broadcasts ──
        for i in range(8):
            st = random.choice(["completed", "completed", "pending", "in_progress", "failed"])
            s.add(Broadcast(mirror_bot_id=random.choice(bots).id if random.random() > 0.3 else None, message_text=f"Test broadcast message #{i}", status=st, total_users=random.randint(100, 5000), sent_count=random.randint(50, 4000), failed_count=random.randint(0, 100), created_by=5611930487, created_at=rnd_date(30)))
        await s.flush()
        print("✅ Broadcasts: 8")

        # ── 22. Marketer Stats ──
        for m in marketers:
            for d in range(30):
                s.add(MarketerStats(marketer_id=m.id, date=datetime.utcnow().date() - timedelta(days=d), registrations=random.randint(0, 20), first_topups=random.randint(0, 10), topup_amount=rnd_price(0, 500), earned=rnd_price(0, 100)))
        await s.flush()
        print("✅ MarketerStats: 150")

        # ── 23. Marketer Withdrawals ──
        for i in range(8):
            s.add(MarketerWithdrawal(marketer_id=random.choice(marketers).id, amount=rnd_price(50, 1000), requisites=f"TRC20:T{rnd_str(33)}", status=random.choice(["pending", "approved", "rejected"]), created_at=rnd_date(30)))
        await s.flush()
        print("✅ MarketerWithdrawals: 8")

        # ── 24. Worker Stats ──
        for w in workers:
            for d in range(14):
                s.add(WorkerStats(worker_id=w.id, date=datetime.utcnow().date() - timedelta(days=d), category=random.choice(CATEGORIES), orders_done=random.randint(1, 20), orders_nf=random.randint(0, 3), orders_total=random.randint(5, 25), earnings=rnd_price(10, 500)))
        await s.flush()
        print("✅ WorkerStats: 140")

        # ── 25. Worker Withdrawals ──
        for i in range(6):
            s.add(WorkerWithdrawal(worker_id=random.choice(workers).id, amount=rnd_price(50, 1500), requisites=f"BTC:bc1q{rnd_str(38)}", status=random.choice(["pending", "approved", "rejected"]), created_at=rnd_date(30)))
        await s.flush()
        print("✅ WorkerWithdrawals: 6")

        # ── 26. Worker Expense Reports ──
        for i in range(5):
            s.add(WorkerExpenseReport(worker_id=random.choice(workers).id, amount=rnd_price(10, 200), category=random.choice(["subscription", "tools", "other"]), description=f"Expense report #{i}", status=random.choice(["pending", "approved", "rejected"]), created_at=rnd_date(30)))
        await s.flush()
        print("✅ WorkerExpenseReports: 5")

        # ── 27. Bot Owners ──
        for owner_id in [100001, 100002, 100003]:
            s.add(BotOwner(owner_user_id=owner_id, balance=rnd_price(100, 5000), total_earned=rnd_price(500, 20000), total_withdrawn=rnd_price(100, 5000)))
        await s.flush()
        print("✅ BotOwners: 3")

        # ── 28. Bot Owner Stats ──
        for bot in bots[:3]:
            for d in range(30):
                s.add(BotOwnerStats(mirror_bot_id=bot.id, date=datetime.utcnow().date() - timedelta(days=d), spent=rnd_price(10, 500), topped_up=rnd_price(20, 1000), owner_income=rnd_price(1, 70)))
        await s.flush()
        print("✅ BotOwnerStats: 90")

        # ── 29. Bot Owner Withdrawals ──
        for i in range(4):
            s.add(BotOwnerWithdrawal(owner_user_id=random.choice([100001, 100002, 100003]), amount=rnd_price(50, 2000), payment_method="USDT", payment_network="TRC20", requisites=f"T{rnd_str(33)}", status=random.choice(["pending", "approved"]), created_at=rnd_date(30)))
        await s.flush()
        print("✅ BotOwnerWithdrawals: 4")

        # ── 30. Admin Roles ──
        roles = [
            ("super_admin", "Super Admin", {"users": True, "orders": True, "finance": True, "sellers": True, "workers": True, "admins": True, "audit": True, "analytics": True, "broadcasts": True}, True),
            ("moderator", "Moderator", {"users": True, "orders": True, "sellers": True, "complaints": True}, True),
            ("finance", "Finance Manager", {"finance": True, "deposits": True, "reports": True, "analytics": True}, True),
            ("support", "Support Agent", {"users": True, "support": True, "complaints": True}, True),
        ]
        admin_roles = []
        for name, display, perms, is_sys in roles:
            r = AdminRole(name=name, display_name=display, permissions=perms, is_system=is_sys)
            s.add(r)
            admin_roles.append(r)
        await s.flush()
        print(f"✅ AdminRoles: {len(admin_roles)}")

        # ── 31. Audit Log entries ──
        for i in range(50):
            s.add(AdminAuditLog(admin_id=1, action=random.choice(["login", "user_ban", "order_approve", "seller_approve", "deposit_approve", "settings_change"]), entity_type=random.choice(["user", "order", "seller", "worker"]), entity_id=random.randint(1, 100), details={"info": f"Test audit #{i}"}, ip_address=f"192.168.1.{random.randint(1, 254)}", created_at=rnd_date(30)))
        await s.flush()
        print("✅ AuditLogs: 50")

        # ── 32. Notification Logs ──
        for i in range(30):
            s.add(NotificationLog(event_type=random.choice(["order_created", "order_completed", "deposit_confirmed", "support_reply"]), channel=random.choice(["telegram", "web", "email"]), recipient_id=random.randint(100000, 999999), status=random.choice(["sent", "failed", "pending"]), created_at=rnd_date(15)))
        await s.flush()
        print("✅ NotificationLogs: 30")

        # ── 33. Pricing Config ──
        configs = [
            ("seller_markup_default", "number", 20.0, "Default seller markup %"),
            ("min_deposit", "number", 10.0, "Minimum deposit amount"),
            ("max_withdrawal", "number", 5000.0, "Maximum withdrawal per day"),
            ("referral_bonus", "number", 5.0, "Referral bonus %"),
            ("escrow_hold_hours", "number", 24.0, "Escrow hold period hours"),
        ]
        for key, vtype, val, desc in configs:
            s.add(PricingConfig(key=key, value_type=vtype, value_number=Decimal(str(val)), description=desc))
        await s.flush()
        print("✅ PricingConfig: 5")

        # ── 34. Knowledge Base ──
        for i in range(10):
            s.add(KnowledgeBaseArticle(title=f"How to {random.choice(['use', 'setup', 'configure', 'manage'])} {random.choice(['orders', 'deposits', 'sellers', 'workers', 'bots'])}", body=f"Detailed article #{i} with step-by-step instructions...\n\nStep 1: Open the dashboard.\nStep 2: Navigate to the section.\nStep 3: Follow the prompts.", keywords=f"help,guide,tutorial,faq", category=random.choice(["general", "financial", "technical", "worker"]), audience=random.choice(["user", "worker", "all"]), views=random.randint(0, 500), helpful_votes=random.randint(0, 50), is_active=True, created_at=rnd_date(60)))
        await s.flush()
        print("✅ KnowledgeBase: 10")

        # ── 35. Menu Categories ──
        from sqlalchemy import select as sa_select
        menu_cats = [
            ("lookup", "lookup", "SSN / DL / MVR Lookup", 0, 0),
            ("banks", "banks", "Banks Catalog", 1, 0),
            ("cc", "cc", "Credit Cards", 1, 1),
            ("education", "education", "Education & Manuals", 2, 0),
            ("accounts", "accounts", "Accounts & Subs", 2, 1),
            ("documents", "documents", "Documents", 3, 0),
        ]
        added_mc = 0
        for code, route, label, row, pos in menu_cats:
            exists = (await s.execute(sa_select(MirrorMenuCategory).where(MirrorMenuCategory.code == code))).scalar_one_or_none()
            if not exists:
                s.add(MirrorMenuCategory(code=code, route_key=route, label_en=label, label_ru=label, row_index=row, position=pos, is_active=True))
                added_mc += 1
        await s.flush()
        print(f"✅ MenuCategories: {added_mc} new (skipped existing)")

        # ── 36. Automation ──
        proxy = AutomationProxy(name="US Residential Proxy", host="proxy.example.com", port=8080, username="user", password="pass", proxy_type="http", country="us", is_active=True, is_default=True)
        s.add(proxy)
        await s.flush()
        s.add(AutomationApiKey(provider="lookup_api", name="Primary Key", key_value="ak_test_" + rnd_str(32), balance=Decimal("450.00"), daily_limit=1000, is_active=True))
        s.add(AutomationConfig(service_code="lookup_credit", is_enabled=True, worker_count=10, max_retries=3, active_proxy_id=proxy.id))
        await s.flush()
        print("✅ Automation: 1 proxy, 1 key, 1 config")

        # ── 37. Seller Disputes ──
        from sqlalchemy import select
        seller_order_ids = (await s.execute(select(SellerOrder.id).limit(5))).scalars().all()
        for i, so_id in enumerate(seller_order_ids[:3]):
            s.add(SellerOrderDispute(order_id=so_id, opened_by=random.choice(users).user_id, reason=random.choice(["not_working", "wrong_data", "scam"]), description=f"Dispute #{i}: item not as described", status=random.choice(["open", "resolved"]), created_at=rnd_date(15)))
        await s.flush()
        print("✅ SellerDisputes: 3")

        # ── 38. Worker Violations ──
        for i in range(5):
            s.add(WorkerViolation(worker_id=random.choice(workers).id, order_id=random.choice(orders).id, violation_type=random.choice(["contact_leak", "phone_number", "url_leak"]), original_text=f"Contact me at test@example.com", filtered_text=f"Contact me at [FILTERED]", created_at=rnd_date(30)))
        await s.flush()
        print("✅ WorkerViolations: 5")

        # ── 39. Referrals ──
        for i in range(10):
            u1, u2 = random.sample(users, 2)
            try:
                s.add(Referral(referrer_id=u1.user_id, referred_id=u2.user_id, earned_total=rnd_price(1, 50), created_at=rnd_date(60)))
                await s.flush()
            except Exception:
                await s.rollback()
                continue
        print("✅ Referrals: ~10")

        # ── 40. Seller NFC/OTP/Check items (a few each) ──
        for i in range(3):
            sl = random.choice(sellers)
            s.add(SellerNFCItem(seller_id=sl.id, item_name=f"Apple Pay {random.choice(BANK_NAMES)} #{i}", nfc_type=random.choice(["ap", "gp"]), bank_name=random.choice(BANK_NAMES), country="US", state=random.choice(US_STATES), seller_price=rnd_price(100, 500), buyer_price=rnd_price(150, 700), data_file_path=f"/data/nfc/nfc_{i}.dat", moderation_status="approved", is_active=True, created_at=rnd_date(30)))
        for i in range(3):
            sl = random.choice(sellers)
            s.add(SellerOTPItem(seller_id=sl.id, item_name=f"OTP {random.choice(BANK_NAMES)} #{i}", bank_name=random.choice(BANK_NAMES), balance=rnd_price(1000, 50000), has_fullz=random.random() > 0.5, sms_access_type=random.choice(["seller_mediated", "account_access"]), seller_price=rnd_price(100, 800), buyer_price=rnd_price(150, 1000), moderation_status="approved", is_active=True, created_at=rnd_date(30)))
        for i in range(3):
            sl = random.choice(sellers)
            s.add(SellerCheckItem(seller_id=sl.id, item_name=f"Check {random.choice(BANK_NAMES)} #{i}", check_type=random.choice(["personal", "business", "cashiers"]), bank_name=random.choice(BANK_NAMES), amount=rnd_price(500, 10000), state=random.choice(US_STATES), scan_file_path=f"/data/checks/check_{i}.png", seller_price=rnd_price(50, 300), buyer_price=rnd_price(80, 500), moderation_status="approved", is_active=True, created_at=rnd_date(30)))
        await s.flush()
        print("✅ NFC/OTP/Check items: 3+3+3")

        # ── 41. System Settings ──
        settings = [
            ("maintenance_mode", "false", "Enable maintenance mode"),
            ("min_order_amount", "5", "Minimum order amount USD"),
            ("support_auto_close_hours", "72", "Auto-close tickets after hours"),
            ("max_daily_withdrawals", "3", "Max withdrawal requests per day"),
        ]
        for key, val, desc in settings:
            s.add(SystemSetting(key=key, value=val, description=desc))
        await s.flush()
        print("✅ SystemSettings: 4")

        # ── 42. Product Catalog Services ──
        pcs_data = [
            ("docs", "documents_photo", "test_dl_front_back", "DL Front + Back"),
            ("docs", "documents_photo", "test_dl_selfie", "DL + Selfie"),
            ("docs", "documents_direct", "test_work_travel_permit", "Work/Travel Permit"),
            ("pros_fullz", "fullz_personal", "test_fullz_standard", "Standard Fullz"),
            ("pros_fullz", "fullz_personal", "test_fullz_premium", "Premium Fullz"),
        ]
        for cat, grp, code, name in pcs_data:
            existing_pcs = (await s.execute(sa_select(ProductCatalogService).where(ProductCatalogService.code == code))).scalar_one_or_none()
            if not existing_pcs:
                s.add(ProductCatalogService(category_key=cat, menu_group=grp, code=code, name=name, is_active=True))
        await s.flush()
        print("✅ ProductCatalogServices: 5")

        # ── 43. Marketer Activity Logs ──
        for i in range(20):
            s.add(MarketerActivityLog(marketer_id=random.choice(marketers).id, action=random.choice(["earning", "withdrawal_request", "withdrawal_approved"]), amount=rnd_price(5, 200), details=f"Activity #{i}", created_at=rnd_date(30)))
        await s.flush()
        print("✅ MarketerActivityLogs: 20")

        # ── COMMIT ──
        try:
            await s.commit()
        except Exception as e:
            print(f"⚠️ Commit error: {e}")
            await s.rollback()
            await s.commit()
        print("\n" + "=" * 50)
        print("🎉 ALL TEST DATA LOADED SUCCESSFULLY!")
        print("=" * 50)
        print("\nRefresh Admin Panel at http://localhost:8000/dashboard")


if __name__ == "__main__":
    asyncio.run(seed())
