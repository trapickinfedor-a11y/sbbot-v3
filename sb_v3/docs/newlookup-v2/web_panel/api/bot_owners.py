"""API для владельцев ботов: выводы"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetim, timezone
from pydantic import BaseModel
from aiogram import Bot

from web_panel.database import get_db
from web_panel.auth import require_finance_access
from shared.database.models import BotOwner, BotOwnerWithdrawal
from shared.services.ledger_projection_service import LedgerProjectionService
from shared.services.ledger_service import LedgerService
from web_panel.config import web_panel_config
from web_panel.services.audit_service import log_action

router = APIRouter(prefix="/api/bot-owners", tags=["bot-owners"])


class OwnerWithdrawalPayBody(BaseModel):
    tx_hash: str


class OwnerWithdrawalRejectBody(BaseModel):
    reason: str = ""


@router.get("/withdrawals")
async def get_owner_withdrawals(
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Заявки на вывод владельцев ботов"""
    query = select(BotOwnerWithdrawal).order_by(BotOwnerWithdrawal.created_at.desc())
    if status:
        query = query.where(BotOwnerWithdrawal.status == status)
    result = await db.execute(query)
    withdrawals = result.scalars().all()
    items = []
    for w in withdrawals:
        owner_res = await db.execute(select(BotOwner).where(BotOwner.owner_user_id == w.owner_user_id))
        owner = owner_res.scalar_one_or_none()
        items.append({
            "id": w.id,
            "owner_user_id": w.owner_user_id,
            "amount": float(w.amount),
            "payment_method": w.payment_method,
            "payment_network": w.payment_network,
            "requisites": w.requisites,
            "tx_hash": w.tx_hash,
            "status": w.status,
            "reject_reason": w.reject_reason,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "processed_at": w.processed_at.isoformat() if w.processed_at else None,
        })
    return {"withdrawals": items}


@router.post("/withdrawals/{withdrawal_id}/pay")
async def pay_owner_withdrawal(
    withdrawal_id: int,
    body: OwnerWithdrawalPayBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Подтвердить выплату — нужен tx hash, баланс обнуляется, статистика сохраняется"""
    result = await db.execute(select(BotOwnerWithdrawal).where(BotOwnerWithdrawal.id == withdrawal_id))
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Not found")
    if w.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")

    owner_res = await db.execute(select(BotOwner).where(BotOwner.owner_user_id == w.owner_user_id))
    owner = owner_res.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    projected_balance = float((await LedgerProjectionService.get_owner_projection(db, owner.owner_user_id))["balance"])
    if not getattr(w, "funds_reserved", False) and projected_balance < float(w.amount):
        raise HTTPException(status_code=400, detail="Insufficient balance")

    tx_hash = (body.tx_hash or "").strip()
    if not tx_hash:
        raise HTTPException(status_code=400, detail="tx_hash is required")

    paid_amount = w.amount
    if not getattr(w, "funds_reserved", False):
        if not await LedgerService.reserve_owner_withdrawal(
            db,
            owner=owner,
            amount=paid_amount,
            withdrawal_id=w.id,
        ):
            raise HTTPException(status_code=400, detail="Insufficient balance")
        w.funds_reserved = True
    await LedgerService.finalize_owner_withdrawal(
        db,
        owner=owner,
        amount=paid_amount,
        withdrawal_id=w.id,
    )
    w.tx_hash = tx_hash
    w.status = "approved"
    w.processed_at = datetime.now(timezone.utc)
    w.processed_by = current_user.get("telegram_id") or current_user.get("user_id")

    await log_action(
        db,
        current_user.get("admin_id"),
        "bot_owner_withdrawal_pay",
        "bot_owner_withdrawal",
        w.id,
        {
            "owner_user_id": w.owner_user_id,
            "amount": float(w.amount),
            "tx_hash": tx_hash,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()

    if web_panel_config.main_bot_token:
        bot = Bot(token=web_panel_config.main_bot_token)
        try:
            network_line = f"Сеть: {w.payment_network}\n" if w.payment_network else ""
            await bot.send_message(
                w.owner_user_id,
                (
                    f"✅ Выплата выполнена\n\n"
                    f"Сумма: ${float(w.amount):.2f}\n"
                    f"Валюта: {w.payment_method or '-'}\n"
                    f"{network_line}"
                    f"Hash: {w.tx_hash}\n"
                    f"Реквизиты: {w.requisites or '-'}"
                ),
                parse_mode=None
            )
        finally:
            await bot.session.close()

    return {"ok": True, "message": "Выплата подтверждена, баланс обновлён"}


@router.post("/withdrawals/{withdrawal_id}/reject")
async def reject_owner_withdrawal(
    withdrawal_id: int,
    body: OwnerWithdrawalRejectBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Отклонить заявку"""
    result = await db.execute(select(BotOwnerWithdrawal).where(BotOwnerWithdrawal.id == withdrawal_id))
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Not found")
    if w.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")

    w.status = "rejected"
    w.processed_at = datetime.now(timezone.utc)
    w.processed_by = current_user.get("telegram_id") or current_user.get("user_id")
    w.reject_reason = (body.reason or "").strip() or None
    owner = await db.scalar(select(BotOwner).where(BotOwner.owner_user_id == w.owner_user_id))
    if owner and getattr(w, "funds_reserved", False):
        await LedgerService.release_owner_withdrawal_reservation(
            db,
            owner=owner,
            amount=w.amount,
            withdrawal_id=w.id,
        )

    await log_action(
        db,
        current_user.get("admin_id"),
        "bot_owner_withdrawal_reject",
        "bot_owner_withdrawal",
        w.id,
        {
            "owner_user_id": w.owner_user_id,
            "amount": float(w.amount),
            "reason": w.reject_reason,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()

    if web_panel_config.main_bot_token:
        bot = Bot(token=web_panel_config.main_bot_token)
        try:
            network_line = f"Сеть: {w.payment_network}\n" if w.payment_network else ""
            text = (
                f"❌ Выплата отклонена\n\n"
                f"Сумма: ${float(w.amount):.2f}\n"
                f"Валюта: {w.payment_method or '-'}\n"
                f"{network_line}"
                f"Реквизиты: {w.requisites or '-'}"
            )
            if w.reject_reason:
                text += f"\nПричина: {w.reject_reason}"
            await bot.send_message(w.owner_user_id, text, parse_mode=None)
        finally:
            await bot.session.close()

    return {"ok": True}
