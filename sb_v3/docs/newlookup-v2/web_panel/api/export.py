"""CSV Export API"""
import io
import csv
import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from web_panel.database import get_db
from web_panel.auth import require_finance_access
from web_panel.services.audit_service import log_action
from shared.database.models import User, Order, Transaction

router = APIRouter(prefix="/api/export", tags=["export"])
logger = logging.getLogger(__name__)


def _csv_stream(rows: list, headers: list) -> io.BytesIO:
    """Create CSV bytes with BOM for Excel UTF-8"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    buf = io.BytesIO()
    buf.write(b"\xef\xbb\xbf")  # UTF-8 BOM
    buf.write(output.getvalue().encode("utf-8"))
    buf.seek(0)
    return buf


@router.get("/users")
async def export_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Экспорт пользователей в CSV (требует роль finance/owner)"""
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(10000))
    users = result.scalars().all()
    rows = [
        [u.id, u.user_id, u.username or "", u.mirror_bot_id, u.language, float(u.balance),
         u.referrer_id or "", u.referral_link, u.is_banned,
         u.created_at.isoformat() if u.created_at else ""]
        for u in users
    ]
    headers = ["id", "user_id", "username", "mirror_bot_id", "language", "balance",
               "referrer_id", "referral_link", "is_banned", "created_at"]
    await log_action(
        db, current_user.get("admin_id"), "export_users", "export", None,
        {"rows": len(rows)}, request.client.host if request.client else None,
    )
    await db.commit()
    buf = _csv_stream(rows, headers)
    return StreamingResponse(
        buf, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )


@router.get("/orders")
async def export_orders(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Экспорт заказов в CSV (требует роль finance/owner)"""
    result = await db.execute(select(Order).order_by(Order.created_at.desc()).limit(10000))
    orders = result.scalars().all()
    rows = [
        [o.id, o.user_id, o.mirror_bot_id, o.category, o.service_name,
         float(o.price), o.status, o.is_bulk, o.bulk_count,
         o.created_at.isoformat() if o.created_at else ""]
        for o in orders
    ]
    headers = ["id", "user_id", "mirror_bot_id", "category", "service_name",
               "price", "status", "is_bulk", "bulk_count", "created_at"]
    await log_action(
        db, current_user.get("admin_id"), "export_orders", "export", None,
        {"rows": len(rows)}, request.client.host if request.client else None,
    )
    await db.commit()
    buf = _csv_stream(rows, headers)
    return StreamingResponse(
        buf, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders.csv"},
    )


@router.get("/deposits")
async def export_deposits(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Экспорт транзакций (пополнений) в CSV (требует роль finance/owner)"""
    result = await db.execute(
        select(Transaction).where(Transaction.type == "topup")
        .order_by(Transaction.created_at.desc()).limit(10000)
    )
    txns = result.scalars().all()
    rows = [
        [t.id, t.user_id, t.type, float(t.amount), t.description or "",
         t.created_at.isoformat() if t.created_at else ""]
        for t in txns
    ]
    headers = ["id", "user_id", "type", "amount", "description", "created_at"]
    await log_action(
        db, current_user.get("admin_id"), "export_deposits", "export", None,
        {"rows": len(rows)}, request.client.host if request.client else None,
    )
    await db.commit()
    buf = _csv_stream(rows, headers)
    return StreamingResponse(
        buf, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=deposits.csv"},
    )
