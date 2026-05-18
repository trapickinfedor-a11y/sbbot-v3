from __future__ import annotations

"""Admin Panel API — Knowledge Base management"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import KnowledgeBaseArticle
from web_panel.auth import require_page_access
from web_panel.database import get_db
from web_panel.services.audit_service import log_action

router = APIRouter()


class ArticleCreate(BaseModel):
    title: str
    body: str
    keywords: Optional[str] = None
    category: str = "general"
    audience: str = "user"
    is_active: bool = True


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    keywords: Optional[str] = None
    category: Optional[str] = None
    audience: Optional[str] = None
    is_active: Optional[bool] = None


def _serialize(art: KnowledgeBaseArticle) -> dict:
    return {
        "id": art.id,
        "title": art.title,
        "body": art.body,
        "keywords": art.keywords,
        "category": art.category,
        "audience": art.audience,
        "is_active": art.is_active,
        "views": art.views,
        "helpful_votes": art.helpful_votes,
        "created_at": art.created_at.isoformat() if art.created_at else None,
        "updated_at": art.updated_at.isoformat() if art.updated_at else None,
    }


@router.get("/")
async def list_articles(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("knowledge-base")),
):
    r = await db.execute(
        select(KnowledgeBaseArticle).order_by(KnowledgeBaseArticle.id.desc())
    )
    return [_serialize(a) for a in r.scalars().all()]


@router.post("/")
async def create_article(
    payload: ArticleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("knowledge-base")),
):
    art = KnowledgeBaseArticle(
        title=payload.title,
        body=payload.body,
        keywords=payload.keywords,
        category=payload.category,
        audience=payload.audience,
        is_active=payload.is_active,
    )
    db.add(art)
    await db.flush()
    await log_action(
        db, current_user.get("admin_id"), "kb_create", "kb_article", art.id,
        {"title": art.title}, request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(art)
    return _serialize(art)


@router.put("/{article_id}")
async def update_article(
    article_id: int,
    payload: ArticleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("knowledge-base")),
):
    art = await db.get(KnowledgeBaseArticle, article_id)
    if not art:
        raise HTTPException(status_code=404, detail="Article not found")
    if payload.title is not None:
        art.title = payload.title
    if payload.body is not None:
        art.body = payload.body
    if payload.keywords is not None:
        art.keywords = payload.keywords
    if payload.category is not None:
        art.category = payload.category
    if payload.audience is not None:
        art.audience = payload.audience
    if payload.is_active is not None:
        art.is_active = payload.is_active
    await log_action(
        db, current_user.get("admin_id"), "kb_update", "kb_article", art.id,
        {"title": art.title}, request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(art)
    return _serialize(art)


@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("knowledge-base")),
):
    art = await db.get(KnowledgeBaseArticle, article_id)
    if not art:
        raise HTTPException(status_code=404, detail="Article not found")
    await db.delete(art)
    await log_action(
        db, current_user.get("admin_id"), "kb_delete", "kb_article", article_id,
        {"title": art.title}, request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "deleted": article_id}
