from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    AutomationApiKey,
    AutomationConfig,
    AutomationFinanceEntry,
    AutomationJob,
    AutomationProxy,
    Order,
)
from web_panel.auth import get_current_user, ROLE_OWNER, ROLE_SUPER_ADMIN, require_page_access
from web_panel.database import get_db


def _is_owner(current_user: dict) -> bool:
    role = current_user.get("role", "")
    return role in (ROLE_OWNER, ROLE_SUPER_ADMIN)


def _mask(value: Optional[str], show_for_owner: bool) -> Optional[str]:
    """Маскирует секретное значение для не-owner ролей."""
    if not value:
        return value
    if show_for_owner:
        return value
    visible = min(4, len(value))
    return value[:visible] + "***"

router = APIRouter(prefix="/api/automation", tags=["automation"])

# Service codes supported by the automation panel
_ALL_SERVICE_CODES = ["lookup_credit", "lookup_ssn", "lookup_dl"]

# Default configs per service
_SERVICE_DEFAULTS: dict[str, dict] = {
    "lookup_credit": {"worker_count": 10, "max_retries": 3, "poll_interval_seconds": 5},
    "lookup_ssn":   {"worker_count": 3,  "max_retries": 1, "poll_interval_seconds": 3},
    "lookup_dl":    {"worker_count": 3,  "max_retries": 1, "poll_interval_seconds": 3},
}


def _resolve_date_range(
    date_from: Optional[str],
    date_to: Optional[str],
    default_days: int = 30,
):
    now = datetime.now(timezone.utc)
    if date_from:
        start_dt = datetime.strptime(date_from, "%Y-%m-%d")
    elif date_to:
        end_base = datetime.strptime(date_to, "%Y-%m-%d")
        start_dt = end_base - timedelta(days=max(default_days - 1, 0))
    else:
        start_dt = now - timedelta(days=default_days)

    if date_to:
        end_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
    else:
        end_dt = now + timedelta(seconds=1)

    return start_dt, end_dt


def _config_to_dict(config: AutomationConfig) -> dict:
    return {
        "id": config.id,
        "service_code": config.service_code,
        "is_enabled": config.is_enabled,
        "worker_count": config.worker_count,
        "max_retries": config.max_retries,
        "headless": config.headless,
        "poll_interval_seconds": config.poll_interval_seconds,
        "screenshot_dir": config.screenshot_dir,
        "active_proxy_id": config.active_proxy_id,
        "notify_admin_on_error": config.notify_admin_on_error,
        "notify_user_on_error": config.notify_user_on_error,
        "notes": config.notes,
    }


# ─── Pydantic models ──────────────────────────────────────────────────────────

class AutomationConfigUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    worker_count: Optional[int] = None
    max_retries: Optional[int] = None
    headless: Optional[bool] = None
    poll_interval_seconds: Optional[int] = None
    screenshot_dir: Optional[str] = None
    active_proxy_id: Optional[int] = None
    notify_admin_on_error: Optional[bool] = None
    notify_user_on_error: Optional[bool] = None
    notes: Optional[str] = None


class ProxyBody(BaseModel):
    name: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: str = "http"
    country: str = "us"
    rotate_every: int = 3
    is_active: bool = True
    is_default: bool = False
    notes: Optional[str] = None


class ApiKeyBody(BaseModel):
    provider: str = "other"
    name: str
    key_value: str
    balance: Optional[float] = None
    daily_limit: Optional[int] = None
    is_active: bool = True
    notes: Optional[str] = None


# ─── Internal helpers ─────────────────────────────────────────────────────────

async def _get_or_create_config(
    db: AsyncSession, service_code: str = "lookup_credit"
) -> AutomationConfig:
    result = await db.execute(
        select(AutomationConfig).where(AutomationConfig.service_code == service_code)
    )
    config = result.scalar_one_or_none()
    if config:
        return config

    defaults = _SERVICE_DEFAULTS.get(service_code, {"worker_count": 3, "max_retries": 1})
    config = AutomationConfig(service_code=service_code, **defaults)
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


# ─── Overview (per service) ───────────────────────────────────────────────────

