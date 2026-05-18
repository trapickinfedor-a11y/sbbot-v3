"""
API endpoints для Support Tickets
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from web_panel.database import get_db
from web_panel.auth import require_support_access
from shared.database.models import SupportTicket, SupportMessage, User
from mirror_bot.services.support_service import SupportService
from mirror_bot.services.support_notification_service import SupportNotificationService

router = APIRouter()


# ============ Pydantic Models ============

class TicketResponse(BaseModel):
    id: int
    user_id: int
    mirror_bot_id: int
    category: str
    subject: str
    status: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    
    # Дополнительные поля
    user_username: Optional[str] = None
    unread_count: int = 0
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender_type: str
    sender_id: int
    message_text: str
    files: Optional[List[dict]]
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TicketDetailResponse(BaseModel):
    ticket: TicketResponse
    messages: List[MessageResponse]
    user_info: dict
    
    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    message_text: str


class UpdateStatusRequest(BaseModel):
    status: str  # open, in_progress, waiting_user, closed


class TicketStatsResponse(BaseModel):
    total: int
    open: int
    in_progress: int
    waiting_user: int
    closed: int
    by_category: dict


# ============ API Endpoints ============

@router.get("/stats", response_model=TicketStatsResponse)
async def get_tickets_stats(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_support_access())
):
    """Получить статистику по тикетам"""
    
    # Общее количество
    total_result = await session.execute(select(func.count(SupportTicket.id)))
    total = total_result.scalar_one()
    
    # По статусам
    open_result = await session.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == "open")
    )
    open_count = open_result.scalar_one()
    
    in_progress_result = await session.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == "in_progress")
    )
    in_progress_count = in_progress_result.scalar_one()
    
    waiting_result = await session.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == "waiting_user")
    )
    waiting_count = waiting_result.scalar_one()
    
    closed_result = await session.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == "closed")
    )
    closed_count = closed_result.scalar_one()
    
    # По категориям
    categories = ["payment", "product", "general", "partnership"]
    by_category = {}
    
    for cat in categories:
        cat_result = await session.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.category == cat)
        )
        by_category[cat] = cat_result.scalar_one()
    
    return TicketStatsResponse(
        total=total,
        open=open_count,
        in_progress=in_progress_count,
        waiting_user=waiting_count,
        closed=closed_count,
        by_category=by_category
    )


@router.get("/")
async def get_tickets(
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_support_access())
):
    """Получить список тикетов с фильтрами и пагинацией"""
    
    total = await SupportService.get_tickets_count(
        session=session,
        category=category,
        status=status
    )
    
    tickets = await SupportService.get_all_tickets(
        session=session,
        category=category,
        status=status,
        limit=limit,
        offset=offset
    )
    
    items = []
    for ticket in tickets:
        user_result = await session.execute(
            select(User).where(User.user_id == ticket.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        unread_result = await session.execute(
            select(func.count(SupportMessage.id)).where(
                and_(
                    SupportMessage.ticket_id == ticket.id,
                    SupportMessage.is_read == False,
                    SupportMessage.sender_type == "user"
                )
            )
        )
        unread_count = unread_result.scalar_one()
        
        # Compute SLA deadline based on priority
        SLA_MINUTES = {"CRITICAL": 15, "HIGH": 60, "NORMAL": 240, "LOW": 1440}
        priority = getattr(ticket, "priority", "NORMAL") or "NORMAL"
        sla_min = SLA_MINUTES.get(priority, 240)
        sla_due = None
        sla_breached = False
        if ticket.created_at:
            from datetime import timedelta
            sla_due_dt = ticket.created_at + timedelta(minutes=sla_min)
            sla_due = sla_due_dt.isoformat()
            from datetime import datetime as _dt
            if ticket.status not in ("solved", "closed") and sla_due_dt < _dt.utcnow():
                sla_breached = True

        items.append({
            "id": ticket.id,
            "user_id": ticket.user_id,
            "mirror_bot_id": ticket.mirror_bot_id,
            "category": ticket.category,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": priority,
            "sla_due": sla_due,
            "sla_breached": sla_breached,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
            "user_username": f"@{user.username}" if user and user.username else f"#{ticket.user_id}",
            "unread_count": unread_count
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items
    }


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket_detail(
    ticket_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_support_access())
):
    """Получить детальную информацию о тикете"""
    
    ticket = await SupportService.get_ticket_with_messages(session, ticket_id)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Получаем информацию о пользователе
    user_result = await session.execute(
        select(User).where(User.user_id == ticket.user_id)
    )
    user = user_result.scalar_one_or_none()
    
    user_info = {
        "user_id": ticket.user_id,
        "username": f"@{user.username}" if user and user.username else f"#{ticket.user_id}",
        "balance": float(user.balance) if user else 0.0,
        "language": user.language if user else "unknown"
    }
    
    # Формируем ответ
    ticket_dict = {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "mirror_bot_id": ticket.mirror_bot_id,
        "category": ticket.category,
        "subject": ticket.subject,
        "status": ticket.status,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "closed_at": ticket.closed_at,
        "unread_count": 0
    }
    
    messages = [
        MessageResponse(
            id=msg.id,
            ticket_id=msg.ticket_id,
            sender_type=msg.sender_type,
            sender_id=msg.sender_id,
            message_text=msg.message_text,
            files=msg.files,
            is_read=msg.is_read,
            created_at=msg.created_at
        )
        for msg in ticket.messages
    ]
    
    return TicketDetailResponse(
        ticket=TicketResponse(**ticket_dict),
        messages=messages,
        user_info=user_info
    )


@router.post("/{ticket_id}/messages")
async def send_message(
    ticket_id: int,
    message_text: str = Form(...),
    file: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_support_access())
):
    """Отправить сообщение в тикет (от админа) с поддержкой файлов"""
    
    # Проверяем что тикет существует
    ticket = await SupportService.get_ticket_by_id(session, ticket_id)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="Ticket is closed")
    
    # Обрабатываем файл если есть (SEC-1: Secure file upload)
    files_data = None
    if file:
        from web_panel.services.file_upload_service import validate_and_save_upload
        
        try:
            file_path, file_metadata = await validate_and_save_upload(file)
            files_data = [file_metadata]
        except HTTPException:
            raise  # Re-raise validation errors
        except Exception as e:
            logger.error("File upload failed: %s", e)
            raise HTTPException(500, "Failed to process file upload")
    
    # admin_id берём из JWT, не из тела запроса (SEC-5)
    sender_admin_id = current_user.get("admin_id") or 0

    # Добавляем сообщение
    message = await SupportService.add_message_to_ticket(
        session=session,
        ticket_id=ticket_id,
        sender_type="admin",
        sender_id=sender_admin_id,
        message_text=message_text,
        files=files_data
    )
    
    # Отправляем уведомление пользователю
    notification_sent = await SupportNotificationService.notify_user_about_reply(
        session=session,
        ticket_id=ticket_id,
        message_text=message_text,
        files=files_data
    )
    
    return {
        "success": True,
        "message_id": message.id,
        "notification_sent": notification_sent,
        "message": "Message sent successfully",
        "has_file": files_data is not None
    }


@router.put("/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: int,
    request: UpdateStatusRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_support_access())
):
    """Обновить статус тикета"""
    
    valid_statuses = ["open", "in_progress", "waiting_user", "closed"]
    
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    success = await SupportService.update_ticket_status(
        session=session,
        ticket_id=ticket_id,
        status=request.status
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Отправляем уведомление пользователю об изменении статуса
    notification_sent = await SupportNotificationService.notify_user_about_status_change(
        session=session,
        ticket_id=ticket_id,
        new_status=request.status
    )
    
    return {
        "success": True,
        "notification_sent": notification_sent,
        "message": f"Ticket status updated to {request.status}"
    }


@router.post("/{ticket_id}/mark_read")
async def mark_ticket_messages_read(
    ticket_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_support_access())
):
    """Отметить все сообщения тикета как прочитанные (админом)"""
    
    # Отмечаем сообщения от пользователя как прочитанные
    result = await session.execute(
        select(SupportMessage).where(
            and_(
                SupportMessage.ticket_id == ticket_id,
                SupportMessage.is_read == False,
                SupportMessage.sender_type == "user"
            )
        )
    )
    
    messages = result.scalars().all()
    
    for message in messages:
        message.is_read = True
    
    await session.commit()
    
    return {
        "success": True,
        "marked_count": len(messages)
    }


@router.get("/category/{category}")
async def get_tickets_by_category(
    category: str,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_support_access())
):
    """Получить тикеты определенной категории"""
    
    valid_categories = ["payment", "product", "general", "partnership"]
    
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")
    
    return await get_tickets(
        category=category,
        status=status,
        limit=limit,
        offset=offset,
        session=session,
        current_user=current_user,
    )


@router.get("/csat")
async def get_csat_stats(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_support_access())
):
    """CSAT статистика из тикетов поддержки"""
    try:
        from shared.database.models import SupportTicket as NewSupportTicket
        good_r = await session.execute(
            select(func.count(NewSupportTicket.id)).where(NewSupportTicket.csat_score == 3)
        )
        good = good_r.scalar() or 0
        
        ok_r = await session.execute(
            select(func.count(NewSupportTicket.id)).where(NewSupportTicket.csat_score == 2)
        )
        ok = ok_r.scalar() or 0
        
        bad_r = await session.execute(
            select(func.count(NewSupportTicket.id)).where(NewSupportTicket.csat_score == 1)
        )
        bad = bad_r.scalar() or 0
        
        total = good + ok + bad
        
        logger.info("CSAT stats retrieved: good=%d, ok=%d, bad=%d, total=%d", good, ok, bad, total)
        return {"good": good, "ok": ok, "bad": bad, "total": total}
        
    except Exception as exc:
        logger.error("CSAT stats query failed: %s", exc, exc_info=True)
        raise HTTPException(500, "Failed to load CSAT statistics")

