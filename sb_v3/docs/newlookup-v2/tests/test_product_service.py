import unittest
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mirror_bot.services.product_service import ProductService
from shared.database.models import (
    Base,
    MirrorBot,
    Product,
    ProductPurchase,
    Referral,
    Seller,
    Transaction,
    TRANSACTION_STATUS_ON_HOLD,
    User,
)


class ProductServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_purchase_product_marks_item_sold_and_credits_referrer(self) -> None:
        async with self.session_maker() as session:
            mirror_bot = MirrorBot(
                id=1,
                bot_token="token",
                bot_username="mirror_test_bot",
                owner_user_id=999999,
            )
            buyer = User(
                user_id=1001,
                username="buyer",
                mirror_bot_id=1,
                balance=Decimal("100.00"),
                referral_link="buyer-link",
            )
            referrer = User(
                user_id=2002,
                username="referrer",
                mirror_bot_id=1,
                balance=Decimal("10.00"),
                referral_link="ref-link",
            )
            referral = Referral(referrer_id=referrer.user_id, referred_id=buyer.user_id)
            product = Product(
                seller_id=None,
                name="Test Product",
                description="demo",
                category="lookup",
                service="ssn_lookup",
                state="CA",
                price=Decimal("25.00"),
                file_path="/tmp/test-product.txt",
                file_name="test-product.txt",
                file_type="txt",
                is_available=True,
                is_active=True,
                moderation_status="approved",
            )
            session.add_all([mirror_bot, buyer, referrer, referral, product])
            await session.commit()

            result = await ProductService.purchase_product(
                session=session,
                product_id=product.id,
                user_id=buyer.user_id,
                mirror_bot_id=mirror_bot.id,
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["purchase_id"], 1)
            self.assertEqual(result["new_balance"], 75.0)

            await session.refresh(product)
            await session.refresh(buyer)
            await session.refresh(referrer)
            await session.refresh(referral)

            self.assertFalse(product.is_available)
            self.assertEqual(Decimal(str(buyer.balance)), Decimal("75.00"))
            self.assertEqual(Decimal(str(referrer.balance)), Decimal("11.00"))
            self.assertEqual(Decimal(str(referral.earned_total)), Decimal("1.00"))

            purchases = (await session.execute(select(ProductPurchase))).scalars().all()
            self.assertEqual(len(purchases), 1)

            transactions = (await session.execute(select(Transaction).order_by(Transaction.id.asc()))).scalars().all()
            self.assertEqual(len(transactions), 4)
            purchase_tx = next(tx for tx in transactions if tx.type == "purchase")
            referral_tx = next(tx for tx in transactions if tx.type == "referral_bonus")
            self.assertEqual(Decimal(str(purchase_tx.amount)), Decimal("-25.00"))
            self.assertEqual(purchase_tx.status, TRANSACTION_STATUS_ON_HOLD)
            self.assertIsNotNone(purchase_tx.effective_at)
            self.assertEqual(Decimal(str(referral_tx.amount)), Decimal("1.00"))

    async def test_purchase_product_rejects_insufficient_balance_without_side_effects(self) -> None:
        async with self.session_maker() as session:
            mirror_bot = MirrorBot(
                id=1,
                bot_token="token",
                bot_username="mirror_test_bot",
                owner_user_id=999999,
            )
            buyer = User(
                user_id=3003,
                username="poor_buyer",
                mirror_bot_id=1,
                balance=Decimal("5.00"),
                referral_link="poor-link",
            )
            product = Product(
                seller_id=None,
                name="Expensive Product",
                description="demo",
                category="lookup",
                service="ssn_lookup",
                state="NY",
                price=Decimal("25.00"),
                file_path="/tmp/expensive-product.txt",
                file_name="expensive-product.txt",
                file_type="txt",
                is_available=True,
                is_active=True,
                moderation_status="approved",
            )
            session.add_all([mirror_bot, buyer, product])
            await session.commit()

            result = await ProductService.purchase_product(
                session=session,
                product_id=product.id,
                user_id=buyer.user_id,
                mirror_bot_id=mirror_bot.id,
            )

            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "Insufficient balance")

            await session.refresh(product)
            await session.refresh(buyer)

            self.assertTrue(product.is_available)
            self.assertEqual(Decimal(str(buyer.balance)), Decimal("5.00"))
            purchases = (await session.execute(select(ProductPurchase))).scalars().all()
            transactions = (await session.execute(select(Transaction))).scalars().all()
            self.assertEqual(len(purchases), 0)
            self.assertEqual(len(transactions), 0)

    async def test_purchase_product_is_idempotent_for_same_buyer(self) -> None:
        async with self.session_maker() as session:
            mirror_bot = MirrorBot(
                id=1,
                bot_token="token",
                bot_username="mirror_test_bot",
                owner_user_id=999999,
            )
            buyer = User(
                user_id=4004,
                username="repeat_buyer",
                mirror_bot_id=1,
                balance=Decimal("100.00"),
                referral_link="repeat-link",
            )
            product = Product(
                seller_id=None,
                name="Idempotent Product",
                description="demo",
                category="lookup",
                service="ssn_lookup",
                state="TX",
                price=Decimal("25.00"),
                file_path="/tmp/idempotent.txt",
                file_name="idempotent.txt",
                file_type="txt",
                is_available=True,
                is_active=True,
                moderation_status="approved",
            )
            session.add_all([mirror_bot, buyer, product])
            await session.commit()

            first = await ProductService.purchase_product(
                session=session,
                product_id=product.id,
                user_id=buyer.user_id,
                mirror_bot_id=mirror_bot.id,
            )
            second = await ProductService.purchase_product(
                session=session,
                product_id=product.id,
                user_id=buyer.user_id,
                mirror_bot_id=mirror_bot.id,
            )

            self.assertTrue(first["success"])
            self.assertTrue(second["success"])
            self.assertEqual(first["purchase_id"], second["purchase_id"])
            self.assertEqual(first["new_balance"], second["new_balance"])

            purchases = (await session.execute(select(ProductPurchase))).scalars().all()
            transactions = (await session.execute(select(Transaction))).scalars().all()
            self.assertEqual(len(purchases), 1)
            self.assertEqual(len(transactions), 2)

    async def test_get_product_by_id_hides_inactive_or_unapproved_products(self) -> None:
        async with self.session_maker() as session:
            hidden_inactive = Product(
                seller_id=None,
                name="Hidden Inactive",
                description="demo",
                category="lookup",
                service="ssn_lookup",
                state="CA",
                price=Decimal("10.00"),
                file_path="/tmp/hidden-inactive.txt",
                file_name="hidden-inactive.txt",
                file_type="txt",
                is_available=True,
                is_active=False,
                moderation_status="approved",
            )
            hidden_unapproved = Product(
                seller_id=None,
                name="Hidden Unapproved",
                description="demo",
                category="lookup",
                service="ssn_lookup",
                state="CA",
                price=Decimal("10.00"),
                file_path="/tmp/hidden-unapproved.txt",
                file_name="hidden-unapproved.txt",
                file_type="txt",
                is_available=True,
                is_active=True,
                moderation_status="pending_moderation",
            )
            session.add_all([hidden_inactive, hidden_unapproved])
            await session.commit()

            self.assertIsNone(await ProductService.get_product_by_id(session, hidden_inactive.id))
            self.assertIsNone(await ProductService.get_product_by_id(session, hidden_unapproved.id))

    async def test_get_user_purchase_history_applies_filters(self) -> None:
        async with self.session_maker() as session:
            mirror_bot = MirrorBot(
                id=1,
                bot_token="token",
                bot_username="mirror_test_bot",
                owner_user_id=999999,
            )
            user = User(
                user_id=5005,
                username="history_buyer",
                mirror_bot_id=1,
                balance=Decimal("100.00"),
                referral_link="history-link",
            )
            seller_a = Seller(telegram_id=7001, username="seller_a", display_name="Seller A", is_approved=True, is_active=True)
            seller_b = Seller(telegram_id=7002, username="seller_b", display_name="Seller B", is_approved=True, is_active=True)
            product_a = Product(
                seller_id=1,
                name="CA Lookup",
                description="demo",
                category="lookup",
                service="ssn_lookup",
                state="CA",
                price=Decimal("10.00"),
                file_path="/tmp/a.txt",
                file_name="a.txt",
                file_type="txt",
                is_available=False,
                is_active=True,
                moderation_status="approved",
            )
            product_b = Product(
                seller_id=2,
                name="TX Document",
                description="demo",
                category="docs",
                service="passport",
                state="TX",
                price=Decimal("20.00"),
                file_path="/tmp/b.txt",
                file_name="b.txt",
                file_type="txt",
                is_available=False,
                is_active=True,
                moderation_status="approved",
            )
            session.add_all([mirror_bot, user, seller_a, seller_b, product_a, product_b])
            await session.flush()
            session.add_all(
                [
                    ProductPurchase(product_id=product_a.id, user_id=user.user_id),
                    ProductPurchase(product_id=product_b.id, user_id=user.user_id),
                ]
            )
            await session.commit()

            all_history = await ProductService.get_user_purchase_history(
                session,
                user_id=user.user_id,
                mirror_bot_id=mirror_bot.id,
                page=1,
                limit=10,
            )
            lookup_history = await ProductService.get_user_purchase_history(
                session,
                user_id=user.user_id,
                mirror_bot_id=mirror_bot.id,
                page=1,
                limit=10,
                category_id="lookup",
            )
            seller_history = await ProductService.get_user_purchase_history(
                session,
                user_id=user.user_id,
                mirror_bot_id=mirror_bot.id,
                page=1,
                limit=10,
                seller_id=seller_b.id,
            )

            self.assertEqual(all_history["total"], 2)
            self.assertEqual(lookup_history["total"], 1)
            self.assertEqual(lookup_history["items"][0]["product"]["name"], "CA Lookup")
            self.assertEqual(seller_history["total"], 1)
            self.assertEqual(seller_history["items"][0]["seller"]["name"], "Seller B")

    async def test_set_archive_channel_updates_user(self) -> None:
        async with self.session_maker() as session:
            mirror_bot = MirrorBot(
                id=1,
                bot_token="token",
                bot_username="mirror_test_bot",
                owner_user_id=999999,
            )
            user = User(
                user_id=6006,
                username="archiver",
                mirror_bot_id=1,
                balance=Decimal("0.00"),
                referral_link="archive-link",
            )
            session.add_all([mirror_bot, user])
            await session.commit()

            updated = await ProductService.set_archive_channel(
                session,
                user_id=user.user_id,
                mirror_bot_id=mirror_bot.id,
                channel_id=-1001234567890,
            )

            self.assertTrue(updated)
            await session.refresh(user)
            self.assertEqual(user.archive_channel_id, -1001234567890)
