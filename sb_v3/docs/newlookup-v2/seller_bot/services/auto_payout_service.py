from __future__ import annotations

"""Background service: auto-payout for sellers when balance exceeds threshold."""
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from shared.database.models import Seller, SellerWithdrawal

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 3600  # Check every hour


async def run_auto_payout_watcher(
    stop_event: asyncio.Event,
    session_maker: async_sessionmaker,
    bot,
) -> None:
    """Long-running loop that checks seller balances for auto-payout conditions."""
    while not stop_event.is_set():
        try:
            await _process_auto_payouts(session_maker, bot)
        except Exception as exc:
            logger.warning("Auto-payout watcher error: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CHECK_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


async def _process_auto_payouts(session_maker: async_sessionmaker, bot) -> None:
    """Find sellers with auto-payout enabled and balance >= threshold, create withdrawal."""
    async with session_maker() as session:
        result = await session.execute(
            select(Seller).where(
                Seller.auto_payout_enabled == True,
                Seller.is_active == True,
                Seller.access_status == "active",
            )
        )
        sellers = list(result.scalars().all())

        for seller in sellers:
            balance = Decimal(str(getattr(seller, 'withdrawable_balance', 0) or 0))
            threshold = Decimal(str(seller.auto_payout_threshold or 500))  # unified to $500
            if balance < threshold:
                continue

            # Check no pending withdrawal already exists
            existing = await session.scalar(
                select(SellerWithdrawal).where(
                    SellerWithdrawal.seller_id == seller.id,
                    SellerWithdrawal.status == "pending",
                )
            )
            if existing:
                continue

            # Check that the seller has a saved wallet address
            wallet = getattr(seller, "btc_wallet", None) or getattr(seller, "payout_wallet", None)
            if not wallet:
                logger.info("Auto-payout: seller %s has no wallet address configured", seller.id)
                continue

            # Create auto-withdrawal request
            withdrawal = SellerWithdrawal(
                seller_id=seller.id,
                amount=balance,
                wallet_address=wallet,
                status="pending",
                note="Auto-payout (balance threshold reached)",
                created_at=datetime.now(timezone.utc),
            )
            session.add(withdrawal)
            await session.commit()

            logger.info(
                "Auto-payout created for seller %s: amount=%s wallet=%s",
                seller.id, balance, wallet
            )

            # Notify seller
            try:
                await bot.send_message(
                    chat_id=seller.telegram_id,
                    text=(
                        f"💸 <b>Auto-Payout Initiated!</b>\n\n"
                        f"Your balance reached the auto-payout threshold.\n"
                        f"Withdrawal request created for <b>${float(balance):.2f}</b>.\n\n"
                        f"It will be processed shortly."
                    ),
                    parse_mode="HTML",
                )
            except Exception as exc:
                logger.warning("Failed to notify seller %s of auto-payout: %s", seller.telegram_id, exc)