@router.get("/overview")
async def get_overview(
    service_code: str = "lookup_credit",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    config = await _get_or_create_config(db, service_code)
    start_dt, end_dt = _resolve_date_range(date_from, date_to, 30)

    job_counts = await db.execute(
        select(AutomationJob.status, func.count(AutomationJob.id))
        .where(
            AutomationJob.service_code == service_code,
            AutomationJob.created_at >= start_dt,
            AutomationJob.created_at < end_dt,
        )
        .group_by(AutomationJob.status)
    )
    counts = {status: count for status, count in job_counts.all()}

    finance = await db.execute(
        select(
            func.sum(func.case(
                (AutomationFinanceEntry.entry_type == "income", AutomationFinanceEntry.amount),
                else_=0,
            )).label("income"),
            func.sum(func.case(
                (AutomationFinanceEntry.entry_type == "expense", AutomationFinanceEntry.amount),
                else_=0,
            )).label("expense"),
        )
        .join(AutomationJob, AutomationJob.id == AutomationFinanceEntry.job_id, isouter=True)
        .where(
            AutomationJob.service_code == service_code,
            AutomationFinanceEntry.created_at >= start_dt,
            AutomationFinanceEntry.created_at < end_dt,
        )
    )
    income, expense = finance.one()

    return {
        "config": _config_to_dict(config),
        "jobs": counts,
        "period": {
            "date_from": start_dt.strftime("%Y-%m-%d"),
            "date_to": (end_dt - timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        "finance": {
            "income": float(income or 0),
            "expense": float(expense or 0),
            "net": float((income or 0) - (expense or 0)),
        },
    }


# ─── Analytics (all services combined) ───────────────────────────────────────

@router.get("/analytics")
async def get_analytics(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    """Per-service cost/revenue/profit breakdown for the admin analytics tab."""
    start_dt, end_dt = _resolve_date_range(date_from, date_to, 30)
    result: dict = {}

    for sc in _ALL_SERVICE_CODES:
        job_counts = await db.execute(
            select(AutomationJob.status, func.count(AutomationJob.id))
            .where(
                AutomationJob.service_code == sc,
                AutomationJob.created_at >= start_dt,
                AutomationJob.created_at < end_dt,
            )
            .group_by(AutomationJob.status)
        )
        counts = {status: cnt for status, cnt in job_counts.all()}

        finance = await db.execute(
            select(
                func.sum(func.case(
                    (AutomationFinanceEntry.entry_type == "income", AutomationFinanceEntry.amount),
                    else_=0,
                )).label("income"),
                func.sum(func.case(
                    (AutomationFinanceEntry.entry_type == "expense", AutomationFinanceEntry.amount),
                    else_=0,
                )).label("expense"),
            )
            .join(AutomationJob, AutomationJob.id == AutomationFinanceEntry.job_id)
            .where(
                AutomationJob.service_code == sc,
                AutomationFinanceEntry.created_at >= start_dt,
                AutomationFinanceEntry.created_at < end_dt,
            )
        )
        income, expense = finance.one()
        income_f = float(income or 0)
        expense_f = float(expense or 0)

        result[sc] = {
            "jobs": counts,
            "total_jobs": sum(counts.values()),
            "success": counts.get("success", 0),
            "noresult": counts.get("noresult", 0),
            "failed": counts.get("failed", 0),
            "income": income_f,
            "expense": expense_f,
            "profit": income_f - expense_f,
        }

    return result


# ─── Config ───────────────────────────────────────────────────────────────────

@router.get("/config")
async def get_config(
    service_code: str = "lookup_credit",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    config = await _get_or_create_config(db, service_code)
    return _config_to_dict(config)


@router.put("/config")
async def update_config(
    body: AutomationConfigUpdate,
    service_code: str = "lookup_credit",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    config = await _get_or_create_config(db, service_code)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(config, key, value)
    config.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


# ─── Proxies ──────────────────────────────────────────────────────────────────

@router.get("/proxies")
async def list_proxies(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    result = await db.execute(
        select(AutomationProxy).order_by(AutomationProxy.is_default.desc(), AutomationProxy.id.asc())
    )
    proxies = result.scalars().all()
    can_see_secrets = _is_owner(current_user)
    return [
        {
            "id": item.id,
            "name": item.name,
            "host": item.host,
            "port": item.port,
            "username": item.username,
            "password": _mask(item.password, can_see_secrets),
            "proxy_type": item.proxy_type,
            "country": item.country,
            "rotate_every": item.rotate_every,
            "is_active": item.is_active,
            "is_default": item.is_default,
            "notes": item.notes,
            "last_error": item.last_error,
        }
        for item in proxies
    ]


@router.post("/proxies")
async def create_proxy(
    body: ProxyBody,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    if body.is_default:
        result = await db.execute(select(AutomationProxy).where(AutomationProxy.is_default == True))
        for item in result.scalars().all():
            item.is_default = False

    proxy = AutomationProxy(**body.model_dump())
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return {"id": proxy.id}


@router.put("/proxies/{proxy_id}")
async def update_proxy(
    proxy_id: int,
    body: ProxyBody,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    proxy = await db.get(AutomationProxy, proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    if body.is_default:
        result = await db.execute(
            select(AutomationProxy).where(
                AutomationProxy.is_default == True, AutomationProxy.id != proxy_id
            )
        )
        for item in result.scalars().all():
            item.is_default = False

    for key, value in body.model_dump().items():
        setattr(proxy, key, value)
    proxy.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.delete("/proxies/{proxy_id}")
async def delete_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    proxy = await db.get(AutomationProxy, proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    await db.delete(proxy)
    await db.commit()
    return {"ok": True}


# ─── API Keys ─────────────────────────────────────────────────────────────────

@router.get("/api-keys")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    result = await db.execute(
        select(AutomationApiKey).order_by(AutomationApiKey.id.asc())
    )
    keys = result.scalars().all()
    can_see_secrets = _is_owner(current_user)
    return [
        {
            "id": item.id,
            "provider": item.provider,
            "name": item.name,
            "key_value": _mask(item.key_value, can_see_secrets),
            "balance": float(item.balance) if item.balance is not None else None,
            "daily_limit": item.daily_limit,
            "is_active": item.is_active,
            "notes": item.notes,
            "last_error": item.last_error,
            "last_used_at": item.last_used_at.isoformat() if item.last_used_at else None,
        }
        for item in keys
    ]


@router.post("/api-keys")
async def create_api_key(
    body: ApiKeyBody,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    api_key = AutomationApiKey(**body.model_dump())
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return {"id": api_key.id}


@router.put("/api-keys/{key_id}")
async def update_api_key(
    key_id: int,
    body: ApiKeyBody,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    api_key = await db.get(AutomationApiKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    for key, value in body.model_dump().items():
        setattr(api_key, key, value)
    api_key.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    api_key = await db.get(AutomationApiKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(api_key)
    await db.commit()
    return {"ok": True}


# ─── Check usfull.info API balance ───────────────────────────────────────────

@router.get("/api-balance")
async def check_api_balance(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    """Fetch live balance from usfull.info API and update stored value."""
    result = await db.execute(
        select(AutomationApiKey)
        .where(AutomationApiKey.provider == "usfull", AutomationApiKey.is_active == True)
        .order_by(AutomationApiKey.id.asc())
    )
    key_record = result.scalar_one_or_none()
    if not key_record:
        return {"balance": None, "error": "No active usfull API key configured"}

    import json
    username = password = None
    if key_record.notes:
        try:
            creds = json.loads(key_record.notes)
            username = creds.get("username")
            password = creds.get("password")
        except Exception:
            parts = key_record.notes.split(":", 1)
            if len(parts) == 2:
                username, password = parts

    try:
        from mirror_bot.services.usfull_service import UsfullClient
        client = UsfullClient(api_key=key_record.key_value, username=username, password=password)
        balance = await client.get_balance()
        key_record.balance = balance
        key_record.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        return {"balance": balance, "key_name": key_record.name}
    except Exception as e:
        return {"balance": None, "error": str(e)}


# ─── Jobs ─────────────────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs(
    service_code: str = "lookup_credit",
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    start_dt, end_dt = _resolve_date_range(date_from, date_to, 30)
    stmt = (
        select(AutomationJob, Order)
        .join(Order, Order.id == AutomationJob.order_id)
        .where(
            AutomationJob.service_code == service_code,
            AutomationJob.created_at >= start_dt,
            AutomationJob.created_at < end_dt,
        )
        .order_by(AutomationJob.created_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(AutomationJob.status == status)

    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": job.id,
            "order_id": job.order_id,
            "service_code": job.service_code,
            "bulk_item_number": job.bulk_item_number,
            "status": job.status,
            "user_id": job.user_id,
            "worker_label": job.worker_label,
            "attempts": job.attempts,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "service_name": order.service_name,
            "order_status": order.status,
            "price": float(order.price),
        }
        for job, order in rows
    ]


# ─── Finance log ──────────────────────────────────────────────────────────────

@router.get("/finance")
async def list_finance_entries(
    service_code: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("automation")),
):
    start_dt, end_dt = _resolve_date_range(date_from, date_to, 30)
    stmt = (
        select(AutomationFinanceEntry)
        .where(
            AutomationFinanceEntry.created_at >= start_dt,
            AutomationFinanceEntry.created_at < end_dt,
        )
        .order_by(AutomationFinanceEntry.created_at.desc())
        .limit(limit)
    )
    if service_code:
        stmt = (
            stmt.join(AutomationJob, AutomationJob.id == AutomationFinanceEntry.job_id, isouter=True)
            .where(AutomationJob.service_code == service_code)
        )

    result = await db.execute(stmt)
    entries = result.scalars().all()
    return [
        {
            "id": item.id,
            "job_id": item.job_id,
            "order_id": item.order_id,
            "entry_type": item.entry_type,
            "source_type": item.source_type,
            "source_ref": item.source_ref,
            "amount": float(item.amount),
            "currency": item.currency,
            "description": item.description,
            "payload": item.payload,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in entries
    ]
