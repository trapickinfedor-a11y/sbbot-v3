import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.models import (
    AdminAuditLog,
    Base,
    BruteBankItem,
    Seller,
    SellerBank,
    SellerCCItem,
    SellerCheckItem,
    SellerDepositPayment,
    SellerNFCItem,
    SellerOTPItem,
    SellerSelfregCCItem,
)
from shared.services.seller_deposit_service import SellerDepositService


class SellerDepositServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_process_paid_invoice_auto_approves_seller_and_writes_audit(self) -> None:
        async with self.session_maker() as session:
            seller = Seller(
                telegram_id=111111,
                username="seller_one",
                display_name="Seller One",
                seller_type="external",
                is_approved=False,
                is_active=False,
                access_status="pending_deposit",
            )
            session.add(seller)
            await session.commit()
            await session.refresh(seller)

            payment = SellerDepositPayment(
                seller_id=seller.id,
                package_code="bank",
                categories=["bank", "enrol", "brute"],
                amount=Decimal("100.00"),
                currency="USD",
                provider="btcpay",
                provider_invoice_id="inv-auto-1",
                status="pending",
            )
            session.add(payment)
            await session.commit()

            with patch("shared.services.admin_audit_service.LogChannelService.send", new=AsyncMock()), patch(
                "shared.services.seller_deposit_service.AdminNotificationService.notify_admin_action",
                new=AsyncMock(),
            ), patch(
                "shared.services.seller_deposit_service.NotificationService.broadcast",
                new=AsyncMock(),
            ), patch(
                "shared.services.seller_deposit_service.SellerDepositService._notify_seller_payment_success",
                new=AsyncMock(),
            ):
                processed = await SellerDepositService.process_paid_invoice(
                    session,
                    "inv-auto-1",
                    invoice_payload={"id": "inv-auto-1", "status": "Settled"},
                )

            self.assertIsNotNone(processed)
            await session.refresh(seller)
            await session.refresh(payment)

            self.assertEqual(payment.status, "paid")
            self.assertTrue(seller.is_approved)
            self.assertTrue(seller.is_active)
            self.assertEqual(seller.access_status, "active")
            self.assertEqual(seller.security_deposit_status, "held")
            self.assertEqual(Decimal(str(seller.security_deposit_balance)), Decimal("100.00"))
            self.assertEqual(set(seller.security_deposit_categories or []), {"bank", "enrol", "brute"})

            audit_rows = (
                await session.execute(
                    select(AdminAuditLog).where(AdminAuditLog.action == "seller_deposit_auto_approved")
                )
            ).scalars().all()
            self.assertEqual(len(audit_rows), 1)
            self.assertEqual(audit_rows[0].entity_id, seller.id)

    async def test_sync_invoice_status_updates_pending_payment_without_unlock(self) -> None:
        async with self.session_maker() as session:
            seller = Seller(
                telegram_id=333333,
                username="seller_three",
                display_name="Seller Three",
                seller_type="external",
                is_approved=False,
                is_active=False,
                access_status="pending_deposit",
            )
            session.add(seller)
            await session.commit()
            await session.refresh(seller)

            payment = SellerDepositPayment(
                seller_id=seller.id,
                package_code="cc",
                categories=["cc"],
                amount=Decimal("50.00"),
                currency="USD",
                provider="btcpay",
                provider_invoice_id="inv-pending-1",
                status="pending",
            )
            session.add(payment)
            await session.commit()

            synced = await SellerDepositService.sync_invoice_status(
                session,
                "inv-pending-1",
                invoice_payload={"id": "inv-pending-1", "status": "New"},
            )

            self.assertIsNotNone(synced)
            await session.refresh(seller)
            await session.refresh(payment)

            self.assertEqual(payment.status, "pending")
            self.assertFalse(seller.is_approved)
            self.assertFalse(seller.is_active)
            self.assertEqual(seller.access_status, "pending_deposit")

    async def test_ban_seller_for_leak_disables_all_inventory_types(self) -> None:
        async with self.session_maker() as session:
            seller = Seller(
                telegram_id=222222,
                username="seller_two",
                display_name="Seller Two",
                seller_type="external",
                is_approved=True,
                is_active=True,
                access_status="active",
                security_deposit_balance=Decimal("150.00"),
                security_deposit_status="held",
            )
            session.add(seller)
            await session.commit()
            await session.refresh(seller)

            bank = SellerBank(
                seller_id=seller.id,
                bank_name="Chase",
                bank_code="chase",
                category="personal",
                seller_price=Decimal("50.00"),
                buyer_price=Decimal("60.00"),
                stock_count=1,
                is_in_stock=True,
                is_active=True,
            )
            cc = SellerCCItem(
                seller_id=seller.id,
                item_name="Visa",
                cc_code="visa_gold",
                category_code="standard",
                seller_price=Decimal("25.00"),
                buyer_price=Decimal("30.00"),
                stock_count=1,
                is_in_stock=True,
                is_active=True,
            )
            nfc = SellerNFCItem(
                seller_id=seller.id,
                item_name="Apple Pay",
                nfc_type="ap",
                bank_name="BoA",
                country="US",
                seller_price=Decimal("40.00"),
                buyer_price=Decimal("48.00"),
                data_file_path="/tmp/nfc.bin",
                is_in_stock=True,
                is_active=True,
            )
            otp = SellerOTPItem(
                seller_id=seller.id,
                item_name="OTP Card",
                bank_name="Wells Fargo",
                balance=Decimal("100.00"),
                sms_access_type="seller_mediated",
                seller_price=Decimal("35.00"),
                buyer_price=Decimal("42.00"),
                is_in_stock=True,
                is_active=True,
            )
            selfreg = SellerSelfregCCItem(
                seller_id=seller.id,
                item_name="Selfreg",
                bank_name="Citi",
                seller_price=Decimal("45.00"),
                buyer_price=Decimal("54.00"),
                is_in_stock=True,
                is_active=True,
            )
            check = SellerCheckItem(
                seller_id=seller.id,
                item_name="Cashier Check",
                check_type="cashier",
                bank_name="PNC",
                amount=Decimal("500.00"),
                scan_file_path="/tmp/check.png",
                seller_price=Decimal("20.00"),
                buyer_price=Decimal("24.00"),
                is_in_stock=True,
                is_active=True,
            )
            brute = BruteBankItem(
                seller_id=seller.id,
                bank_name="Navy",
                bank_code="navy",
                category="personal",
                credentials={"login": "u", "password": "p"},
                price=Decimal("70.00"),
                is_active=True,
                status="available",
            )
            session.add_all([bank, cc, nfc, otp, selfreg, check, brute])
            await session.commit()

            with patch(
                "shared.services.seller_deposit_service.AdminNotificationService.notify_admin_action",
                new=AsyncMock(),
            ), patch(
                "shared.services.seller_deposit_service.SellerDepositService._notify_seller_banned",
                new=AsyncMock(),
            ):
                affected = await SellerDepositService.ban_seller(
                    session,
                    seller,
                    actor_id=999999,
                    reason="Confirmed data leak",
                    source="test",
                    ban_for_leak=True,
                )

            await session.refresh(seller)
            for row in (bank, cc, nfc, otp, selfreg, check, brute):
                await session.refresh(row)

            self.assertFalse(seller.is_active)
            self.assertTrue(seller.is_banned_for_leak)
            self.assertEqual(seller.access_status, "banned")
            self.assertEqual(seller.security_deposit_status, "withheld")

            self.assertFalse(bank.is_active)
            self.assertFalse(bank.is_in_stock)
            self.assertEqual(bank.moderation_status, "suspended")
            self.assertFalse(cc.is_active)
            self.assertFalse(cc.is_in_stock)
            self.assertEqual(cc.moderation_status, "suspended")
            self.assertFalse(nfc.is_active)
            self.assertFalse(nfc.is_in_stock)
            self.assertEqual(nfc.moderation_status, "suspended")
            self.assertFalse(otp.is_active)
            self.assertFalse(otp.is_in_stock)
            self.assertEqual(otp.moderation_status, "suspended")
            self.assertFalse(selfreg.is_active)
            self.assertFalse(selfreg.is_in_stock)
            self.assertEqual(selfreg.moderation_status, "suspended")
            self.assertFalse(check.is_active)
            self.assertFalse(check.is_in_stock)
            self.assertEqual(check.moderation_status, "suspended")
            self.assertFalse(brute.is_active)
            self.assertEqual(brute.status, "removed")

            self.assertEqual(affected["banks_disabled"], 1)
            self.assertEqual(affected["cc_disabled"], 1)
            self.assertEqual(affected["nfc_disabled"], 1)
            self.assertEqual(affected["otp_disabled"], 1)
            self.assertEqual(affected["selfreg_cc_disabled"], 1)
            self.assertEqual(affected["checks_disabled"], 1)
            self.assertEqual(affected["brute_disabled"], 1)


if __name__ == "__main__":
    unittest.main()
