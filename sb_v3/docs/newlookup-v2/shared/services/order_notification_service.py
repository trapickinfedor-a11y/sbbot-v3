"""
Общий сервис уведомлений о заказах
"""

import asyncio
import logging
import aiohttp
from typing import Optional
from shared.security.internal_api import build_internal_api_headers

logger = logging.getLogger(__name__)


class OrderNotificationService:
    """Сервис для отправки уведомлений о заказах через HTTP API"""

    @staticmethod
    async def _post_with_retry(url: str, order_data: dict, *, event_type: str, timeout_seconds: int = 5) -> bool:
        from shared.services.notification_log_service import fire_log

        order_id = order_data.get("id")
        last_error = "unknown error"

        for attempt in range(1, 4):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                    async with session.post(
                        url,
                        json=order_data,
                        headers=build_internal_api_headers(),
                        timeout=aiohttp.ClientTimeout(total=timeout_seconds),
                    ) as response:
                        if response.status == 200:
                            logger.info("%s sent successfully for order %s on attempt %s", event_type, order_id, attempt)
                            fire_log(
                                event_type=event_type,
                                channel="http_api",
                                status="sent",
                                related_id=order_id,
                                related_type="order",
                                payload={"attempt": attempt, "order_id": order_id},
                            )
                            return True
                        last_error = f"HTTP {response.status}"
            except aiohttp.ClientError as exc:
                last_error = f"Network error: {exc}"
            except Exception as exc:
                last_error = str(exc)

            logger.warning("%s failed for order %s on attempt %s: %s", event_type, order_id, attempt, last_error)
            if attempt < 3:
                await asyncio.sleep(attempt)

        fire_log(
            event_type=event_type,
            channel="http_api",
            status="failed",
            related_id=order_id,
            related_type="order",
            error_message=last_error,
            payload={"order_id": order_id, "attempts": 3},
        )
        return False
    
    @staticmethod
    async def notify_new_order(order_data: dict) -> bool:
        """
        Уведомить worker bot о новом заказе через HTTP API

        Returns:
            bool: Успешность отправки
        """
        import os
        try:
            base_url = (
                os.getenv("WORKER_BOT_URL")
                or os.getenv("WORKER_BOT_API_URL")
                or os.getenv("SUPPORT_BOT_URL")
                or "http://worker_bot:8181"
            ).rstrip("/")
            worker_bot_url = base_url + "/api/notifications/new-order"
            return await OrderNotificationService._post_with_retry(
                worker_bot_url,
                order_data,
                event_type="new_order_to_worker",
            )
        except Exception as e:
            logger.error(f"Failed to send order notification: {e}")
            return False
    
    @staticmethod
    async def send_order_to_channel(order_data: dict) -> bool:
        """
        Публичная отправка заказов в каналы отключена.

        Returns:
            bool: Всегда False
        """
        logger.info("Skipping order-to-channel for order %s: DM-only notifications enabled", order_data.get("id"))
        return False