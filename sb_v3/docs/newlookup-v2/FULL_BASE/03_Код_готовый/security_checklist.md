# Security Checklist — Pre-Deployment (v24)

This document provides a comprehensive security checklist that must be completed before deploying the Newlookup platform to production. Each item is categorized by component and priority.

---

## 1. Authentication & Authorization

| # | Check | Priority | Status |
|---|---|---|---|
| 1.1 | All API endpoints require authentication (no public endpoints except `/health` and `/webhooks`) | Critical | [ ] |
| 1.2 | Role-based access control (RBAC) is enforced on every admin endpoint | Critical | [ ] |
| 1.3 | Bot webhook tokens are validated on every incoming request | Critical | [ ] |
| 1.4 | Admin Panel login uses a secure token (not Telegram ID alone) | Critical | [ ] |
| 1.5 | Telegram `initData` is validated using HMAC-SHA256 before trusting any Mini App request | Critical | [ ] |
| 1.6 | Session tokens have a reasonable expiry (e.g., 24h for admin, 7 days for bots) | High | [ ] |
| 1.7 | Failed login attempts are rate-limited (max 5 attempts per 15 minutes) | High | [ ] |

### Telegram `initData` Validation Code

```python
# app/utils/telegram_auth.py
import hashlib
import hmac
import json
import time
from urllib.parse import unquote

def validate_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """
    Validate Telegram Mini App initData.
    Returns the parsed user data if valid, raises ValueError if invalid.
    """
    parsed = dict(item.split("=", 1) for item in init_data.split("&"))
    hash_value = parsed.pop("hash", None)

    if not hash_value:
        raise ValueError("Missing hash in initData")

    # Check timestamp (reject if older than 1 hour)
    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > 3600:
        raise ValueError("initData is expired")

    # Build data check string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    # Calculate HMAC
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, hash_value):
        raise ValueError("Invalid initData hash")

    user_data = json.loads(unquote(parsed.get("user", "{}")))
    return user_data
```

---

## 2. Input Validation & Injection Prevention

| # | Check | Priority | Status |
|---|---|---|---|
| 2.1 | All user inputs are validated with Pydantic before processing | Critical | [ ] |
| 2.2 | SQL injection is prevented by using SQLAlchemy ORM (never raw SQL with user input) | Critical | [ ] |
| 2.3 | All text sent to Telegram is sanitized (HTML entities escaped for non-HTML parse mode) | High | [ ] |
| 2.4 | File uploads (if any) are validated for type and size | High | [ ] |
| 2.5 | Coupon codes are normalized to uppercase and stripped of whitespace before lookup | Medium | [ ] |
| 2.6 | Numeric inputs (amounts, quantities) have min/max bounds enforced | High | [ ] |
| 2.7 | Channel IDs are validated as negative integers (Telegram channel IDs are always negative) | Medium | [ ] |

---

## 3. Financial Security

| # | Check | Priority | Status |
|---|---|---|---|
| 3.1 | All balance operations use database row-level locks (`SELECT FOR UPDATE`) to prevent race conditions | Critical | [ ] |
| 3.2 | All financial transactions are atomic (wrapped in a single DB transaction) | Critical | [ ] |
| 3.3 | Double-spend prevention: check balance AFTER acquiring the row lock | Critical | [ ] |
| 3.4 | Withdrawal requests require manual approval for amounts above threshold | Critical | [ ] |
| 3.5 | Payment processor webhooks are validated using the provider's signature | Critical | [ ] |
| 3.6 | All financial operations are logged to the `transactions` table with full context | High | [ ] |
| 3.7 | Negative balance is impossible (enforced at DB level with CHECK constraint) | Critical | [ ] |
| 3.8 | Platform fee calculation uses server-side values, never client-provided values | Critical | [ ] |

### DB Constraint for Non-Negative Balance

```sql
ALTER TABLE users ADD CONSTRAINT balance_non_negative CHECK (balance >= 0);
```

---

## 4. Bot Security

| # | Check | Priority | Status |
|---|---|---|---|
| 4.1 | Bot tokens are stored in environment variables, never in code or git | Critical | [ ] |
| 4.2 | Webhook URLs use HTTPS with a valid SSL certificate | Critical | [ ] |
| 4.3 | Webhook secret token is set and validated on every update | Critical | [ ] |
| 4.4 | Bot only processes updates from Telegram's IP ranges (optional but recommended) | Medium | [ ] |
| 4.5 | Banned users are checked on every handler call, not just at `/start` | Critical | [ ] |
| 4.6 | FSM state is cleared after any error to prevent stuck states | High | [ ] |
| 4.7 | Rate limiting is applied per user (max 30 messages/minute) | High | [ ] |
| 4.8 | Bot does not log sensitive data (product content, user messages) | High | [ ] |

### Webhook Secret Validation

