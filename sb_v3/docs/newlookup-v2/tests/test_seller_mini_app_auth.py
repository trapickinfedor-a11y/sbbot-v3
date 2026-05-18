from __future__ import annotations

import hashlib
import hmac
import json
import time
import unittest
from urllib.parse import quote

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from seller_bot.config import seller_bot_config
from shared.database.models import Base, Seller
from web_panel.api.seller_mini_app import get_current_seller_from_webapp


def _build_init_data(user_payload: dict, bot_token: str, auth_date: int | None = None) -> str:
    auth_date = auth_date or int(time.time())
    pairs = {
        "auth_date": str(auth_date),
        "query_id": "AAEAAAE",
        "user": json.dumps(user_payload, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return "&".join(f"{k}={quote(v)}" for k, v in pairs.items())


class SellerMiniAppAuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)
        self.original_token = seller_bot_config.bot_token
        seller_bot_config.bot_token = "999999:test-token"

    async def asyncTearDown(self) -> None:
        seller_bot_config.bot_token = self.original_token
        await self.engine.dispose()

    async def test_get_current_seller_from_webapp_accepts_valid_init_data(self) -> None:
        async with self.session_maker() as session:
            seller = Seller(
                telegram_id=555001,
                username="miniapp_seller",
                display_name="Mini App Seller",
                is_approved=True,
                is_active=True,
                access_status="active",
            )
            session.add(seller)
            await session.commit()

            init_data = _build_init_data({"id": seller.telegram_id, "username": seller.username}, seller_bot_config.bot_token)
            actor = await get_current_seller_from_webapp(
                db=session,
                telegram_init_data=init_data,
                dev_seller_telegram_id=None,
            )
            self.assertEqual(actor.seller.telegram_id, seller.telegram_id)
            self.assertTrue(actor.is_owner)
