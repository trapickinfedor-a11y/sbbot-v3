from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from datetime import date, datetim, timezone
from typing import Optional, Dict

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import User, Referral, Transaction, Marketer, MarketerStats, MirrorBot, BotOwner, BotOwnerStats, MarketerBotLink
from shared.database.session import async_session_maker
from shared.services.bot_pool import get_mirror_bot_instance
from shared.services.ledger_service import LedgerService
from shared.services.marketer_activity_log import log_marketer_activity
from shared.services.marketer_monitoring_service import get_or_create_marketer_stats_row, record_marketer_registration
from shared.services.nocodb_service import NocoDBService
import secrets
import string

logger = logging.getLogger(__name__)
OWNER_COMMISSION_PERCENT = 7  # Реально 7%, владельцу показываем 10%
USER_MILESTONE_STEP = 50


def _build_user_milestone_message(language: str | None, total_users: int) -> str:
    lang = (language or "en").lower()
    messages = {
        "ru": (
            "🎉 <b>Нас уже {total_users} пользователей!</b>\n\n"
            "Спасибо, что вы с нами в этом боте."
        ),
        "es": (
            "🎉 <b>Ya somos {total_users} usuarios!</b>\n\n"
            "Gracias por estar con nosotros en este bot."
        ),
        "zh": (
            "🎉 <b>本机器人已经有 {total_users} 位用户！</b>\n\n"
            "感谢你加入我们。"
        ),
        "en": (
            "🎉 <b>We have already reached {total_users} users!</b>\n\n"
            "Thanks for being with us in this bot."
        ),
    }
    template = messages.get(lang, messages["en"])
    return template.format(total_users=total_users)


async def _send_user_milestone_broadcast(mirror_bot_id: int, total_users: int) -> None:
    try:
        async with async_session_maker() as session:
            mirror_bot = await session.scalar(
                select(MirrorBot).where(
                    MirrorBot.id == mirror_bot_id,
                    MirrorBot.is_active == True,
                )
            )
            if not mirror_bot:
                return

            rows = (
                await session.execute(
                    select(User.user_id, User.language).where(
                        User.mirror_bot_id == mirror_bot_id,
                        User.is_banned == False,
                    )
                )
            ).all()

        if not rows:
            return

        bot = get_mirror_bot_instance(mirror_bot.bot_token)
        sent = 0
        failed = 0
        for user_id, language in rows:
            try:
                await bot.send_message(
                    chat_id=int(user_id),
                    text=_build_user_milestone_message(language, total_users),
                    parse_mode="HTML",
                )
                sent += 1
                await asyncio.sleep(0.05)
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
                try:
                    await bot.send_message(
                        chat_id=int(user_id),
                        text=_build_user_milestone_message(language, total_users),
                        parse_mode="HTML",
                    )
                    sent += 1
                    await asyncio.sleep(0.05)
                except Exception as retry_exc:
                    logger.warning(
                        "Failed retry milestone broadcast to user %s in bot %s: %s",
                        user_id,
                        mirror_bot_id,
                        retry_exc,
                    )
                    failed += 1
            except TelegramForbiddenError:
                failed += 1
            except Exception as exc:
                logger.warning(
                    "Failed milestone broadcast to user %s in bot %s: %s",
                    user_id,
                    mirror_bot_id,
                    exc,
                )
                failed += 1

        logger.info(
            "User milestone broadcast finished for bot %s at %s users: sent=%s failed=%s",
            mirror_bot_id,
            total_users,
            sent,
            failed,
        )
    except Exception as exc:
        logger.error(
            "Failed to run user milestone broadcast for bot %s at %s users: %s",
            mirror_bot_id,
            total_users,
            exc,
        )


