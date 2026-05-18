"""
API для авторизации
"""

from fastapi import APIRouter, HTTPException, Response, status, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.admin_catalog_access import get_admin_allowed_catalogs
from web_panel.auth import build_access_profile, create_access_token, get_current_user, normalize_permissions
from web_panel.config import web_panel_config
from web_panel.database import get_db
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
from web_panel.services.admin_service import ensure_first_admin, verify_admin_password
from web_panel.services.audit_service import log_action

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Авторизация админа. Проверка по таблице admins.
    Первый owner создаётся из ADMIN_USERNAME/ADMIN_PASSWORD при первом запуске.
    """
    await ensure_first_admin(db)
    admin = await verify_admin_password(db, credentials.username, credentials.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    access_token = create_access_token(data={
        "sub": admin.username,
        "role": admin.role,
        "role_id": getattr(admin, "role_id", None),
        "role_name": getattr(getattr(admin, "role_obj", None), "name", None),
        "admin_id": admin.id,
        "allowed_catalogs": get_admin_allowed_catalogs(admin),
        "permissions": normalize_permissions(getattr(getattr(admin, "role_obj", None), "permissions", None)),
    })
    client_ip = request.client.host if request.client else None
    await log_action(db, admin.id, "login", ip_address=client_ip)
    await db.commit()
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=web_panel_config.access_token_expire_minutes * 60,
        samesite="lax",
        secure=request.url.scheme == "https",
        httponly=True,
        path="/",
    )
    return LoginResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Завершить сессию — удаляет httponly cookie."""
    await log_action(db, current_user.get("admin_id"), "logout")
    await db.commit()
    response.delete_cookie(key="access_token", path="/")
    return {"ok": True, "message": "Logged out successfully"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Получить информацию о текущем залогиненном админе"""
    profile = build_access_profile(
        current_user.get("role", "admin"),
        current_user.get("allowed_catalogs"),
        current_user.get("permissions"),
    )
    return {
        "username": current_user["username"],
        "admin_id": current_user.get("admin_id"),
        "role": current_user.get("role", "admin"),
        "role_id": current_user.get("role_id"),
        "role_name": current_user.get("role_name"),
        "allowed_catalogs": current_user.get("allowed_catalogs", []),
        **profile,
    }

