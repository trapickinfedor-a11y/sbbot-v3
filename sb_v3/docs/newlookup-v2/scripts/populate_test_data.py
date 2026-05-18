#!/usr/bin/env python3
"""
Populate database with test data for development/demo purposes.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
import random
import string

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from shared.database.session import async_session_maker
from shared.database.models import (
    MirrorBot, User, Seller, Worker, Marketer,
    Product, SellerCCItem, SellerLogsItem,
    Order, Transaction, SupportTicket, Admin, AdminRole,
    SellerWithdrawal, WorkerWithdrawal, SellerCCOrder
)


def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


async def populate_test_data():
    """Create comprehensive test data."""
    
    async with async_session_maker() as session:
        print("🚀 Starting test data population...")
        
        # 1. Create Mirror Bots
        print("\n📱 Creating Mirror Bots...")
        mirror_bot1 = MirrorBot(
            bot_token="1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
            bot_username="test_shop_bot",
            owner_user_id=111111111,
            bot_type="user",
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(mirror_bot1)
        
        mirror_bot2 = MirrorBot(
            bot_token="9876543210:BBHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
            bot_username="premium_cards_bot",
            owner_user_id=222222222,
            bot_type="user",
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(mirror_bot2)
        
        await session.flush()
        print(f"✅ Created 2 mirror bots")
        
        # 2. Create Users
        print("\n👥 Creating Users...")
        users = []
        for i in range(1, 11):
            user = User(
                user_id=300000000 + i,
                username=f"buyer_{i}",
                language="en" if i % 2 == 0 else "ru",
                balance=Decimal(f"{100 * i}.00"),
                referral_link=f"ref_{random_string(12)}",
                is_banned=False,
                mirror_bot_id=mirror_bot1.id if i <= 5 else mirror_bot2.id,
                created_at=datetime.utcnow() - timedelta(days=30-i)
            )
            users.append(user)
            session.add(user)
        
        await session.flush()
        print(f"✅ Created {len(users)} users")
        
        # 3. Create Sellers
        print("\n🏪 Creating Sellers...")
        sellers = []
        for i in range(1, 6):
            seller = Seller(
                telegram_id=400000000 + i,
                username=f"seller_{i}",
                display_name=f"Seller {i}",
                language="en",
                rules_accepted=True,
                seller_type="external",
                is_approved=True,
                is_active=True,
                access_status="active",
                markup_percent=15.0 + i * 2,
                total_orders=i * 10,
                total_earned=Decimal(f"{1000 * i}.00"),
                deposit_balance=Decimal(f"{500 * i}.00"),
                withdrawable_balance=Decimal(f"{300 * i}.00"),
                seller_score=4.0 + (i * 0.15),
                created_at=datetime.utcnow() - timedelta(days=60-i),
                approved_at=datetime.utcnow() - timedelta(days=55-i)
            )
            sellers.append(seller)
            session.add(seller)
        
        await session.flush()
        print(f"✅ Created {len(sellers)} sellers")
        
        # 4. Create Workers
        print("\n👷 Creating Workers...")
        workers = []
        for i in range(1, 8):
            worker = Worker(
                telegram_id=500000000 + i,
                username=f"worker_{i}",
                categories=["docs", "pros_fullz"] if i % 2 == 0 else ["docs"],
                services=["dl_lookup", "ssn_lookup"] if i % 2 == 0 else ["dl_lookup"],
                balance=Decimal(f"{200 * i}.00"),
                orders_completed=i * 5,
                is_active=True,
                total_earned=Decimal(f"{800 * i}.00"),
                worker_score=4.2 + (i * 0.1),
                commission_percent=70.0 if i % 2 == 0 else None,
                fixed_price=Decimal("25.00") if i % 2 != 0 else None,
                created_at=datetime.utcnow() - timedelta(days=45-i)
            )
            workers.append(worker)
            session.add(worker)
        
        await session.flush()
        print(f"✅ Created {len(workers)} workers")
        
        # 5. Create Marketers
        print("\n📢 Creating Marketers...")
        marketers = []
        for i in range(1, 4):
            marketer = Marketer(
                telegram_id=600000000 + i,
                username=f"marketer_{i}",
                display_name=f"Marketer{i}",
                language="en",
                promo_code=f"PROMO{i}{random.randint(100, 999)}",
                balance=Decimal(f"{150 * i}.00"),
                total_earned=Decimal(f"{600 * i}.00"),
                is_active=True,
                rules_accepted=True,
                created_at=datetime.utcnow() - timedelta(days=40-i)
            )
            marketers.append(marketer)
            session.add(marketer)
        
        await session.flush()
        print(f"✅ Created {len(marketers)} marketers")
        
        # 6. Create CC Items
        print("\n💳 Creating CC Items...")
        cc_items = []
        card_brands = ["VISA", "MASTERCARD", "AMEX", "DISCOVER"]
        banks = ["Chase", "Bank of America", "Wells Fargo", "Citi", "Capital One"]
        states = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
        
        for i in range(1, 21):
            cc = SellerCCItem(
                seller_id=sellers[i % len(sellers)].id,
                item_name=f"CC {card_brands[i % len(card_brands)]} {banks[i % len(banks)]}",
                cc_code=f"cc_{random_string(8)}",
                category_code="cc_with_fullz",
                product_type="cc",
                product_subtype="with_fullz",
                seller_price=Decimal(f"{40 + i * 2}.00"),
                buyer_price=Decimal(f"{50 + i * 2}.00"),
                base_price=Decimal(f"{45 + i * 2}.00"),
                final_price=Decimal(f"{50 + i * 2}.00"),
                bank_name=banks[i % len(banks)],
                card_brand=card_brands[i % len(card_brands)],
                state=states[i % len(states)],
                zip=f"{10000 + i * 100}",
                city=f"City{i}",
                moderation_status="approved" if i % 4 != 0 else "pending_moderation",
                is_in_stock=True,
                stock_count=random.randint(1, 10),
                created_at=datetime.utcnow() - timedelta(days=20-i%20)
            )
            cc_items.append(cc)
            session.add(cc)
        
        await session.flush()
        print(f"✅ Created {len(cc_items)} CC items")
        
        # 7. Create Logs Items
        print("\n📋 Creating Logs Items...")
        logs_items = []
        for i in range(1, 16):
            log = SellerLogsItem(
                seller_id=sellers[i % len(sellers)].id,
                bank=banks[i % len(banks)],
                total_balance=float(500 + i * 50),
                price=float(30 + i * 3),
                has_cvv=i % 2 == 0,
                bt_available=i % 3 == 0,
                email_valid=i % 2 == 0,
                moderation_status="approved" if i % 3 != 0 else "pending",
                is_in_stock=True,
                created_at=datetime.utcnow() - timedelta(days=15-i%15)
            )
            logs_items.append(log)
            session.add(log)
        
        await session.flush()
        print(f"✅ Created {len(logs_items)} logs items")
        
        # 8. Create Products
        print("\n📦 Creating Products...")
        products = []
        categories = ["docs", "pros_fullz"]
        services = ["dl_front_back", "passport", "ssn_card", "work_travel"]
        
        for i in range(1, 16):
            product = Product(
                seller_id=None,
                uploaded_by=f"worker:{workers[i % len(workers)].id}" if i % 2 == 0 else f"admin:1",
                name=f"Product {i}",
                description=f"Test product description {i}",
                category=categories[i % len(categories)],
                service=services[i % len(services)],
                state=states[i % len(states)],
                price=Decimal(f"{40 + i * 3}.00"),
                base_price=Decimal(f"{35 + i * 3}.00"),
                final_price=Decimal(f"{45 + i * 3}.00"),
                file_path=f"/uploads/products/test_{i}.jpg",
                file_name=f"test_{i}.jpg",
                file_type="image/jpeg",
                is_available=True if i % 5 != 0 else False,
                is_active=True,
                moderation_status="approved" if i % 3 != 0 else "pending_moderation",
                created_at=datetime.utcnow() - timedelta(days=10-i%10)
            )
            products.append(product)
            session.add(product)
        
        await session.flush()
        print(f"✅ Created {len(products)} products")
        
        # 9. Create Orders
        print("\n📦 Creating Orders...")
        orders = []
        order_categories = ["SSN", "DL", "MVR", "FULLZ", "CR"]
        for i in range(1, 21):
            order = Order(
                user_id=users[i % len(users)].user_id,
                mirror_bot_id=mirror_bot1.id if i <= 10 else mirror_bot2.id,
                worker_id=workers[i % len(workers)].id if i % 3 == 0 else None,
                category=order_categories[i % len(order_categories)],
                service_name=services[i % len(services)],
                input_data={"test": f"data_{i}"},
                price=Decimal(f"{50 + i * 5}.00"),
                status="completed" if i % 4 == 0 else ("processing" if i % 4 == 1 else "pending"),
                created_at=datetime.utcnow() - timedelta(days=10-i%10),
                completed_at=datetime.utcnow() - timedelta(days=9-i%9) if i % 4 == 0 else None
            )
            orders.append(order)
            session.add(order)
        
        await session.flush()
        print(f"✅ Created {len(orders)} orders")
        
        # 10. Create Seller CC Orders
        print("\n💳 Creating Seller CC Orders...")
        seller_cc_orders = []
        for i in range(1, 11):
            if i <= len(cc_items):
                cc_order = SellerCCOrder(
                    buyer_user_id=users[i % len(users)].user_id,
                    seller_id=sellers[i % len(sellers)].id,
                    seller_cc_item_id=cc_items[i-1].id,
                    mirror_bot_id=mirror_bot1.id if i <= 5 else mirror_bot2.id,
                    price_for_buyer=Decimal(f"{60 + i * 5}.00"),
                    price_for_seller=Decimal(f"{50 + i * 4}.00"),
                    status="completed" if i % 3 == 0 else ("pending_admin" if i % 3 == 1 else "pending_check"),
                    created_at=datetime.utcnow() - timedelta(days=8-i%8),
                    completed_at=datetime.utcnow() - timedelta(days=7-i%7) if i % 3 == 0 else None
                )
                seller_cc_orders.append(cc_order)
                session.add(cc_order)
        
        await session.flush()
        print(f"✅ Created {len(seller_cc_orders)} seller CC orders")
        
        # 11. Create Transactions
        print("\n💰 Creating Transactions...")
        transactions = []
        tx_types = ["deposit", "order", "withdrawal", "refund", "bonus"]
        for i in range(1, 31):
            tx = Transaction(
                user_id=users[i % len(users)].user_id,
                account_type="user",
                account_id=users[i % len(users)].user_id,
                type=tx_types[i % len(tx_types)],
                amount=Decimal(f"{10 + i * 5}.00"),
                description=f"Test transaction {i}",
                created_at=datetime.utcnow() - timedelta(days=20-i%20)
            )
            transactions.append(tx)
            session.add(tx)
        
        await session.flush()
        print(f"✅ Created {len(transactions)} transactions")
        
        # 12. Create Support Tickets
        print("\n🎫 Creating Support Tickets...")
        tickets = []
        categories = ["payment", "product", "general", "technical", "financial"]
        for i in range(1, 11):
            ticket = SupportTicket(
                user_id=users[i % len(users)].user_id,
                mirror_bot_id=mirror_bot1.id if i <= 5 else mirror_bot2.id,
                category=categories[i % len(categories)],
                subject=f"Test ticket {i}: Need help with order",
                status="open" if i % 3 == 0 else ("in_progress" if i % 3 == 1 else "closed"),
                priority="HIGH" if i % 4 == 0 else ("NORMAL" if i % 4 == 1 else "LOW"),
                created_at=datetime.utcnow() - timedelta(days=5-i%5)
            )
            tickets.append(ticket)
            session.add(ticket)
        
        await session.flush()
        print(f"✅ Created {len(tickets)} support tickets")
        
        # 13. Create Admin Users and Roles
        print("\n👨‍💼 Creating Admin Users...")
        
        # Create custom role
        custom_role = AdminRole(
            name="manager",
            display_name="Manager",
            permissions={
                "dashboard": True,
                "users": True,
                "orders": True,
                "products": True,
                "sellers": False,
                "workers": False,
                "finance": False,
                "settings": False
            },
            created_at=datetime.utcnow()
        )
        session.add(custom_role)
        await session.flush()
        
        # Admin users (password for all: admin123)
        admin_users = [
            Admin(
                username="moderator1",
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIq.Oe9Jai",
                role="moderator",
                is_active=True,
                created_at=datetime.utcnow()
            ),
            Admin(
                username="accountant1",
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIq.Oe9Jai",
                role="accountant",
                is_active=True,
                created_at=datetime.utcnow()
            ),
            Admin(
                username="manager1",
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIq.Oe9Jai",
                role="custom",
                role_id=custom_role.id,
                is_active=True,
                created_at=datetime.utcnow()
            )
        ]
        
        for admin in admin_users:
            session.add(admin)
        
        await session.flush()
        print(f"✅ Created {len(admin_users)} admin users + 1 custom role")
        
        # 14. Create Seller Withdrawals
        print("\n💸 Creating Seller Withdrawals...")
        seller_withdrawals = []
        for i in range(1, 8):
            withdrawal = SellerWithdrawal(
                seller_id=sellers[i % len(sellers)].id,
                amount=Decimal(f"{100 + i * 20}.00"),
                requisites=f"0x{'a' * 40}",
                status="approved" if i % 2 == 0 else "pending",
                created_at=datetime.utcnow() - timedelta(days=3-i%3),
                processed_at=datetime.utcnow() - timedelta(days=2-i%2) if i % 2 == 0 else None
            )
            seller_withdrawals.append(withdrawal)
            session.add(withdrawal)
        
        await session.flush()
        print(f"✅ Created {len(seller_withdrawals)} seller withdrawals")
        
        # 15. Create Worker Withdrawals
        print("\n💵 Creating Worker Withdrawals...")
        worker_withdrawals = []
        for i in range(1, 8):
            withdrawal = WorkerWithdrawal(
                worker_id=workers[i % len(workers)].id,
                amount=Decimal(f"{50 + i * 10}.00"),
                requisites=f"0x{'b' * 40}",
                status="approved" if i % 2 == 0 else "pending",
                created_at=datetime.utcnow() - timedelta(days=3-i%3),
                processed_at=datetime.utcnow() - timedelta(days=2-i%2) if i % 2 == 0 else None
            )
            worker_withdrawals.append(withdrawal)
            session.add(withdrawal)
        
        await session.flush()
        print(f"✅ Created {len(worker_withdrawals)} worker withdrawals")
        
        # Commit all changes
        await session.commit()
        print("\n✨ Test data population completed successfully!")
        print(f"""
📊 Summary:
   - Mirror Bots: 2
   - Users: {len(users)}
   - Sellers: {len(sellers)}
   - Workers: {len(workers)}
   - Marketers: {len(marketers)}
   - CC Items: {len(cc_items)}
   - Logs Items: {len(logs_items)}
   - Products: {len(products)}
   - Orders: {len(orders)}
   - Seller CC Orders: {len(seller_cc_orders)}
   - Transactions: {len(transactions)}
   - Support Tickets: {len(tickets)}
   - Admin Users: {len(admin_users)} + 1 custom role
   - Seller Withdrawals: {len(seller_withdrawals)}
   - Worker Withdrawals: {len(worker_withdrawals)}
        """)


if __name__ == "__main__":
    try:
        asyncio.run(populate_test_data())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
