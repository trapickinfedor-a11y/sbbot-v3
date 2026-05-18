from __future__ import annotations

from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from shared.database.models import Seller, SellerDepositPayment
from shared.services.btcpay_service import BTCPayService
from shared.services.seller_deposit_service import SellerDepositService
from web_panel.auth import require_finance_access
from web_panel.database import get_db
from web_panel.services.audit_service import log_action

router = APIRouter(prefix="/api/seller-deposits", tags=["seller-deposits"])


class SellerDepositPaymentResponse(BaseModel):
    id: int
    seller_id: int
    seller_name: str
    package_code: str
    package_label: str
    categories: List[str]
    amount: Decimal
    currency: str
    provider: str
    provider_invoice_id: Optional[str]
    checkout_url: Optional[str]
    status: str
    created_at: str
    updated_at: str
    paid_at: Optional[str]
    expires_at: Optional[str]


def _serialize_payment(payment: SellerDepositPayment, seller: Optional[Seller]) -> SellerDepositPaymentResponse:
    seller_name = "-"
    if seller:
        seller_name = seller.display_name or seller.username or f"Seller {seller.id}"
    return SellerDepositPaymentResponse(
        id=payment.id,
        seller_id=payment.seller_id,
        seller_name=seller_name,
        package_code=payment.package_code,
        package_label=SellerDepositService.package_label(payment.package_code),
        categories=list(payment.categories or []),
        amount=payment.amount,
        currency=payment.currency,
        provider=payment.provider,
        provider_invoice_id=payment.provider_invoice_id,
        checkout_url=payment.checkout_url,
        status=payment.status,
        created_at=payment.created_at.isoformat() if payment.created_at else "",
        updated_at=payment.updated_at.isoformat() if payment.updated_at else "",
        paid_at=payment.paid_at.isoformat() if payment.paid_at else None,
        expires_at=payment.expires_at.isoformat() if payment.expires_at else None,
    )


@router.get("", response_model=List[SellerDepositPaymentResponse])
async def list_seller_deposit_payments(
    seller_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    stmt = (
        select(SellerDepositPayment, Seller)
        .join(Seller, Seller.id == SellerDepositPayment.seller_id)
        .order_by(desc(SellerDepositPayment.created_at), desc(SellerDepositPayment.id))
        .limit(limit)
    )
    if seller_id is not None:
        stmt = stmt.where(SellerDepositPayment.seller_id == seller_id)
    if status:
        stmt = stmt.where(SellerDepositPayment.status == status)
    rows = (await db.execute(stmt)).all()
    return [_serialize_payment(payment, seller) for payment, seller in rows]


@router.post("/{payment_id}/sync", response_model=SellerDepositPaymentResponse)
async def sync_seller_deposit_payment(
    payment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    payment = await db.scalar(select(SellerDepositPayment).where(SellerDepositPayment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=404, detail="Seller deposit payment not found")
    if not payment.provider_invoice_id:
        raise HTTPException(status_code=400, detail="Payment has no provider invoice id")
    invoice_payload = await BTCPayService.fetch_invoice(payment.provider_invoice_id)
    synced = await SellerDepositService.sync_invoice_status(
        db,
        payment.provider_invoice_id,
        invoice_payload=invoice_payload,
    )
    seller = await db.scalar(select(Seller).where(Seller.id == payment.seller_id))
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_deposit_sync",
        "seller_deposit_payment",
        payment.id,
        {
            "seller_id": payment.seller_id,
            "provider_invoice_id": payment.provider_invoice_id,
            "status": synced.status if synced else payment.status,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    return _serialize_payment(synced or payment, seller)


@router.post("/btcpay/webhook")
async def btcpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    btcpay_sig: Optional[str] = Header(default=None, alias="BTCPay-Sig"),
):
    raw_body = await request.body()
    if not BTCPayService.verify_webhook_signature(raw_body, btcpay_sig):
        raise HTTPException(status_code=401, detail="Invalid BTCPay webhook signature")

    payload = BTCPayService.decode_webhook_body(raw_body)
    invoice_id = BTCPayService.parse_webhook_invoice_id(payload)
    if not invoice_id:
        return {"ok": True, "status": "ignored", "reason": "invoice_id_missing"}

    invoice_payload = await BTCPayService.fetch_invoice(invoice_id)
    payment = await SellerDepositService.sync_invoice_status(
        db,
        invoice_id,
        invoice_payload=invoice_payload,
    )
    if not payment:
        return {"ok": True, "status": "ignored", "reason": "payment_not_found"}
    if payment.status != "paid":
        return {"ok": True, "status": "synced", "payment_id": payment.id, "payment_status": payment.status}
    return {"ok": True, "status": "processed", "payment_id": payment.id, "payment_status": payment.status}
