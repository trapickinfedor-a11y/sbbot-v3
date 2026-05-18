"""
Сервис уведомлений для админов о ВСЕХ операциях системы.
Отправляет уведомления всем admin_ids через support bot.
"""

import logging
import os
from typing import Optional, List
from aiogram import Bot
from aiogram.enums import ParseMode
from datetime import datetime, timezone

from shared.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN", "")


class AdminNotificationService:
    """Централизованный сервис уведомлений для админов обо всех операциях"""

    _bot: Optional[Bot] = None

    @classmethod
    def init(cls, bot: Bot):
        cls._bot = bot

    @classmethod
    def _get_bot(cls) -> Optional[Bot]:
        if cls._bot:
            return cls._bot
        if SUPPORT_BOT_TOKEN:
            return Bot(token=SUPPORT_BOT_TOKEN)
        return None

    @classmethod
    async def _send_to_admins(
        cls,
        text: str,
        event_type: str = "admin_notification",
        urgent: bool = False,
    ):
        from shared.services.notification_log_service import fire_log

        if not ADMIN_IDS:
            return
        bot = cls._get_bot()
        if not bot:
            logger.warning("AdminNotificationService: no bot available")
            fire_log(
                event_type=event_type,
                channel="admin",
                status="failed",
                error_message="No bot available",
                payload={"text": text[:500]},
            )
            return
        need_close = bot != cls._bot
        try:
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=text,
                        parse_mode=ParseMode.HTML
                    )
                    fire_log(
                        event_type=event_type,
                        channel="admin",
                        status="sent",
                        recipient_id=admin_id,
                        payload={"text_preview": text[:200]},
                    )
                except Exception as e:
                    logger.error(f"Failed to send admin notification to {admin_id}: {e}")
                    fire_log(
                        event_type=event_type,
                        channel="admin",
                        status="failed",
                        recipient_id=admin_id,
                        error_message=str(e),
                        payload={"text": text[:500]},
                    )
        finally:
            if need_close:
                await bot.session.close()

    @classmethod
    async def notify_admin_action(
        cls,
        title: str,
        lines: list[str],
        event_type: str = "admin_action",
        urgent: bool = False,
    ):
        """Generic notification helper for admin/support actions."""
        prefix = "! " if urgent else ""
        body = "\n".join(line for line in lines if line)
        text = f"""{prefix}<b>{title}</b>

{body}
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"""
        await cls._send_to_admins(text, event_type=event_type, urgent=urgent)

    # ===================== ORDERS =====================

    @classmethod
    async def notify_new_order(
        cls,
        order_id: int,
        user_id: int,
        service_name: str,
        category: str,
        price: float,
        is_bulk: bool = False,
        bulk_count: int = 1,
        input_data: Optional[dict] = None
    ):
        order_type = "BULK" if is_bulk else "Single"
        bulk_info = f" ({bulk_count} items)" if is_bulk else ""

        customer_lines = ""
        if input_data:
            for k, v in input_data.items():
                if v and k not in ("price", "service", "category", "status", "id"):
                    customer_lines += f"   • <b>{k.replace('_', ' ').title()}:</b> <code>{v}</code>\n"

        text = f"""🆕 <b>NEW ORDER</b>

📦 <b>Order #{order_id}</b> ({order_type}{bulk_info})
🔧 <b>Service:</b> {service_name}
📂 <b>Category:</b> {category}
💰 <b>Price:</b> ${price:.2f}
👤 <b>User:</b> <code>{user_id}</code>
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"""

        if customer_lines:
            text += f"\n\n👤 <b>Data:</b>\n{customer_lines}"
        await NotificationService.broadcast(
            roles=["moderator", "admin", "super_admin"],
            text=text,
            event_type="new_order",
        )

    @classmethod
    async def notify_order_taken(
        cls,
        order_id: int,
        service_name: str,
        worker_username: str,
        worker_id: int,
        user_id: int
    ):
        text = f"""🔥 <b>ORDER TAKEN</b>

📦 <b>Order #{order_id}</b>
🔧 <b>Service:</b> {service_name}
👷 <b>Worker:</b> @{worker_username} (ID: {worker_id})
👤 <b>Client:</b> <code>{user_id}</code>
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"""

        await cls._send_to_admins(text, event_type="order_taken", urgent=True)

    @classmethod
    async def notify_order_completed(
        cls,
        order_id: int,
        service_name: str,
        result_status: str,
        worker_username: str,
        worker_id: int,
        user_id: int,
        price: float = 0,
        refund_amount: float = 0
    ):
        status_emoji = "✅" if result_status == "done" else "❌"
        status_text = "DONE" if result_status == "done" else "NOT FOUND"

        text = f"""{status_emoji} <b>ORDER {status_text}</b>

📦 <b>Order #{order_id}</b>
🔧 <b>Service:</b> {service_name}
📊 <b>Result:</b> {status_text}
👷 <b>Worker:</b> @{worker_username} (ID: {worker_id})
👤 <b>Client:</b> <code>{user_id}</code>"""

        if result_status == "done" and price > 0:
            text += f"\n💰 <b>Income:</b> ${price:.2f}"
        if result_status == "nf" and refund_amount > 0:
            text += f"\n💸 <b>Refunded:</b> ${refund_amount:.2f}"

        text += f"\n⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"

        await cls._send_to_admins(text, event_type="order_completed", urgent=result_status != "done")

    @classmethod
    async def notify_order_cancelled(
        cls,
        order_id: int,
        service_name: str,
        user_id: int,
        refund_amount: float = 0,
        reason: str = "",
        worker_username: str = "",
        worker_id: int = 0
    ):
        text = f"""🚫 <b>ORDER CANCELLED</b>

📦 <b>Order #{order_id}</b>
🔧 <b>Service:</b> {service_name}
👤 <b>Client:</b> <code>{user_id}</code>"""

        if worker_username:
            text += f"\n👷 <b>Worker:</b> @{worker_username} (ID: {worker_id})"
        if refund_amount > 0:
            text += f"\n💸 <b>Refunded:</b> ${refund_amount:.2f}"
        if reason:
            text += f"\n📝 <b>Reason:</b> {reason}"

        text += f"\n⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"

        await cls._send_to_admins(text, event_type="order_cancelled", urgent=True)

    @classmethod
    async def notify_bulk_order_completed(
        cls,
        order_id: int,
        service_name: str,
        worker_username: str,
        worker_id: int,
        user_id: int,
        done_count: int = 0,
        nf_count: int = 0,
        total_count: int = 0,
        total_income: float = 0,
        total_refund: float = 0
    ):
        text = f"""📦 <b>BULK ORDER COMPLETED</b>

📦 <b>Order #{order_id}</b>
🔧 <b>Service:</b> {service_name}
👷 <b>Worker:</b> @{worker_username} (ID: {worker_id})
👤 <b>Client:</b> <code>{user_id}</code>

📊 <b>Results:</b>
   ✅ Done: {done_count}
   ❌ NF: {nf_count}
   📋 Total: {total_count}

💰 <b>Income:</b> ${total_income:.2f}
💸 <b>Refunded:</b> ${total_refund:.2f}
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"""

        await cls._send_to_admins(text, event_type="bulk_order_completed")

    @classmethod
    async def notify_bulk_item_completed(
        cls,
        order_id: int,
        item_number: int,
        service_name: str,
        result_status: str,
        worker_username: str,
        worker_id: int,
        user_id: int,
        refund_amount: float = 0
    ):
        status_emoji = "✅" if result_status == "done" else "❌"
        status_text = "DONE" if result_status == "done" else "NF"

        text = f"""{status_emoji} <b>BULK ITEM {status_text}</b>

📦 <b>Order #{order_id} — Item #{item_number}</b>
🔧 <b>Service:</b> {service_name}
👷 <b>Worker:</b> @{worker_username} (ID: {worker_id})
👤 <b>Client:</b> <code>{user_id}</code>"""

        if result_status == "nf" and refund_amount > 0:
            text += f"\n💸 <b>Refunded:</b> ${refund_amount:.2f}"

        text += f"\n⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"

        await cls._send_to_admins(text, event_type="bulk_item_completed", urgent=result_status == "nf")

    @classmethod
    async def notify_addinfo_set(
        cls,
        order_id: int,
        service_name: str,
        worker_username: str,
        worker_id: int,
        user_id: int,
        wait_hours: int
    ):
        text = f"""⏰ <b>ADD INFO TIME SET</b>

📦 <b>Order #{order_id}</b>
🔧 <b>Service:</b> {service_name}
👷 <b>Worker:</b> @{worker_username} (ID: {worker_id})
👤 <b>Client:</b> <code>{user_id}</code>
⏱ <b>Wait:</b> {wait_hours}h
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"""

        await cls._send_to_admins(text, event_type="addinfo_set")

    # ===================== PAYMENTS =====================

    @classmethod
    async def notify_payment_success(
        cls,
        user_id: int,
        amount: float,
        new_balance: float,
        payment_method: str,
        invoice_id: str = ""
    ):
        text = f"""💰 <b>PAYMENT RECEIVED</b>

👤 <b>User:</b> <code>{user_id}</code>
💵 <b>Amount:</b> ${amount:.2f}
💳 <b>Method:</b> {payment_method}
💰 <b>New Balance:</b> ${new_balance:.2f}"""

        if invoice_id:
            text += f"\n🧾 <b>Invoice:</b> <code>{invoice_id}</code>"

        text += f"\n⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"

        await NotificationService.broadcast(
            roles=["support", "finance", "accountant", "admin", "super_admin"],
            text=text,
            event_type="payment_success",
        )

    @classmethod
    async def notify_payment_expired(
        cls,
        user_id: int,
        amount: float,
        payment_method: str,
        invoice_id: str = ""
    ):
        text = f"""⏰ <b>PAYMENT EXPIRED</b>

👤 <b>User:</b> <code>{user_id}</code>
💵 <b>Amount:</b> ${amount:.2f}
💳 <b>Method:</b> {payment_method}"""

        if invoice_id:
            text += f"\n🧾 <b>Invoice:</b> <code>{invoice_id}</code>"

        text += f"\n⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"

        await NotificationService.broadcast(
            roles=["support", "finance", "accountant", "admin", "super_admin"],
            text=text,
            event_type="payment_expired",
        )

    # ===================== BALANCE =====================

    @classmethod
    async def notify_balance_update(
        cls,
        user_id: int,
        amount: float,
        reason: str,
        admin_username: str = "web_panel"
    ):
        direction = "➕" if amount > 0 else "➖"
        text = f"""{direction} <b>ADMIN BALANCE CHANGE</b>

👤 <b>User:</b> <code>{user_id}</code>
💵 <b>Amount:</b> {"+" if amount > 0 else ""}${amount:.2f}
📝 <b>Reason:</b> {reason}
🔑 <b>By:</b> {admin_username}
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"""

        await cls._send_to_admins(text, event_type="balance_update", urgent=True)

    # ===================== USERS =====================

    @classmethod
    async def notify_new_user(
        cls,
        user_id: int,
        username: str = "",
        mirror_bot_id: int = 0,
        language: str = "en"
    ):
        text = f"""👋 <b>NEW USER</b>

👤 <b>User:</b> <code>{user_id}</code>"""

        if username:
            text += f"\n📛 <b>Username:</b> @{username}"
        if mirror_bot_id:
            text += f"\n🤖 <b>Bot ID:</b> {mirror_bot_id}"

        text += f"\n🌐 <b>Language:</b> {language}"
        text += f"\n⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"

        await cls._send_to_admins(text, event_type="new_user")

    @classmethod
    async def notify_user_banned(
        cls,
        user_id: int,
        is_banned: bool,
        reason: str = "",
        admin_username: str = "web_panel"
    ):
        if is_banned:
            text = f"""🚫 <b>USER BANNED</b>

👤 <b>User:</b> <code>{user_id}</code>"""
            if reason:
                text += f"\n📝 <b>Reason:</b> {reason}"
        else:
            text = f"""✅ <b>USER UNBANNED</b>

👤 <b>User:</b> <code>{user_id}</code>"""

        text += f"\n🔑 <b>By:</b> {admin_username}"
        text += f"\n⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"

        await cls._send_to_admins(text, event_type="user_banned", urgent=is_banned)

    # ===================== SUPPORT TICKETS =====================

    @classmethod
    async def notify_new_support_ticket(
        cls,
        ticket_id: int,
        user_id: int,
        category: str,
        subject: str
    ):
        text = f"""🎫 <b>NEW SUPPORT TICKET</b>

📋 <b>Ticket #{ticket_id}</b>
👤 <b>User:</b> <code>{user_id}</code>
📂 <b>Category:</b> {category}
📌 <b>Subject:</b> {subject}
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"""

        await cls._send_to_admins(text, event_type="new_support_ticket")

    @classmethod
    async def notify_new_complaint(
        cls,
        complaint_id: int,
        worker_username: str,
        worker_id: int,
        user_id: int,
        order_id: int,
        complaint_text: str
    ):
        text = f"""⚠️ <b>NEW COMPLAINT</b>

📋 <b>Complaint #{complaint_id}</b>
👷 <b>Worker:</b> @{worker_username} (ID: {worker_id})
👤 <b>Client:</b> <code>{user_id}</code>
📦 <b>Order:</b> #{order_id}

📝 <b>Description:</b>
<code>{complaint_text[:300]}</code>
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"""

        await cls._send_to_admins(text, event_type="new_complaint", urgent=True)

    # ===================== FILES =====================

    @classmethod
    async def notify_files_sent(
        cls,
        order_id: int,
        service_name: str,
        worker_username: str,
        worker_id: int,
        user_id: int,
        files_count: int
    ):
        text = f"""📎 <b>FILES SENT</b>

📦 <b>Order #{order_id}</b>
🔧 <b>Service:</b> {service_name}
👷 <b>Worker:</b> @{worker_username} (ID: {worker_id})
👤 <b>Client:</b> <code>{user_id}</code>
📁 <b>Files:</b> {files_count}
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"""

        await cls._send_to_admins(text, event_type="files_sent")

    # ===================== PRODUCTS =====================

    @classmethod
    async def notify_product_purchased(
        cls,
        purchase_id: int,
        product_id: int,
        product_name: str,
        category: str,
        service: str,
        user_id: int,
        price: float,
        mirror_bot_id: int = 0
    ):
        """Уведомить админов о покупке товара"""
        text = f"""🛒 <b>PRODUCT PURCHASED</b>

📦 <b>Purchase #{purchase_id}</b> (Product #{product_id})
📋 <b>Product:</b> {product_name}
📂 <b>Category:</b> {category}
🔧 <b>Service:</b> {service}
💰 <b>Price:</b> ${price:.2f}
👤 <b>User:</b> <code>{user_id}</code>"""
        if mirror_bot_id:
            text += f"\n🤖 <b>Bot ID:</b> {mirror_bot_id}"
        text += f"\n⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"

        await cls._send_to_admins(text, event_type="product_purchased")

    # ===================== DISPUTES =====================

    @classmethod
    @classmethod
    async def notify_dispute(cls, order_id: int, bank_name: str, buyer_id: int):
        """Notify admins that buyer opened a dispute"""
        text = f"""⚠️ <b>DISPUTE OPENED</b>

📦 <b>Order #{order_id}</b> ({bank_name})
👤 <b>Buyer ID:</b> <code>{buyer_id}</code>

View chat in Support Bot: /seller_orders
⏰ <b>Time:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"""
        await NotificationService.broadcast(
            roles=["support", "moderator", "admin", "super_admin"],
            text=text,
            event_type="dispute_opened",
        )

    @classmethod
    async def notify_new_dispute(
        cls,
        *,
        order_type: str,
        order_id: int,
        buyer_user_id: int,
        seller_id: int,
    ):
        """Notify admins about a buyer report / moderation request."""
        text = (
            f"🚨 <b>NEW REPORT — Moderation Required</b>\n\n"
            f"📦 <b>Order:</b> #{order_id}\n"
            f"📂 <b>Type:</b> {order_type}\n"
            f"👤 <b>Buyer:</b> <code>{buyer_user_id}</code>\n"
            f"🏪 <b>Seller ID:</b> {seller_id}\n\n"
            f"View: /seller_orders\n"
            f"⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S %d.%m.%Y')} UTC"
        )
        await NotificationService.broadcast(
            roles=["support", "moderator", "admin", "super_admin"],
            text=text,
            event_type="buyer_report",
        )
