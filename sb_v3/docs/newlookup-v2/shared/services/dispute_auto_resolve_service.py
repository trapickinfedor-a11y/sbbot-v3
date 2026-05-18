from __future__ import annotations

"""Background watcher: auto-resolve disputes where seller didn't respond within 24h."""
import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 600  # Check every 10 minutes


async def run_dispute_auto_resolve_watcher(
    stop_event: asyncio.Event,
    session_maker: async_sessionmaker,
) -> None:
    """Long-running loop: finds expired disputes and auto-resolves them in buyer's favor."""
    while not stop_event.is_set():
        try:
            await _process_expired_disputes(session_maker)
        except Exception as exc:
            logger.warning("Dispute auto-resolve watcher error: %s", exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CHECK_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


async def _process_expired_disputes(session_maker: async_sessionmaker) -> None:
    from shared.services.seller_dispute_service import SellerDisputeService

    async with session_maker() as session:
        try:
            resolved = await SellerDisputeService.auto_resolve_expired_disputes(session, limit=50)
            if resolved > 0:
                await session.commit()
                logger.info("Auto-resolved %d expired disputes (seller no-response)", resolved)
        except Exception as exc:
            await session.rollback()
            logger.error("Failed to commit auto-resolved disputes: %s", exc)
            raise
