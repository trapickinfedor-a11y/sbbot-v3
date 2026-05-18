# Error Handling — Full Specification (v24)

This document defines the complete error handling strategy for all components of the Newlookup platform: bots, API, services, and background tasks.

---

## 1. Error Handling Philosophy

The platform follows a **fail-safe, user-friendly** approach to error handling:

1. **Never crash silently** — all exceptions must be logged with full context.
2. **Always inform the user** — every error must produce a human-readable message in the bot.
3. **Retry transient failures** — network errors, database timeouts, and API failures should be retried.
4. **Audit critical failures** — payment failures, dispute errors, and data integrity issues must be logged to the audit table.
5. **Degrade gracefully** — if a non-critical feature fails (e.g., archive channel forwarding), the main flow must still complete.

---

## 2. Error Categories

| Category | Examples | Handling Strategy |
|---|---|---|
| **User Input Error** | Invalid coupon code, wrong channel ID | Show friendly message, ask to retry |
| **Business Logic Error** | Insufficient balance, out of stock | Show specific error with actionable advice |
| **Authorization Error** | User banned, insufficient role | Show access denied message |
| **External API Error** | Payment processor timeout, Telegram API error | Retry 3x, then notify admin |
| **Database Error** | Connection timeout, constraint violation | Retry 3x, log to audit, notify admin |
| **Critical System Error** | Unhandled exception, data corruption | Log to Sentry, notify owner immediately |

---

## 3. Bot-Level Error Handling

### 3.1. Global Error Handler (aiogram)

```python
# bots/mirror_bot/middlewares/error_handler.py
from aiogram import BaseMiddleware
from aiogram.types import Update
import logging
import traceback

logger = logging.getLogger(__name__)

class GlobalErrorMiddleware(BaseMiddleware):
    """
    Catches all unhandled exceptions in bot handlers.
    Logs the error and sends a generic error message to the user.
    """
    async def __call__(self, handler, event: Update, data: dict):
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(
                f"Unhandled exception in handler: {e}\n"
                f"Traceback: {traceback.format_exc()}\n"
                f"Update: {event}"
            )
            # Try to notify the user
            try:
                if event.message:
                    await event.message.answer(
                        "❌ Произошла внутренняя ошибка. Попробуйте позже или обратитесь в поддержку."
                    )
                elif event.callback_query:
                    await event.callback_query.answer(
                        "❌ Ошибка. Попробуйте позже.",
                        show_alert=True
                    )
            except Exception:
                pass  # If we can't notify, just log and continue

# Register in dispatcher:
# dp.update.middleware(GlobalErrorMiddleware())
```

### 3.2. Specific Error Messages

```python
# bots/mirror_bot/texts/errors.py

# Business Logic Errors
ERR_INSUFFICIENT_BALANCE = """
❌ <b>Недостаточно средств</b>

Необходимо: <b>${required:.2f}</b>
Ваш баланс: <b>${balance:.2f}</b>

👉 Пополните баланс: /deposit
"""

ERR_OUT_OF_STOCK = "❌ Товар закончился. Выберите другой товар."

ERR_PRODUCT_NOT_FOUND = "❌ Товар не найден или был удалён."

ERR_COUPON_INVALID = "❌ Купон недействителен, истёк или уже использован."

ERR_COUPON_ALREADY_ACTIVATED = "❌ Вы уже активировали этот купон."

ERR_DISPUTE_ALREADY_EXISTS = "❌ Спор по этому заказу уже открыт."

ERR_DISPUTE_WINDOW_CLOSED = "❌ Окно для открытия спора закрыто. Срок для подачи спора истёк. (Hold duration depends on seller/buyer reputation score.)"

ERR_ARCHIVE_CHANNEL_NOT_ADMIN = """
❌ <b>Ошибка настройки архив-канала</b>

Бот не является администратором в указанном канале.

Убедитесь, что:
1. Вы добавили бота (@{bot_username}) в канал
2. Назначили его администратором
3. Повторите попытку
"""

# Authorization Errors
ERR_BANNED = """
🚫 <b>Доступ заблокирован</b>

Ваш аккаунт заблокирован.
Причина: {reason}

Для обжалования: @support_username
"""

ERR_SELLER_ONLY = "❌ Эта функция доступна только продавцам."

ERR_ADMIN_ONLY = "❌ Эта функция доступна только администраторам."

# System Errors
ERR_GENERIC = "❌ Произошла ошибка. Попробуйте позже."

ERR_PAYMENT_FAILED = """
❌ <b>Ошибка платежа</b>

Не удалось обработать платёж. Попробуйте позже.
Если средства были списаны, обратитесь в поддержку: /support
"""

ERR_TELEGRAM_API = "❌ Ошибка Telegram API. Попробуйте позже."
```

### 3.3. Error Handling in Purchase Flow

