import unittest
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mirror_bot.services.user_service import UserService
from shared.database.models import (
    Base,
    BotOwner,
    BotOwnerStats,
    Marketer,
    MarketerActivityLog,
    MarketerStats,
    MirrorBot,
    Referral,
    Transaction,
    User,
)


class UserServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_add_balance_updates_user_and_creates_transaction(self) -> None:
        async with self.session_maker() as session:
            user = User(
                user_id=920001,
                username="topup_user",
                mirror_bot_id=1,
                balance=Decimal("5.00"),
                referral_link="topup-user-link",
            )
            session.add(user)
            await session.commit()

            balance = await UserService.add_balance(
                session,
                user_id=user.user_id,
                amount=Decimal("10.00"),
                mirror_bot_id=1,
                description="Top-up test",
            )

            self.assertEqual(Decimal(str(balance)), Decimal("15.00"))
            await session.refresh(user)
            self.assertEqual(Decimal(str(user.balance)), Decimal("15.00"))

            tx_rows = (await session.execute(select(Transaction))).scalars().all()
            self.assertEqual(len(tx_rows), 2)
            self.assertEqual(tx_rows[-1].type, "topup")
            self.assertEqual(Decimal(str(tx_rows[-1].amount)), Decimal("10.00"))

    async def test_add_balance_with_marketer_applies_reward_bonus_and_owner_commission(self) -> None:
        async with self.session_maker() as session:
            mirror_bot = MirrorBot(
                id=1,
                bot_token="bot-token",
                bot_username="mirror_bot_test",
                owner_user_id=930003,
            )
            marketer = Marketer(
                id=1,
                telegram_id=930001,
                username="marketer",
                display_name="Marketer",
                promo_code="PROMO1",
                reward_percent=Decimal("7.0"),
                user_bonus_percent=Decimal("3.0"),
                balance=Decimal("0.00"),
                total_earned=Decimal("0.00"),
                is_active=True,
            )
            user = User(
                user_id=930002,
                username="buyer_marketer",
                mirror_bot_id=1,
                balance=Decimal("0.00"),
                marketer_id=marketer.id,
                first_topup_bonus_applied=False,
                referral_link="buyer-marketer-link",
            )
            session.add_all([mirror_bot, marketer, user])
            await session.commit()

            new_balance = await UserService.add_balance_with_marketer(
                session,
                user_id=user.user_id,
                amount=Decimal("100.00"),
                mirror_bot_id=mirror_bot.id,
                description="Top-up with marketer",
            )

            self.assertEqual(Decimal(str(new_balance)), Decimal("103.00"))
            await session.refresh(user)
            await session.refresh(marketer)

            owner = await session.scalar(select(BotOwner).where(BotOwner.owner_user_id == mirror_bot.owner_user_id))
            self.assertIsNotNone(owner)

            self.assertEqual(Decimal(str(user.balance)), Decimal("103.00"))
            self.assertTrue(user.first_topup_bonus_applied)
            self.assertEqual(Decimal(str(marketer.balance)), Decimal("7.00"))
            self.assertEqual(Decimal(str(marketer.total_earned)), Decimal("7.00"))
            self.assertEqual(Decimal(str(owner.balance)), Decimal("7.00"))
            self.assertEqual(Decimal(str(owner.total_earned)), Decimal("7.00"))

            tx_rows = (await session.execute(select(Transaction).order_by(Transaction.id.asc()))).scalars().all()
            self.assertEqual(len(tx_rows), 4)
            self.assertEqual(tx_rows[0].type, "topup")
            self.assertEqual(tx_rows[1].type, "commission")
            self.assertEqual(tx_rows[2].type, "marketer_bonus")
            self.assertEqual(tx_rows[3].type, "commission")

            marketer_stats = (await session.execute(select(MarketerStats))).scalars().all()
            self.assertEqual(len(marketer_stats), 1)
            self.assertEqual(Decimal(str(marketer_stats[0].topup_amount)), Decimal("100.00"))
            self.assertEqual(Decimal(str(marketer_stats[0].earned)), Decimal("7.00"))
            self.assertEqual(marketer_stats[0].first_topups, 1)

            marketer_logs = (await session.execute(select(MarketerActivityLog))).scalars().all()
            self.assertEqual(len(marketer_logs), 1)
            self.assertEqual(Decimal(str(marketer_logs[0].amount)), Decimal("7.00"))

            owner_stats = (await session.execute(select(BotOwnerStats))).scalars().all()
            self.assertEqual(len(owner_stats), 1)
            self.assertEqual(Decimal(str(owner_stats[0].topped_up)), Decimal("100.00"))
            self.assertEqual(Decimal(str(owner_stats[0].owner_income)), Decimal("7.00"))

    async def test_get_or_create_user_ignores_self_referrer(self) -> None:
        async with self.session_maker() as session:
            user, created = await UserService.get_or_create_user(
                session,
                user_id=930010,
                mirror_bot_id=1,
                referrer_id=930010,
                username="self_ref",
                return_created=True,
            )

            self.assertTrue(created)
            self.assertIsNone(user.referrer_id)
            referrals = (await session.execute(select(Referral))).scalars().all()
            self.assertEqual(len(referrals), 0)

    async def test_apply_promo_code_with_options_links_marketer_once(self) -> None:
        async with self.session_maker() as session:
            marketer = Marketer(
                id=2,
                telegram_id=930020,
                username="promo_marketer",
                display_name="Promo Marketer",
                promo_code="HELLO100",
                is_active=True,
            )
            user = User(
                user_id=930021,
                username="promo_user",
                mirror_bot_id=1,
                balance=Decimal("0.00"),
                referral_link="promo-user-link",
            )
            session.add_all([marketer, user])
            await session.commit()

            applied = await UserService.apply_promo_code_with_options(
                session,
                user_id=user.user_id,
                mirror_bot_id=1,
                promo_code="hello100",
                count_registration=False,
            )
            self.assertTrue(applied)
            await session.refresh(user)
            self.assertEqual(user.marketer_id, marketer.id)

            second_apply = await UserService.apply_promo_code_with_options(
                session,
                user_id=user.user_id,
                mirror_bot_id=1,
                promo_code="hello100",
                count_registration=False,
            )
            self.assertFalse(second_apply)
