"""
API для управления жалобами
"""

import aiohttp
import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetim, timezone

from web_panel.auth import require_complaints_access
from web_panel.database import get_db
from shared.database.models import Complaint, Worker, User, Order
from shared.security.internal_api import build_internal_api_headers

logger = logging.getLogger(__name__)

router = APIRouter()


async def notify_worker_about_complaint_resolution(worker_telegram_id: int, complaint_id: int, status: str, admin_response: str, action: str = None):
    """
    Отправить уведомление воркеру о решении жалобы через worker_bot API
    """
    try:
        base_url = (
            os.getenv("WORKER_BOT_URL")
            or os.getenv("WORKER_BOT_API_URL")
            or os.getenv("SUPPORT_BOT_URL")
            or "http://worker_bot:8181"
        ).rstrip("/")
        worker_bot_api_url = f"{base_url}/api/notifications/complaint-resolved"
        
        payload = {
            "complaint_id": complaint_id,
            "worker_telegram_id": worker_telegram_id,
            "status": status,
            "admin_response": admin_response,
            "action": action
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.post(
                worker_bot_api_url,
                json=payload,
                headers=build_internal_api_headers(),
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully notified worker {worker_telegram_id} about complaint {complaint_id} resolution")
                    return True
                else:
                    logger.error(f"Failed to notify worker: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        logger.error(f"Error notifying worker about complaint resolution: {e}")
        return False


class ComplaintResponse(BaseModel):
    id: int
    worker_id: int
    user_id: int
    order_id: Optional[int]
    reason: str
    description: str
    status: str
    admin_response: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    
    # Дополнительная информация
    worker_username: Optional[str] = None
    user_info: Optional[dict] = None
    
    class Config:
        from_attributes = True


class ComplaintResolveRequest(BaseModel):
    admin_response: str
    action: str  # ban_user, warn_user, reject


class ComplaintStatsResponse(BaseModel):
    total: int
    pending: int
    reviewed: int
    resolved: int
    rejected: int


class ComplaintUpdate(BaseModel):
    status: Optional[str] = None
    admin_response: Optional[str] = None


@router.get("/stats", response_model=ComplaintStatsResponse)
async def get_complaints_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_complaints_access())
):
    """Получить статистику по жалобам"""
    
    total_result = await db.execute(select(func.count(Complaint.id)))
    total = total_result.scalar_one()
    
    pending_result = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.status == "pending")
    )
    pending = pending_result.scalar_one()
    
    reviewed_result = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.status == "reviewed")
    )
    reviewed = reviewed_result.scalar_one()
    
    resolved_result = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.status == "resolved")
    )
    resolved = resolved_result.scalar_one()
    
    rejected_result = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.status == "rejected")
    )
    rejected = rejected_result.scalar_one()
    
    return ComplaintStatsResponse(
        total=total,
        pending=pending,
        reviewed=reviewed,
        resolved=resolved,
        rejected=rejected
    )


