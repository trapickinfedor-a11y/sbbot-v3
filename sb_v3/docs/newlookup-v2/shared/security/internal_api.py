import os
import secrets
from typing import Dict, Optional

from fastapi import Header, HTTPException, status


def get_internal_api_token() -> str:
    token = os.getenv("INTERNAL_API_TOKEN", "").strip()
    return token


def build_internal_api_headers() -> Dict[str, str]:
    token = get_internal_api_token()
    return {"X-Internal-Token": token} if token else {}


async def verify_internal_api_request(
    x_internal_token: Optional[str] = Header(default=None),
):
    expected = get_internal_api_token()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal API token is not configured",
        )
    if not x_internal_token or not secrets.compare_digest(x_internal_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API token",
        )