```python
# In FastAPI webhook handler
from fastapi import Request, HTTPException, Header

WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")

@router.post("/webhooks/mirror/")
async def mirror_bot_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    if x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    # Process update...
```

---

## 5. Infrastructure Security

| # | Check | Priority | Status |
|---|---|---|---|
| 5.1 | All secrets are stored in environment variables or a secrets manager (never in `.env` committed to git) | Critical | [ ] |
| 5.2 | `.env` file is in `.gitignore` | Critical | [ ] |
| 5.3 | Database is not exposed to the public internet (only accessible from the app container) | Critical | [ ] |
| 5.4 | Redis is not exposed to the public internet | Critical | [ ] |
| 5.5 | Admin Panel is behind IP allowlist or VPN | High | [ ] |
| 5.6 | HTTPS is enforced for all external endpoints (HTTP redirects to HTTPS) | Critical | [ ] |
| 5.7 | Docker containers run as non-root users | High | [ ] |
| 5.8 | Database backups are automated and tested (daily, 30-day retention) | Critical | [ ] |
| 5.9 | Firewall rules allow only necessary ports (80, 443, and internal ports) | High | [ ] |
| 5.10 | Dependency versions are pinned in `requirements.txt` and `package.json` | Medium | [ ] |

---

## 6. API Security

| # | Check | Priority | Status |
|---|---|---|---|
| 6.1 | CORS is restricted to known origins in production (not `*`) | Critical | [ ] |
| 6.2 | Rate limiting is applied to all API endpoints (e.g., 100 req/min per IP) | High | [ ] |
| 6.3 | API responses never include sensitive data (passwords, full card numbers, etc.) | Critical | [ ] |
| 6.4 | Error responses do not expose internal stack traces in production | High | [ ] |
| 6.5 | API versioning is used (`/api/v1/`) to allow breaking changes | Medium | [ ] |
| 6.6 | Request body size is limited (e.g., max 1MB) | Medium | [ ] |

### Rate Limiting with slowapi

```python
# app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to routes:
@router.post("/orders/")
@limiter.limit("20/minute")
async def create_order(request: Request, ...):
    ...
```

---

## 7. Anti-Fraud Measures

| # | Check | Priority | Status |
|---|---|---|---|
| 7.1 | Multiple accounts from the same IP are flagged for review | High | [ ] |
| 7.2 | Unusually large purchases (> 10x average) trigger manual review | High | [ ] |
| 7.3 | Rapid succession of purchases (> 5 in 1 minute) are rate-limited | High | [ ] |
| 7.4 | Dispute rate per user is monitored (users with > 30% dispute rate are flagged) | Medium | [ ] |
| 7.5 | Coupon abuse is prevented: one activation per user per coupon | Critical | [ ] |
| 7.6 | Bot clone commission fraud: verify that the marketer bot is a legitimate clone | High | [ ] |

---

## 8. Audit & Compliance

| # | Check | Priority | Status |
|---|---|---|---|
| 8.1 | All admin actions are logged to the `audit_logs` table with actor, action, and timestamp | Critical | [ ] |
| 8.2 | Balance adjustments by admins require a reason and are logged | Critical | [ ] |
| 8.3 | User bans/unbans are logged with reason and actor | High | [ ] |
| 8.4 | Price changes by support staff are logged (as specified in CRM access matrix) | High | [ ] |
| 8.5 | Audit logs are immutable (no UPDATE/DELETE allowed, only INSERT) | High | [ ] |
| 8.6 | Logs are retained for at least 90 days | Medium | [ ] |

### Audit Log Model

```python
class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String, nullable=False)  # e.g., "ban_user", "adjust_balance"
    target_type = Column(String)  # e.g., "user", "product", "order"
    target_id = Column(Integer)
    details = Column(JSON)  # Additional context
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    # No updated_at - audit logs are immutable
```

---

## 9. Secrets Management

All secrets must be provided via environment variables. The following secrets are required:

```bash
# .env.example (commit this, NOT .env)

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/newlookup

# Redis
REDIS_URL=redis://localhost:6379/0

# Bot Tokens
MIRROR_BOT_TOKEN=
SELLER_BOT_TOKEN=
MARKETER_BOT_TOKEN=
SUPPORT_BOT_TOKEN=
WORKER_BOT_TOKEN=

# Webhook
TELEGRAM_WEBHOOK_SECRET=
WEBHOOK_BASE_URL=https://your-domain.com

# Admin
OWNER_TELEGRAM_ID=
ALERT_BOT_TOKEN=

# Payment
PAYMENT_PROCESSOR_API_KEY=
PAYMENT_PROCESSOR_WEBHOOK_SECRET=

# Monitoring
SENTRY_DSN=

# Security
SECRET_KEY=  # For JWT or session signing (min 32 chars)
```
