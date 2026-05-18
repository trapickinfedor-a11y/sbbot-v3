from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    BruteBankItem,
    Seller,
    SellerBank,
    SellerBankItem,
    SellerCCItem,
    SellerCheckItem,
    SellerDepositPayment,
    SellerEnrollItem,
    SellerLogsItem,
    SellerNFCItem,
    SellerOTPItem,
    SellerSelfregCCItem,
)
from shared.services.admin_audit_service import log_admin_action
from shared.services.admin_notification_service import AdminNotificationService
from shared.services.audit_event_service import AuditEventService
from shared.services.btcpay_service import BTCPayService
from shared.services.notification_service import NotificationService
from shared.services.nocodb_service import NocoDBService


PACKAGE_CATEGORIES: dict[str, set[str]] = {
    "bank": {"bank", "enrol", "brute"},
    "cc": {"cc"},
    "bank_plus": {"bank", "enrol", "brute", "logs", "nfc", "otp", "checks"},
    "cc_plus": {"cc", "selfreg_cc"},
    "full": {"bank", "enrol", "brute", "cc", "logs", "nfc", "otp", "checks", "selfreg_cc"},
}

PACKAGE_AMOUNTS: dict[str, Decimal] = {
    "bank": Decimal("100"),
    "cc": Decimal("50"),
    "bank_plus": Decimal("150"),
    "cc_plus": Decimal("100"),
    "full": Decimal("250"),
}