@router.get("/", response_model=List[ComplaintResponse])
async def get_complaints(
    status: Optional[str] = None,
    worker_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_complaints_access())
):
    """Получить список жалоб"""
    
    stmt = select(Complaint)
    
    if status:
        stmt = stmt.where(Complaint.status == status)
    
    if worker_id:
        stmt = stmt.where(Complaint.worker_id == worker_id)
    
    stmt = stmt.order_by(Complaint.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    complaints = result.scalars().all()
    
    # Добавляем дополнительную информацию
    response = []
    for complaint in complaints:
        # Получаем worker info
        worker_result = await db.execute(
            select(Worker).where(Worker.id == complaint.worker_id)
        )
        worker = worker_result.scalar_one_or_none()
        
        # Получаем user info
        user_result = await db.execute(
            select(User).where(User.user_id == complaint.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        complaint_dict = {
            "id": complaint.id,
            "worker_id": complaint.worker_id,
            "user_id": complaint.user_id,
            "order_id": complaint.order_id,
            "reason": complaint.reason,
            "description": complaint.description,
            "status": complaint.status,
            "admin_response": complaint.admin_response,
            "created_at": complaint.created_at,
            "resolved_at": complaint.resolved_at,
            "worker_username": worker.username if worker else None,
            "user_info": {
                "user_id": user.user_id,
                "balance": float(user.balance),
                "is_banned": user.is_banned
            } if user else None
        }
        
        response.append(ComplaintResponse(**complaint_dict))
    
    return response


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    complaint_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_complaints_access())
):
    """Получить детали жалобы"""
    
    stmt = select(Complaint).where(Complaint.id == complaint_id)
    result = await db.execute(stmt)
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    # Получаем дополнительную информацию
    worker_result = await db.execute(
        select(Worker).where(Worker.id == complaint.worker_id)
    )
    worker = worker_result.scalar_one_or_none()
    
    user_result = await db.execute(
        select(User).where(User.user_id == complaint.user_id)
    )
    user = user_result.scalar_one_or_none()
    
    complaint_dict = {
        "id": complaint.id,
        "worker_id": complaint.worker_id,
        "user_id": complaint.user_id,
        "order_id": complaint.order_id,
        "reason": complaint.reason,
        "description": complaint.description,
        "status": complaint.status,
        "admin_response": complaint.admin_response,
        "created_at": complaint.created_at,
        "resolved_at": complaint.resolved_at,
        "worker_username": worker.username if worker else None,
        "user_info": {
            "user_id": user.user_id,
            "balance": float(user.balance),
            "is_banned": user.is_banned,
            "ban_reason": user.ban_reason
        } if user else None
    }
    
    return ComplaintResponse(**complaint_dict)


@router.put("/{complaint_id}")
async def update_complaint(
    complaint_id: int,
    data: ComplaintUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_complaints_access())
):
    """Обновить жалобу"""
    
    stmt = select(Complaint).where(Complaint.id == complaint_id)
    result = await db.execute(stmt)
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    # Обновляем поля
    if data.status is not None:
        valid_statuses = ["pending", "investigating", "resolved", "rejected"]
        if data.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        complaint.status = data.status
        
        if data.status in ["resolved", "rejected"]:
            complaint.resolved_at = datetime.now(timezone.utc)
    
    if data.admin_response is not None:
        complaint.admin_response = data.admin_response
    
    await db.commit()
    await db.refresh(complaint)
    
    # Если статус изменился на resolved или rejected, уведомляем воркера
    if data.status in ["resolved", "rejected"]:
        worker_result = await db.execute(
            select(Worker).where(Worker.id == complaint.worker_id)
        )
        worker = worker_result.scalar_one_or_none()
        
        if worker:
            await notify_worker_about_complaint_resolution(
                worker_telegram_id=worker.telegram_id,
                complaint_id=complaint_id,
                status=complaint.status,
                admin_response=data.admin_response or "No additional response provided",
                action=None  # Для простого обновления статуса без конкретного действия
            )
    
    return {
        "message": "Complaint updated successfully",
        "complaint_id": complaint_id,
        "status": complaint.status
    }


@router.put("/{complaint_id}/resolve")
async def resolve_complaint(
    complaint_id: int,
    request: ComplaintResolveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_complaints_access())
):
    """Разрешить жалобу"""
    
    stmt = select(Complaint).where(Complaint.id == complaint_id)
    result = await db.execute(stmt)
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    # Обновляем статус жалобы
    complaint.admin_response = request.admin_response
    complaint.resolved_at = datetime.now(timezone.utc)
    
    # Выполняем действие
    if request.action == "ban_user":
        # Баним пользователя
        user_result = await db.execute(
            select(User).where(User.user_id == complaint.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            user.is_banned = True
            user.ban_reason = f"Banned by admin: {request.admin_response}"
        
        complaint.status = "resolved"
    
    elif request.action == "warn_user":
        complaint.status = "resolved"
    
    elif request.action == "reject":
        complaint.status = "rejected"
    
    await db.commit()
    
    # Получаем telegram_id воркера для уведомления
    worker_result = await db.execute(
        select(Worker).where(Worker.id == complaint.worker_id)
    )
    worker = worker_result.scalar_one_or_none()
    
    if worker:
        # Отправляем уведомление воркеру
        await notify_worker_about_complaint_resolution(
            worker_telegram_id=worker.telegram_id,
            complaint_id=complaint_id,
            status=complaint.status,
            admin_response=request.admin_response,
            action=request.action
        )
    
    return {
        "success": True,
        "complaint_id": complaint_id,
        "action": request.action,
        "status": complaint.status
    }


@router.put("/{complaint_id}/status")
async def update_complaint_status(
    complaint_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_complaints_access())
):
    """Обновить статус жалобы"""
    
    valid_statuses = ["pending", "reviewed", "resolved", "rejected"]
    
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    stmt = select(Complaint).where(Complaint.id == complaint_id)
    result = await db.execute(stmt)
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    complaint.status = status
    
    if status in ["resolved", "rejected"]:
        complaint.resolved_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {
        "success": True,
        "complaint_id": complaint_id,
        "status": status
    }