```python
# In purchase.py handler
@router.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_purchase(callback: CallbackQuery, state: FSMContext, db_session, bot):
    product_id = int(callback.data.replace("confirm_buy_", ""))
    state_data = await state.get_data()

    order_service = OrderService(db_session)
    user_service = UserService(db_session)
    user = user_service.get_by_telegram_id(callback.from_user.id)

    try:
        order = order_service.create_order(
            buyer_id=user.id,
            product_id=product_id,
            quantity=state_data.get("quantity", 1),
            coupon_code=state_data.get("coupon_code")
        )
    except InsufficientBalanceError as e:
        await callback.message.answer(
            ERR_INSUFFICIENT_BALANCE.format(required=e.required, balance=e.balance),
            parse_mode="HTML"
        )
        await state.clear()
        await callback.answer()
        return
    except OutOfStockError:
        await callback.answer(ERR_OUT_OF_STOCK, show_alert=True)
        await state.clear()
        return
    except Exception as e:
        logger.error(f"Purchase failed for user {user.id}, product {product_id}: {e}")
        await callback.message.answer(ERR_GENERIC)
        await state.clear()
        await callback.answer()
        return

    # Purchase succeeded - continue with pinning and archiving
    # These are non-critical operations; failures should NOT block the success flow
    success_text = PURCHASE_SUCCESS.format(...)
    sent_message = await callback.message.answer(success_text, parse_mode="HTML")

    # Non-critical: pin message
    try:
        await bot.pin_chat_message(...)
    except Exception as e:
        logger.warning(f"Failed to pin message for order {order.id}: {e}")
        # Do NOT raise - pinning failure is non-critical

    # Non-critical: forward to archive
    if user.archive_channel_id:
        try:
            await bot.forward_message(...)
        except Exception as e:
            logger.warning(f"Failed to forward to archive for order {order.id}: {e}")
            # Do NOT raise - archive failure is non-critical

    await state.clear()
    await callback.answer()
```

---

## 4. Service-Level Error Handling

### 4.1. Custom Exception Classes

```python
# app/exceptions.py

class NewlookupBaseError(Exception):
    """Base exception for all Newlookup business logic errors."""
    pass

class InsufficientBalanceError(NewlookupBaseError):
    def __init__(self, required: float, balance: float):
        self.required = required
        self.balance = balance
        super().__init__(f"Insufficient balance: required={required}, balance={balance}")

class OutOfStockError(NewlookupBaseError):
    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Product {product_id} is out of stock")

class ProductNotFoundError(NewlookupBaseError):
    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")

class CouponInvalidError(NewlookupBaseError):
    pass

class CouponAlreadyActivatedError(NewlookupBaseError):
    pass

class DisputeAlreadyExistsError(NewlookupBaseError):
    pass

class DisputeWindowClosedError(NewlookupBaseError):
    pass

class UserBannedError(NewlookupBaseError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"User is banned: {reason}")

class UnauthorizedError(NewlookupBaseError):
    def __init__(self, required_role: str):
        self.required_role = required_role
        super().__init__(f"Unauthorized: required role={required_role}")
```

### 4.2. Order Service Error Handling

```python
# app/services/order_service.py
import datetime
from app.exceptions import (
    InsufficientBalanceError, OutOfStockError, ProductNotFoundError
)

class OrderService:
    def create_order(self, buyer_id: int, product_id: int, quantity: int, coupon_code: str = None):
        with self.db.begin():
            # 1. Get product with row lock
            product = (
                self.db.query(Product)
                .filter(Product.id == product_id, Product.is_active == True)
                .with_for_update()  # Row-level lock to prevent race conditions
                .first()
            )

            if not product:
                raise ProductNotFoundError(product_id)

            if product.stock < quantity:
                raise OutOfStockError(product_id)

            # 2. Calculate price
            total_price = product.price * quantity
            if coupon_code:
                discount = self._get_coupon_discount(buyer_id, coupon_code)
                total_price *= (1 - discount / 100)

            # 3. Check balance
            buyer = self.db.query(User).filter(User.id == buyer_id).with_for_update().first()
            if buyer.balance < total_price:
                raise InsufficientBalanceError(required=total_price, balance=buyer.balance)

            # 4. Deduct balance and stock atomically
            buyer.balance -= total_price
            product.stock -= quantity

            # 5. Create order record
            order = Order(
                buyer_id=buyer_id,
                product_id=product_id,
                quantity=quantity,
                total_price=total_price,
                status=OrderStatusEnum.completed
            )
            self.db.add(order)
            self.db.flush()  # Get order.id before commit

            # 6. Create transaction record
            tx = Transaction(
                user_id=buyer_id,
                amount=-total_price,
                type="purchase"
            )
            self.db.add(tx)

            # 7. Schedule escrow release (48h after purchase)
            from app.tasks.finance import release_escrow_funds
            release_escrow_funds.apply_async(
                args=[order.id],
                countdown=48 * 3600
            )

            return order
```