def _money(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class SellerDepositService:
    @staticmethod
    def normalize_payment_status(provider_status: str | None) -> str:
        status = (provider_status or "").strip()
        if BTCPayService.is_paid_status(status):
            return "paid"
        normalized = status.lower()
        if normalized in {"expired", "invalid", "settledinvalid"}:
            return "expired"
        if "refund" in normalized:
            return "refunded"
        if normalized in {"new", "processing"}:
            return "pending"
        return normalized[:20] or "pending"

    @staticmethod
    def package_amount(package_code: str) -> Decimal:
        if package_code not in PACKAGE_AMOUNTS:
            raise ValueError("Unsupported seller deposit package")
        return PACKAGE_AMOUNTS[package_code]

    @staticmethod
    def package_categories(package_code: str) -> set[str]:
        if package_code not in PACKAGE_CATEGORIES:
            raise ValueError("Unsupported seller deposit package")
        return set(PACKAGE_CATEGORIES[package_code])

    @staticmethod
    def package_label(package_code: str) -> str:
        labels = {
            "bank": "Bank package",
            "cc": "CC package",
            "bank_plus": "Bank Plus package",
            "cc_plus": "CC Plus package",
            "full": "Full seller package",
        }
        return labels.get(package_code, package_code)

    @staticmethod
    def seller_is_active(seller: Seller) -> bool:
        access_status = (getattr(seller, "access_status", "") or "").strip().lower()
        if access_status in {"banned", "frozen", "left"}:
            return False
        if seller.seller_type == "internal":
            return True
        return bool(seller.is_approved and seller.is_active and access_status == "active")

    @staticmethod
    def allowed_categories(seller: Seller) -> set[str]:
        if seller.seller_type == "internal":
            return {"bank", "enrol", "brute", "cc", "logs", "nfc", "otp", "checks", "selfreg_cc"}

        categories = getattr(seller, "security_deposit_categories", None) or []
        normalized = {str(item).strip().lower() for item in categories if item}
        if normalized:
            return normalized

        # Backward compatibility for already-approved sellers using the old deposit threshold logic.
        legacy_amount = _money(getattr(seller, "deposit_balance", 0))
        if seller.is_approved and seller.is_active:
            if legacy_amount >= Decimal("150"):
                return {"bank", "enrol", "brute", "cc"}
            if legacy_amount >= Decimal("100"):
                return {"bank", "enrol", "brute"}
            if legacy_amount >= Decimal("50"):
                return {"cc"}
        return set()

    @staticmethod
    def has_upload_access(seller: Seller, item_type: str) -> bool:
        if not SellerDepositService.seller_is_active(seller):
            return False
        return item_type.strip().lower() in SellerDepositService.allowed_categories(seller)

    @staticmethod
    def activate_seller_access(
        seller: Seller,
        *,
        approved_at: Optional[datetime] = None,
        extra_categories: Optional[set[str]] = None,
    ) -> set[str]:
        approved_at = approved_at or datetime.now(timezone.utc)
        merged_categories = SellerDepositService.allowed_categories(seller)
        if extra_categories:
            merged_categories |= {str(item).strip().lower() for item in extra_categories if item}
        if merged_categories:
            seller.security_deposit_categories = sorted(merged_categories)

        if (getattr(seller, "access_status", "") or "").lower() not in {"banned", "left"}:
            seller.is_approved = True
            seller.is_active = True
            seller.access_status = "active" if (seller.seller_type == "internal" or merged_categories) else "pending_deposit"
        if seller.is_approved and not seller.approved_at:
            seller.approved_at = approved_at
        return merged_categories

    @staticmethod
    async def create_btcpay_invoice(
        session: AsyncSession,
        seller: Seller,
        package_code: str,
        *,
        redirect_url: Optional[str] = None,
    ) -> SellerDepositPayment:
        amount = SellerDepositService.package_amount(package_code)
        invoice = await BTCPayService.create_invoice(
            amount=amount,
            package_code=package_code,
            seller_id=seller.id,
            seller_telegram_id=seller.telegram_id,
            title=f"Seller security deposit: {SellerDepositService.package_label(package_code)}",
            redirect_url=redirect_url,
        )
        payment = SellerDepositPayment(
            seller_id=seller.id,
            package_code=package_code,
            categories=sorted(SellerDepositService.package_categories(package_code)),
            amount=amount,
            currency="USD",
            provider="btcpay",
            provider_invoice_id=invoice.invoice_id,
            checkout_url=invoice.checkout_url,
            status="pending",
            raw_payload=invoice.raw_payload,
            expires_at=invoice.expires_at,
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment

    @staticmethod
    async def sync_invoice_status(
        session: AsyncSession,
        invoice_id: str,
        *,
        invoice_payload: Optional[dict] = None,
    ) -> Optional[SellerDepositPayment]:
        payment = await session.scalar(
            select(SellerDepositPayment).where(SellerDepositPayment.provider_invoice_id == str(invoice_id))
        )
        if not payment:
            return None

        if invoice_payload is not None:
            payment.raw_payload = invoice_payload

        normalized_status = SellerDepositService.normalize_payment_status(
            (invoice_payload or {}).get("status")
        )
        if normalized_status == "paid":
            return await SellerDepositService.process_paid_invoice(
                session,
                invoice_id,
                invoice_payload=invoice_payload,
            )

        payment.status = normalized_status
        await session.commit()
        await session.refresh(payment)
        return payment

    @staticmethod
    async def process_paid_invoice(
        session: AsyncSession,
        invoice_id: str,
        *,
        invoice_payload: Optional[dict] = None,
    ) -> Optional[SellerDepositPayment]:
        async with session.begin():
            payment = await session.scalar(
                select(SellerDepositPayment)
                .where(SellerDepositPayment.provider_invoice_id == str(invoice_id))
                .with_for_update()
            )
            if not payment:
                return None
            if payment.status == "paid":
                return payment

            seller = await session.scalar(
                select(Seller).where(Seller.id == payment.seller_id).with_for_update()
            )
            if not seller:
                return None

            package_categories = SellerDepositService.package_categories(payment.package_code)
            merged_categories = SellerDepositService.activate_seller_access(
                seller,
                approved_at=datetime.now(timezone.utc),
                extra_categories=package_categories,
            )

            payment.status = "paid"
            payment.raw_payload = invoice_payload or payment.raw_payload
            payment.paid_at = datetime.now(timezone.utc)

            seller.security_deposit_balance = _money(getattr(seller, "security_deposit_balance", 0)) + _money(payment.amount)
            seller.security_deposit_status = "held"
            seller.security_deposit_paid_at = payment.paid_at
            SellerDepositService.activate_seller_access(
                seller,
                approved_at=payment.paid_at,
                extra_categories=merged_categories,
            )

            await log_admin_action(
                session,
                admin_id=None,
                action="seller_deposit_auto_approved",
                entity_type="seller",
                entity_id=seller.id,
                details={
                    "provider": payment.provider,
                    "invoice_id": payment.provider_invoice_id,
                    "payment_id": payment.id,
                    "package_code": payment.package_code,
                    "amount": float(payment.amount),
                    "allowed_categories": sorted(merged_categories),
                },
                actor_label="system:btcpay",
            )
            await AuditEventService.log(
                session,
                event_type="seller_deposit_paid",
                source="btcpay",
                actor_type="system",
                target_type="seller",
                target_id=seller.id,
                status="paid",
                payload={
                    "payment_id": payment.id,
                    "invoice_id": payment.provider_invoice_id,
                    "package_code": payment.package_code,
                    "amount": float(payment.amount),
                    "allowed_categories": sorted(merged_categories),
                },
            )

            payment_id = payment.id
            payment_amount = payment.amount
            payment_provider = payment.provider
            payment_invoice_id = payment.provider_invoice_id
            payment_package_code = payment.package_code
            payment_paid_at = payment.paid_at
            seller_id = seller.id
            seller_telegram_id = seller.telegram_id
            seller_label = seller.display_name or seller.username or seller.id

        await session.refresh(payment)
        NocoDBService.log_financial_operation(
            user_id=seller_id,
            amount=payment_amount,
            payment_method=payment_provider,
            tx_id=payment_invoice_id,
            operation_type="seller_deposit_paid",
            extra={
                "seller_telegram_id": seller_telegram_id,
                "payment_id": payment_id,
                "package_code": payment_package_code,
                "allowed_categories": sorted(merged_categories),
            },
        )
        NocoDBService.log_event(
            event_type="seller_deposit_access_unlocked",
            actor_type="system",
            actor_id="btcpay",
            target_type="seller",
            target_id=seller_id,
            status="paid",
            payload={
                "payment_id": payment_id,
                "invoice_id": payment_invoice_id,
                "package_code": payment_package_code,
                "amount": float(payment_amount),
                "allowed_categories": sorted(merged_categories),
            },
            timestamp=payment_paid_at,
        )

        await SellerDepositService._notify_seller_payment_success(seller, payment)
        await NotificationService.broadcast(
            roles=["support", "finance", "accountant", "admin", "super_admin"],
            text=(
                "💰 <b>SELLER DEPOSIT PAID</b>\n\n"
                f"🏪 <b>Seller:</b> {seller_label} (#{seller_id})\n"
                f"📦 <b>Package:</b> {SellerDepositService.package_label(payment_package_code)}\n"
                f"💵 <b>Amount:</b> ${float(payment_amount):.2f}\n"
                f"🔓 <b>Access:</b> {', '.join(sorted(merged_categories))}"
            ),
            event_type="seller_deposit_paid_dm",
        )
        return payment

    @staticmethod
    async def ban_seller(
        session: AsyncSession,
        seller: Seller,
        *,
        actor_id: Optional[int],
        reason: str,
        source: str,
        ban_for_leak: bool = False,
    ) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        seller.access_status = "banned"
        seller.is_active = False
        seller.is_banned_for_leak = ban_for_leak
        seller.security_deposit_status = "withheld"
        seller.ban_reason = reason
        seller.banned_at = now
        seller.banned_by = actor_id

        bank_rows = (
            await session.execute(select(SellerBank).where(SellerBank.seller_id == seller.id, SellerBank.is_active == True))
        ).scalars().all()
        cc_rows = (
            await session.execute(select(SellerCCItem).where(SellerCCItem.seller_id == seller.id, SellerCCItem.is_active == True))
        ).scalars().all()
        nfc_rows = (
            await session.execute(select(SellerNFCItem).where(SellerNFCItem.seller_id == seller.id, SellerNFCItem.is_active == True))
        ).scalars().all()
        enroll_rows = (
            await session.execute(
                select(SellerEnrollItem).where(SellerEnrollItem.seller_id == seller.id, SellerEnrollItem.is_active == True)
            )
        ).scalars().all()
        # Note: selfreg_ba has been merged with bank items
        logs_rows = (
            await session.execute(select(SellerLogsItem).where(SellerLogsItem.seller_id == seller.id, SellerLogsItem.is_active == True))
        ).scalars().all()
        otp_rows = (
            await session.execute(select(SellerOTPItem).where(SellerOTPItem.seller_id == seller.id, SellerOTPItem.is_active == True))
        ).scalars().all()
        selfreg_cc_rows = (
            await session.execute(
                select(SellerSelfregCCItem).where(SellerSelfregCCItem.seller_id == seller.id, SellerSelfregCCItem.is_active == True)
            )
        ).scalars().all()
        check_rows = (
            await session.execute(select(SellerCheckItem).where(SellerCheckItem.seller_id == seller.id, SellerCheckItem.is_active == True))
        ).scalars().all()
        brute_rows = (
            await session.execute(select(BruteBankItem).where(BruteBankItem.seller_id == seller.id, BruteBankItem.is_active == True))
        ).scalars().all()

        def _suspend_stock_row(row) -> None:
            row.is_active = False
            if hasattr(row, "is_in_stock"):
                row.is_in_stock = False
            row.moderation_status = "suspended"
            row.moderation_comment = reason
            row.moderated_at = now
            row.moderated_by = actor_id

        for row in bank_rows:
            _suspend_stock_row(row)

        for row in cc_rows:
            _suspend_stock_row(row)

        for row in nfc_rows:
            _suspend_stock_row(row)

        for row in enroll_rows:
            _suspend_stock_row(row)

        for row in logs_rows:
            _suspend_stock_row(row)

        for row in otp_rows:
            _suspend_stock_row(row)

        for row in selfreg_cc_rows:
            _suspend_stock_row(row)

        for row in check_rows:
            _suspend_stock_row(row)

        for row in brute_rows:
            row.is_active = False
            row.status = "removed"
            row.moderation_comment = reason
            row.moderated_by = actor_id

        await session.commit()
        await AuditEventService.log(
            session,
            event_type="seller_banned",
            source=source,
            actor_type="admin" if actor_id else "system",
            actor_id=actor_id,
            target_type="seller",
            target_id=seller.id,
            status="withheld" if ban_for_leak else "banned",
            payload={
                "reason": reason,
                "ban_for_leak": ban_for_leak,
                "security_deposit_status": seller.security_deposit_status,
            },
            commit=True,
        )

        await AdminNotificationService.notify_admin_action(
            "SELLER BANNED",
            [
                f"🏪 <b>Seller:</b> {seller.display_name or seller.username or seller.id} (#{seller.id})",
                f"🆔 <b>Telegram ID:</b> <code>{seller.telegram_id}</code>",
                f"📝 <b>Reason:</b> {reason}",
                f"📍 <b>Source:</b> {source}",
                f"💸 <b>Deposit:</b> withheld",
            ],
            event_type="seller_banned",
            urgent=True,
        )
        await SellerDepositService._notify_seller_banned(seller, reason)
        return {
            "banks_disabled": len(bank_rows),
            "cc_disabled": len(cc_rows),
            "nfc_disabled": len(nfc_rows),
            "enroll_disabled": len(enroll_rows),
            "logs_disabled": len(logs_rows),
            "otp_disabled": len(otp_rows),
            "selfreg_cc_disabled": len(selfreg_cc_rows),
            "checks_disabled": len(check_rows),
            "brute_disabled": len(brute_rows),
            "ban_for_leak": int(ban_for_leak),
        }

    @staticmethod
    async def request_exit(
        session: AsyncSession,
        seller: Seller,
        *,
        actor_id: Optional[int],
        source: str,
    ) -> None:
        if (getattr(seller, "access_status", "") or "").lower() == "banned":
            raise ValueError("Banned sellers cannot request a deposit refund")

        now = datetime.now(timezone.utc)
        seller.access_status = "left"
        seller.is_active = False
        seller.leave_requested_at = now
        seller.left_at = now
        if _money(getattr(seller, "security_deposit_balance", 0)) > 0:
            seller.security_deposit_status = "refund_pending"

        for row in (await session.execute(select(SellerBank).where(SellerBank.seller_id == seller.id))).scalars().all():
            row.is_active = False
            row.is_in_stock = False
        for row in (await session.execute(select(SellerCCItem).where(SellerCCItem.seller_id == seller.id))).scalars().all():
            row.is_active = False
        for row in (await session.execute(select(BruteBankItem).where(BruteBankItem.seller_id == seller.id))).scalars().all():
            row.is_active = False
            row.status = "removed"

        await session.commit()
        await AuditEventService.log(
            session,
            event_type="seller_exit_requested",
            source=source,
            actor_type="seller",
            actor_id=actor_id or seller.telegram_id,
            target_type="seller",
            target_id=seller.id,
            status=seller.security_deposit_status or "left",
            payload={
                "refundable_amount": float(_money(getattr(seller, "security_deposit_balance", 0))),
            },
            commit=True,
        )

        await AdminNotificationService.notify_admin_action(
            "SELLER EXIT REQUEST",
            [
                f"🏪 <b>Seller:</b> {seller.display_name or seller.username or seller.id} (#{seller.id})",
                f"💵 <b>Refundable deposit:</b> ${float(_money(getattr(seller, 'security_deposit_balance', 0))):.2f}",
                f"📍 <b>Source:</b> {source}",
                f"👤 <b>Actor ID:</b> <code>{actor_id or 0}</code>",
            ],
            event_type="seller_exit_requested",
            urgent=True,
        )

    @staticmethod
    async def _notify_seller_payment_success(seller: Seller, payment: SellerDepositPayment) -> None:
        token = os.getenv("SELLER_BOT_TOKEN", "").strip()
        if not token:
            return
        text = (
            "✅ <b>Your security deposit is confirmed.</b>\n\n"
            f"📦 Package: {SellerDepositService.package_label(payment.package_code)}\n"
            f"💵 Amount: ${float(payment.amount):.2f}\n\n"
            "Seller panel access is now active."
        )
        bot = Bot(token=token)
        try:
            await bot.send_message(seller.telegram_id, text)
        finally:
            await bot.session.close()

    @staticmethod
    async def _notify_seller_banned(seller: Seller, reason: str) -> None:
        token = os.getenv("SELLER_BOT_TOKEN", "").strip()
        if not token:
            return
        text = (
            "🚫 <b>Your seller account has been banned.</b>\n\n"
            "All products were removed from sale and the security deposit was withheld.\n\n"
            f"Reason: {reason}"
        )
        bot = Bot(token=token)
        try:
            await bot.send_message(seller.telegram_id, text)
        finally:
            await bot.session.close()