async def _notify_marketer_milestone(
    session: AsyncSession,
    mirror_bot_id: int,
    total_users: int,
) -> None:
    """Notify the marketer who owns this bot when milestone is reached."""
    try:
        from shared.database.models import MarketerOwnBot, Marketer
        bot_row = await session.scalar(
            select(MarketerOwnBot).where(MarketerOwnBot.id == mirror_bot_id)
        )
        if not bot_row:
            return
        marketer = await session.get(Marketer, bot_row.marketer_id)
        if not marketer:
            return
        from aiogram import Bot as _AiogramBot
        from marketer_bot.config import marketer_bot_config
        m_bot = _AiogramBot(token=marketer_bot_config.bot_token)
        try:
            await m_bot.send_message(
                chat_id=marketer.telegram_id,
                text=(
                    f"🎉 <b>Milestone Reached!</b>\n\n"
                    f"Your bot <b>@{bot_row.bot_username or 'YourBot'}</b> just reached "
                    f"<b>{total_users} registrations</b>!\n\n"
                    f"Keep up the great work! 🚀"
                ),
                parse_mode="HTML",
            )
        finally:
            await m_bot.session.close()
    except Exception as exc:
        logger.warning("Failed to notify marketer of milestone: %s", exc)


async def _maybe_schedule_user_milestone_broadcast(
    session: AsyncSession,
    *,
    mirror_bot_id: int,
) -> None:
    total_users = await session.scalar(
        select(func.count(User.id)).where(User.mirror_bot_id == mirror_bot_id)
    )
    total_users = int(total_users or 0)
    if total_users <= 0 or total_users % USER_MILESTONE_STEP != 0:
        return
    asyncio.create_task(_send_user_milestone_broadcast(mirror_bot_id, total_users))
    # Also notify marketer who owns this bot (if applicable)
    asyncio.create_task(_notify_marketer_milestone(session, mirror_bot_id, total_users))