---

## 5. API-Level Error Handling

### 5.1. FastAPI Exception Handlers

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.exceptions import (
    InsufficientBalanceError, OutOfStockError, ProductNotFoundError,
    CouponInvalidError, DisputeAlreadyExistsError, UserBannedError, UnauthorizedError
)

app = FastAPI()

@app.exception_handler(InsufficientBalanceError)
async def insufficient_balance_handler(request: Request, exc: InsufficientBalanceError):
    return JSONResponse(
        status_code=400,
        content={"error": "insufficient_balance", "required": exc.required, "balance": exc.balance}
    )

@app.exception_handler(OutOfStockError)
async def out_of_stock_handler(request: Request, exc: OutOfStockError):
    return JSONResponse(
        status_code=400,
        content={"error": "out_of_stock", "product_id": exc.product_id}
    )

@app.exception_handler(ProductNotFoundError)
async def product_not_found_handler(request: Request, exc: ProductNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "product_not_found", "product_id": exc.product_id}
    )

@app.exception_handler(UserBannedError)
async def user_banned_handler(request: Request, exc: UserBannedError):
    return JSONResponse(
        status_code=403,
        content={"error": "user_banned", "reason": exc.reason}
    )

@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError):
    return JSONResponse(
        status_code=403,
        content={"error": "unauthorized", "required_role": exc.required_role}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger(__name__).error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "An unexpected error occurred."}
    )
```

---

## 6. Celery Task Error Handling

```python
# Pattern for all Celery tasks
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 60 seconds between retries
    autoretry_for=(Exception,),  # Auto-retry on any exception
    retry_backoff=True,  # Exponential backoff: 60s, 120s, 240s
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,  # Add random jitter to prevent thundering herd
)
def my_task(self, arg1, arg2):
    try:
        # Task logic here
        pass
    except SomeExpectedException as e:
        # Expected failure - log as warning, don't retry
        logger.warning(f"Expected failure in task: {e}")
        return {"status": "failed", "reason": str(e)}
    except Exception as exc:
        # Unexpected failure - log as error, will auto-retry
        logger.error(f"Unexpected failure in task: {exc}", exc_info=True)
        raise  # Re-raise to trigger retry
```

---

## 7. Database Error Handling

```python
# app/db.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, DisconnectionError
import logging
import time

logger = logging.getLogger(__name__)

def create_db_engine(database_url: str):
    engine = create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,  # Recycle connections every hour
        pool_pre_ping=True,  # Test connections before using
    )
    return engine

def get_db_with_retry(session_factory, max_retries=3):
    """Get a database session with automatic retry on connection failure."""
    for attempt in range(max_retries):
        try:
            db = session_factory()
            yield db
            db.commit()
        except OperationalError as e:
            db.rollback()
            if attempt < max_retries - 1:
                logger.warning(f"DB connection failed (attempt {attempt + 1}): {e}. Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"DB connection failed after {max_retries} attempts: {e}")
                raise
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
```

---

## 8. Monitoring & Alerting

### 8.1. Sentry Integration

```python
# app/monitoring.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def init_sentry(dsn: str, environment: str):
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,
    )
```

### 8.2. Critical Error Notification to Owner

```python
# app/utils/alerts.py
import requests
import os

OWNER_TELEGRAM_ID = os.getenv("OWNER_TELEGRAM_ID")
ALERT_BOT_TOKEN = os.getenv("ALERT_BOT_TOKEN")

def notify_owner(message: str):
    """Send a critical alert to the platform owner via Telegram."""
    if not OWNER_TELEGRAM_ID or not ALERT_BOT_TOKEN:
        return

    url = f"https://api.telegram.org/bot{ALERT_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": OWNER_TELEGRAM_ID,
        "text": f"🚨 <b>CRITICAL ALERT</b>\n\n{message}",
        "parse_mode": "HTML",
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass  # Alert delivery failure should not cause further errors
```

---

## 9. Error Handling Checklist for Cursor

When implementing any new feature, verify the following:

- [ ] All service methods raise specific custom exceptions (not generic `Exception`)
- [ ] All bot handlers catch specific exceptions and show user-friendly messages
- [ ] Non-critical operations (pinning, archiving) are wrapped in try/except and never block the main flow
- [ ] All Celery tasks have `max_retries`, `default_retry_delay`, and proper logging
- [ ] All database operations use transactions (`with db.begin()`) for atomicity
- [ ] FastAPI exception handlers are registered for all custom exceptions
- [ ] Sentry is initialized and captures unhandled exceptions
- [ ] Critical failures (payment errors, data corruption) trigger owner notifications
- [ ] All errors are logged with sufficient context (user_id, order_id, etc.)
