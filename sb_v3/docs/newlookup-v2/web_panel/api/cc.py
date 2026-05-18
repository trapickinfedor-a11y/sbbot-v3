"""
CC admin page helper — re-uses cc_catalog and seller_moderation APIs.
This module only registers an empty router to satisfy the import in main.py.
The /cc page template directly calls /api/cc-catalog and /api/seller-moderation endpoints.
"""
from fastapi import APIRouter

router = APIRouter(tags=["cc"])