class UserService:
    
    @staticmethod
    async def get_user(session: AsyncSession, user_id: int, mirror_bot_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        result = await session.execute(
            select(User).where(
                User.user_id == user_id,
                User.mirror_bot_id == mirror_bot_id
            )
        )
        user = result.scalar_one_or_none()
        if user:
            user.last_active_at = datetime.now(timezone.utc)
            await session.flush()
        return user
    
    @staticmethod
    async def get_user_by_referral(session: AsyncSession, referral_code: str) -> Optional[User]:
        """Получить пользователя по реферальному коду"""
        result = await session.execute(
            select(User).where(User.referral_link == referral_code)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        user_id: int,
        mirror_bot_id: int,
        referrer_id: Optional[int] = None,
        username: Optional[str] = None,
        initial_language: str = "en",
        return_created: bool = False,
    ) -> User | tuple[User, bool]:
        """Получить или создать пользователя"""
        started_here = not session.in_transaction()

        # Сначала ищем пользователя по user_id (независимо от mirror_bot_id)
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        created = False
        if user:
            # Пользователь существует, обновляем mirror_bot_id и username если нужно
            updated = False
            user.last_active_at = datetime.now(timezone.utc)
            updated = True
            if user.mirror_bot_id != mirror_bot_id:
                user.mirror_bot_id = mirror_bot_id
                updated = True
            if username and user.username != username:
                user.username = username
                updated = True

            if updated:
                await session.flush()
                if started_here:
                    await session.commit()
                    await session.refresh(user)
        else:
            # Пользователя нет, создаем нового
            # Генерируем уникальный реферальный код
            referral_code = f"ref_{user_id}_{UserService._generate_random_string(8)}"
            
            safe_referrer = referrer_id if referrer_id and referrer_id != user_id else None
            
            user = User(
                user_id=user_id,
                username=username,
                mirror_bot_id=mirror_bot_id,
                referrer_id=safe_referrer,
                referral_link=referral_code,
                language=initial_language or "en",
                last_active_at=datetime.now(timezone.utc),
            )
            
            session.add(user)
            try:
                await session.flush()
            except Exception:
                await session.rollback()
                result2 = await session.execute(
                    select(User).where(User.user_id == user_id)
                )
                user = result2.scalar_one_or_none()
                if user:
                    if return_created:
                        return user, False
                    return user
                raise
            if safe_referrer:
                referral = Referral(
                    referrer_id=safe_referrer,
                    referred_id=user_id
                )
                session.add(referral)
                await session.flush()
            if started_here:
                await session.commit()
                await session.refresh(user)
            created = True
            
            # Уведомляем админов о новом пользователе
            try:
                from shared.services.admin_notification_service import AdminNotificationService
                await AdminNotificationService.notify_new_user(
                    user_id=user_id,
                    username=username or "",
                    mirror_bot_id=mirror_bot_id,
                    language=initial_language or "en"
                )
            except Exception as e:
                logger.warning(f"Failed to send admin notification about new user: {e}")

            try:
                await _maybe_schedule_user_milestone_broadcast(
                    session,
                    mirror_bot_id=mirror_bot_id,
                )
            except Exception as e:
                logger.warning(
                    "Failed to schedule milestone broadcast for bot %s: %s",
                    mirror_bot_id,
                    e,
                )

            # Auto-bind marketer by mirror_bot_id (bot = promo code)
            try:
                link = await session.scalar(
                    select(MarketerBotLink).where(
                        MarketerBotLink.mirror_bot_id == mirror_bot_id,
                        MarketerBotLink.is_active == True,
                    )
                )
                if link:
                    marketer = await session.get(Marketer, link.marketer_id)
                    if marketer and marketer.is_active and marketer.telegram_id != user_id:
                        user.marketer_id = marketer.id
                        await session.flush()
                        await record_marketer_registration(session, marketer.id, mirror_bot_id, user_id)
                        logger.info("Auto-bound user %s to marketer %s via bot %s", user_id, marketer.id, mirror_bot_id)
                    if started_here:
                        await session.commit()
                        await session.refresh(user)
            except Exception as e:
                logger.warning("Failed to auto-bind marketer for user %s: %s", user_id, e)

            # Welcome bonus: credit $0.50 to new user's balance
            try:
                from decimal import Decimal as _Dec
                WELCOME_BONUS = _Dec("0.50")
                user.balance = (user.balance or _Dec("0")) + WELCOME_BONUS
                await session.commit()
                await session.refresh(user)
                logger.info("Welcome bonus $0.50 credited to new user %s", user_id)
            except Exception as e:
                logger.warning("Failed to credit welcome bonus to user %s: %s", user_id, e)

            # Auto-issue WELCOME10 coupon for new user
            try:
                await _issue_welcome_coupon(session, user_id)
            except Exception as e:
                logger.warning("Failed to issue WELCOME10 coupon to user %s: %s", user_id, e)

        if return_created:
            return user, created
        return user
    
    @staticmethod
    async def update_language(session: AsyncSession, user_id: int, mirror_bot_id: int, language: str):
        """Обновить язык пользователя"""
        started_here = not session.in_transaction()
        user = await UserService.get_user(session, user_id, mirror_bot_id)
        if user:
            user.language = language
            await session.flush()
            if started_here:
                await session.commit()

    @staticmethod
    async def update_username(session: AsyncSession, user_id: int, username: Optional[str]):
        """Обновить username пользователя"""
        if not username:
            return

        started_here = not session.in_transaction()
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        if user and user.username != username:
            user.username = username
            await session.flush()
            if started_here:
                await session.commit()
    
    @staticmethod
    async def add_balance(
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
        mirror_bot_id: int,
        description: str = "Balance top-up"
    ) -> Optional[Decimal]:
        """Добавить баланс пользователю"""
        amount = Decimal(str(amount))
        started_here = not session.in_transaction()

        async def _apply() -> tuple[Optional[User], Optional[Transaction]]:
            result = await session.execute(
                select(User).where(User.user_id == user_id).with_for_update()
            )
            user = result.scalar_one_or_none()
            if not user:
                return None, None

            transaction = await LedgerService.credit_user_balance(
                session,
                user_id=user_id,
                amount=amount,
                tx_type="topup",
                description=description,
                related_entity_type="mirror_bot",
                related_entity_id=mirror_bot_id,
            )
            await session.flush()
            return user, transaction

        if started_here:
            async with session.begin():
                user, transaction = await _apply()
        else:
            user, transaction = await _apply()

        if not user:
            return None

        if started_here:
            await session.refresh(user)
            NocoDBService.log_financial_operation(
                user_id=user_id,
                amount=amount,
                payment_method="balance_topup",
                tx_id=getattr(transaction, "id", None),
                operation_type="topup",
                extra={"mirror_bot_id": mirror_bot_id, "description": description},
            )
        return user.balance

    @staticmethod
    async def add_balance_with_marketer(
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
        mirror_bot_id: int,
        description: str = "Balance top-up"
    ) -> Optional[Decimal]:
        """Добавить баланс с учётом маркетолога (7% маркетологу, 3% бонус пользователю при первом пополнении)"""
        amount = Decimal(str(amount))
        started_here = not session.in_transaction()

        async def _apply() -> tuple[Optional[User], Optional[Transaction]]:
            user = await session.scalar(select(User).where(User.user_id == user_id).with_for_update())
            if not user:
                return None, None

            transaction = await LedgerService.credit_user_balance(
                session,
                user_id=user_id,
                amount=amount,
                tx_type="topup",
                description=description,
                related_entity_type="mirror_bot",
                related_entity_id=mirror_bot_id,
            )

            if user.marketer_id:
                marketer = await session.scalar(
                    select(Marketer).where(Marketer.id == user.marketer_id).with_for_update()
                )
                if marketer and marketer.is_active:
                    is_self = user_id == marketer.telegram_id
                    if not is_self:
                        reward = (amount * Decimal(str(marketer.reward_percent))) / Decimal("100")
                        reward = reward.quantize(Decimal("0.01"))
                        if reward > 0:
                            await LedgerService.credit_marketer_balance(
                                session,
                                marketer_id=marketer.id,
                                amount=reward,
                                description=f"Marketer commission from top-up by user {user_id}",
                                related_entity_type="user_topup",
                                related_entity_id=user_id,
                            )
                            today = date.today()
                            stats_res = await session.execute(
                                select(MarketerStats).where(
                                    MarketerStats.marketer_id == marketer.id,
                                    MarketerStats.date == today
                                )
                            )
                            stats = stats_res.scalar_one_or_none()
                            if not stats:
                                stats = await get_or_create_marketer_stats_row(session, marketer.id, today)
                            stats.topup_amount = Decimal(str(stats.topup_amount or 0)) + amount
                            stats.earned = Decimal(str(stats.earned or 0)) + reward
                            _display_pct = {7: 9, 9: 12, 12: 15}.get(int(marketer.reward_percent), int(marketer.reward_percent))
                            await log_marketer_activity(
                                session, marketer.id, "earning",
                                amount=reward,
                                details=f"Комиссия {_display_pct}% с пополнения user {user_id}",
                                mirror_bot_id=mirror_bot_id,
                                user_id=user_id
                            )
                            logger.info(f"Marketer {marketer.promo_code} +${reward} from user {user_id} topup")

            bot = await session.scalar(select(MirrorBot).where(MirrorBot.id == mirror_bot_id))
            if bot and bot.owner_user_id != user_id:
                owner_commission = (amount * Decimal(str(OWNER_COMMISSION_PERCENT))) / Decimal("100")
                owner_commission = owner_commission.quantize(Decimal("0.01"))
                if owner_commission > 0:
                    owner = await session.scalar(
                        select(BotOwner).where(BotOwner.owner_user_id == bot.owner_user_id).with_for_update()
                    )
                    if not owner:
                        owner = BotOwner(owner_user_id=bot.owner_user_id)
                        session.add(owner)
                        await session.flush()
                    await LedgerService.credit_owner_balance(
                        session,
                        owner_user_id=owner.owner_user_id,
                        amount=owner_commission,
                        description=f"Owner commission from top-up by user {user_id}",
                        related_entity_type="mirror_bot",
                        related_entity_id=mirror_bot_id,
                    )
                    today = date.today()
                    stats_res = await session.execute(
                        select(BotOwnerStats).where(
                            BotOwnerStats.mirror_bot_id == mirror_bot_id,
                            BotOwnerStats.date == today
                        )
                    )
                    ostats = stats_res.scalar_one_or_none()
                    if not ostats:
                        ostats = BotOwnerStats(mirror_bot_id=mirror_bot_id, date=today)
                        session.add(ostats)
                    ostats.topped_up = Decimal(str(ostats.topped_up or 0)) + amount
                    ostats.owner_income = Decimal(str(ostats.owner_income or 0)) + owner_commission
                    logger.info(f"Bot owner {bot.owner_user_id} +${owner_commission} from topup in bot {mirror_bot_id}")

            await UserService._credit_referral_commission_topup(
                session, user_id, amount, mirror_bot_id,
            )

            await session.flush()
            return user, transaction

        if started_here:
            async with session.begin():
                user, transaction = await _apply()
        else:
            user, transaction = await _apply()

        if not user:
            return None

        if started_here:
            await session.refresh(user)
            NocoDBService.log_financial_operation(
                user_id=user_id,
                amount=amount,
                payment_method="balance_topup",
                tx_id=getattr(transaction, "id", None),
                operation_type="topup",
                extra={
                    "mirror_bot_id": mirror_bot_id,
                    "description": description,
                    "marketer_id": user.marketer_id,
                    "first_topup_bonus_applied": bool(user.first_topup_bonus_applied),
                },
            )
        return user.balance

    @staticmethod
    async def _get_referral_rates(session: AsyncSession) -> dict:
        """Load 4-level referral rates from SystemSetting."""
        defaults = {"1": 10.0, "2": 7.0, "3": 5.0, "4": 3.0}
        try:
            from shared.database.models import SystemSetting
            import json as _json
            row = await session.scalar(
                select(SystemSetting).where(SystemSetting.key == "referral_rates")
            )
            if row:
                return {**defaults, **_json.loads(row.value)}
        except Exception:
            pass
        return defaults

    @staticmethod
    async def _credit_referral_commission_topup(
        session: AsyncSession,
        user_id: int,
        topup_amount: Decimal,
        mirror_bot_id: int,
    ):
        """4-level referral commission on balance top-up with notification to referrers."""
        rates = await UserService._get_referral_rates(session)

        current_user_id = user_id
        seen = {user_id}

        for level in range(1, 5):
            rate = float(rates.get(str(level), 0))
            if rate <= 0:
                continue

            cur_user = await session.scalar(
                select(User).where(User.user_id == current_user_id)
            )
            if not cur_user or not cur_user.referrer_id or cur_user.referrer_id in seen:
                break

            referrer_id = cur_user.referrer_id
            seen.add(referrer_id)

            referrer = await session.scalar(
                select(User).where(User.user_id == referrer_id).with_for_update()
            )
            if not referrer or referrer.is_banned:
                break

            commission = (topup_amount * Decimal(str(rate))) / Decimal("100")
            commission = commission.quantize(Decimal("0.01"))
            if commission <= 0:
                current_user_id = referrer_id
                continue

            await LedgerService.credit_user_balance(
                session,
                user_id=referrer.user_id,
                amount=commission,
                tx_type="referral_commission",
                description=f"Referral L{level} {rate}% from top-up ${topup_amount} (user {user_id})",
                related_entity_type="topup",
                related_entity_id=user_id,
                idempotency_key=LedgerService.build_idempotency_key(
                    f"referral-l{level}-topup", user_id, referrer.user_id,
                    str(topup_amount), str(datetime.now(timezone.utc).strftime("%Y%m%d%H%M")),
                ),
            )

            if level == 1:
                ref_row = await session.scalar(
                    select(Referral).where(
                        Referral.referrer_id == referrer.user_id,
                        Referral.referred_id == user_id,
                    )
                )
                if ref_row:
                    ref_row.earned_total = Decimal(str(ref_row.earned_total or 0)) + commission

            logger.info(
                "Referral topup L%d: $%s (%.1f%%) → user %d from topup $%s (user %d)",
                level, commission, rate, referrer.user_id, topup_amount, user_id,
            )

            asyncio.ensure_future(
                UserService._notify_referrer_commission(
                    referrer.user_id, referrer.mirror_bot_id,
                    commission, rate, level, topup_amount, user_id,
                )
            )

            current_user_id = referrer_id

    @staticmethod
    async def _notify_referrer_commission(
        referrer_user_id: int,
        referrer_mirror_bot_id: int,
        commission: Decimal,
        rate: float,
        level: int,
        topup_amount: Decimal,
        buyer_user_id: int,
    ):
        """Send Telegram notification to referrer about earned commission."""
        try:
            async with async_session_maker() as s:
                bot_row = await s.scalar(
                    select(MirrorBot).where(MirrorBot.id == referrer_mirror_bot_id)
                )
            if not bot_row or not bot_row.bot_token:
                return

            bot = get_mirror_bot_instance(bot_row.bot_token)

            level_emoji = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣"}.get(level, f"L{level}")

            text = (
                f"💰 <b>Referral Bonus!</b>\n\n"
                f"{level_emoji} Level {level} — <b>{rate:.0f}%</b>\n"
                f"Your referral topped up <b>${topup_amount:.2f}</b>\n"
                f"Your bonus: <b>+${commission:.2f}</b>\n\n"
                f"💵 Credited to your balance automatically."
            )

            await bot.send_message(
                chat_id=referrer_user_id,
                text=text,
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning(
                "Failed to notify referrer %s about commission: %s",
                referrer_user_id, exc,
            )

    @staticmethod
    async def get_referral_stats(session: AsyncSession, user_id: int) -> Dict:
        """Получить статистику рефералов"""
        # Количество рефералов
        referrals_count_result = await session.execute(
            select(func.count(Referral.id)).where(Referral.referrer_id == user_id)
        )
        referrals_count = referrals_count_result.scalar() or 0
        
        # Общий заработок с рефералов
        earned_result = await session.execute(
            select(func.sum(Referral.earned_total)).where(Referral.referrer_id == user_id)
        )
        earned = earned_result.scalar() or Decimal("0.00")
        
        return {
            "referrals_count": referrals_count,
            "count": referrals_count,  # для совместимости
            "earned": earned
        }
    
    @staticmethod
    def _generate_random_string(length: int) -> str:
        """Генерировать случайную строку"""
        letters = string.ascii_lowercase + string.digits
        return ''.join(secrets.choice(letters) for _ in range(length))


async def _issue_welcome_coupon(session: AsyncSession, user_id: int) -> None:
    """Assign the WELCOME10 coupon to a brand-new user (creates it if needed)."""
    from shared.database.models import Coupon, UserCoupon
    from datetime import datetime, timedelt, timezone

    WELCOME_CODE = "WELCOME10"

    # Find or create the coupon definition
    coupon = await session.scalar(select(Coupon).where(Coupon.code == WELCOME_CODE))
    if coupon is None:
        coupon = Coupon(
            code=WELCOME_CODE,
            title="Welcome 10% Discount",
            description="10% off your first purchase!",
            discount_type="percentage",
            discount_value=10,
            max_uses=None,
            uses_count=0,
            is_active=True,
            valid_from=datetime.now(timezone.utc),
            valid_to=datetime.now(timezone.utc) + timedelta(days=30),
        )
        session.add(coupon)
        await session.flush()

    # Check if already issued
    existing = await session.scalar(
        select(UserCoupon).where(
            UserCoupon.user_id == user_id,
            UserCoupon.coupon_id == coupon.id,
        )
    )
    if existing:
        return

    uc = UserCoupon(
        user_id=user_id,
        coupon_id=coupon.id,
        is_used=False,
    )
    session.add(uc)
    await session.flush()
    logger.info("Issued WELCOME10 coupon to new user %s", user_id)
