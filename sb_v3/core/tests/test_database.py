"""Complete pytest suite for database.py — all functions async via aiosqlite."""
import pytest
import asyncio
import sys
import time
import json
import collections
from pathlib import Path

# Ensure the module can be imported from the right location
sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db_module


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
async def fresh_db(tmp_path):
    """Fresh DB for each test, using tmp_path to avoid touching real DB."""
    db_path = tmp_path / "test.db"
    original = db_module.DB_PATH
    db_module.DB_PATH = db_path
    # Wipe in-memory rate-window so tests are independent
    db_module._api_rate_window.clear()
    await db_module.init_db()
    yield db_module
    db_module.DB_PATH = original
    db_module._api_rate_window.clear()


# ── Users ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_user_creates_and_returns(fresh_db):
    result = await fresh_db.upsert_user(1, "alice", "Alice Smith")
    assert result["user_id"] == 1
    assert result["username"] == "alice"
    assert result["full_name"] == "Alice Smith"
    assert result["balance"] == 0.0


@pytest.mark.asyncio
async def test_upsert_user_updates_existing(fresh_db):
    await fresh_db.upsert_user(1, "alice", "Alice Smith")
    result = await fresh_db.upsert_user(1, "alice_updated", "Alice Jones")
    assert result["username"] == "alice_updated"
    assert result["full_name"] == "Alice Jones"
    # balance should be preserved (still 0)
    assert result["balance"] == 0.0


@pytest.mark.asyncio
async def test_get_user_returns_dict(fresh_db):
    await fresh_db.upsert_user(2, "bob", "Bob Brown")
    result = await fresh_db.get_user(2)
    assert isinstance(result, dict)
    assert result["user_id"] == 2
    assert result["username"] == "bob"


@pytest.mark.asyncio
async def test_get_user_returns_none_for_unknown(fresh_db):
    result = await fresh_db.get_user(99999)
    assert result is None


@pytest.mark.asyncio
async def test_set_admin_sets_flag(fresh_db):
    await fresh_db.upsert_user(3, "charlie", "Charlie")
    await fresh_db.set_admin(3, True)
    user = await fresh_db.get_user(3)
    assert user["is_admin"] == 1
    await fresh_db.set_admin(3, False)
    user = await fresh_db.get_user(3)
    assert user["is_admin"] == 0


@pytest.mark.asyncio
async def test_set_banned_sets_flag(fresh_db):
    await fresh_db.upsert_user(4, "dan", "Dan")
    await fresh_db.set_banned(4, True)
    user = await fresh_db.get_user(4)
    assert user["is_banned"] == 1
    await fresh_db.set_banned(4, False)
    user = await fresh_db.get_user(4)
    assert user["is_banned"] == 0


@pytest.mark.asyncio
async def test_deduct_balance_subtracts(fresh_db):
    await fresh_db.upsert_user(5, "eve", "Eve")
    # Credit some balance first
    async with fresh_db.aiosqlite.connect(fresh_db.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance=? WHERE user_id=?", (50.0, 5)
        )
        await db.commit()
    ok = await fresh_db.deduct_balance(5, 10.0, "test deduction")
    assert ok is True
    user = await fresh_db.get_user(5)
    assert user["balance"] == 40.0


@pytest.mark.asyncio
async def test_deduct_balance_insufficient_returns_false(fresh_db):
    await fresh_db.upsert_user(6, "frank", "Frank")
    async with fresh_db.aiosqlite.connect(fresh_db.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance=? WHERE user_id=?", (5.0, 6)
        )
        await db.commit()
    ok = await fresh_db.deduct_balance(6, 100.0)
    assert ok is False
    user = await fresh_db.get_user(6)
    assert user["balance"] == 5.0  # unchanged


# ── Settings ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_get_setting_roundtrip(fresh_db):
    await fresh_db.set_setting("my_key", "my_value")
    val = await fresh_db.get_setting("my_key")
    assert val == "my_value"


@pytest.mark.asyncio
async def test_get_setting_unknown_returns_empty_string(fresh_db):
    val = await fresh_db.get_setting("nonexistent_key_xyz")
    assert val == ""


@pytest.mark.asyncio
async def test_get_all_settings_returns_dict(fresh_db):
    await fresh_db.set_setting("key_a", "val_a")
    await fresh_db.set_setting("key_b", "val_b")
    settings = await fresh_db.get_all_settings()
    assert isinstance(settings, dict)
    assert settings["key_a"] == "val_a"
    assert settings["key_b"] == "val_b"


# ── API Keys ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_api_key_returns_dict(fresh_db):
    await fresh_db.upsert_user(10, "apiuser", "API User")
    result = await fresh_db.create_api_key(10, "test_label")
    assert isinstance(result, dict)
    assert "api_key" in result
    assert result["api_key"].startswith("sk_")
    assert result["user_id"] == 10
    assert result["label"] == "test_label"
    assert "id" in result


@pytest.mark.asyncio
async def test_get_api_key_by_key_finds_by_string(fresh_db):
    await fresh_db.upsert_user(11, "keyuser", "Key User")
    created = await fresh_db.create_api_key(11)
    found = await fresh_db.get_api_key_by_key(created["api_key"])
    assert found is not None
    assert found["api_key"] == created["api_key"]


@pytest.mark.asyncio
async def test_get_api_key_by_key_returns_none_for_invalid(fresh_db):
    result = await fresh_db.get_api_key_by_key("sk_invalid_key_string")
    assert result is None


@pytest.mark.asyncio
async def test_get_api_keys_for_user_returns_list(fresh_db):
    await fresh_db.upsert_user(12, "listuser", "List User")
    await fresh_db.create_api_key(12, "key1")
    await fresh_db.create_api_key(12, "key2")
    keys = await fresh_db.get_api_keys_for_user(12)
    assert isinstance(keys, list)
    assert len(keys) == 2


@pytest.mark.asyncio
async def test_revoke_api_key_deletes_row(fresh_db):
    await fresh_db.upsert_user(13, "revuser", "Revoke User")
    created = await fresh_db.create_api_key(13)
    key_id = created["id"]
    ok = await fresh_db.revoke_api_key(key_id, 13)
    assert ok is True
    found = await fresh_db.get_api_keys_for_user(13)
    assert len(found) == 0


@pytest.mark.asyncio
async def test_revoke_api_key_wrong_user_returns_false(fresh_db):
    await fresh_db.upsert_user(14, "otheruser", "Other User")
    await fresh_db.upsert_user(15, "attacker", "Attacker")
    created = await fresh_db.create_api_key(14)
    ok = await fresh_db.revoke_api_key(created["id"], 15)  # wrong user
    assert ok is False


@pytest.mark.asyncio
async def test_check_api_rate_limit_within_limit(fresh_db):
    await fresh_db.upsert_user(20, "rateuser", "Rate User")
    created = await fresh_db.create_api_key(20)
    key_id = created["id"]
    # First call — within limit
    allowed, remaining, rate = await fresh_db.check_api_rate_limit(key_id)
    assert allowed is True
    assert remaining >= 0
    assert rate == created["rate_limit"]


@pytest.mark.asyncio
async def test_check_api_rate_limit_over_limit(fresh_db):
    await fresh_db.upsert_user(21, "ratelimit", "Rate Limit")
    created = await fresh_db.create_api_key(21)
    key_id = created["id"]
    rate_limit = created["rate_limit"]
    # Exhaust the rate limit
    for _ in range(rate_limit):
        await fresh_db.check_api_rate_limit(key_id)
    # Next call should be blocked
    allowed, remaining, rate = await fresh_db.check_api_rate_limit(key_id)
    assert allowed is False
    assert remaining == 0
    assert rate == rate_limit


@pytest.mark.asyncio
async def test_increment_api_usage_increases_counters(fresh_db):
    await fresh_db.upsert_user(22, "incuser", "Incr User")
    created = await fresh_db.create_api_key(22)
    key_id = created["id"]
    # Consume one slot in rate window first
    await fresh_db.check_api_rate_limit(key_id)
    before = created["searches_today"]
    await fresh_db.increment_api_usage(key_id, 1)
    # Re-fetch
    after = await fresh_db.get_api_key_by_key(created["api_key"])
    assert after["searches_today"] == before + 1
    assert after["total_requests"] > 0


# ── API Tiers ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_api_tier_settings_returns_dict(fresh_db):
    # init_db seeds starter tier settings
    settings = await fresh_db.get_api_tier_settings("starter")
    assert isinstance(settings, dict)
    assert "cost" in settings
    assert "daily" in settings
    assert "rate" in settings
    assert settings["cost"] == 29.99
    assert settings["daily"] == 100.0
    assert settings["rate"] == 10.0


@pytest.mark.asyncio
async def test_get_api_tier_settings_unknown_tier_returns_empty(fresh_db):
    settings = await fresh_db.get_api_tier_settings("nonexistent_tier_xyz")
    assert isinstance(settings, dict)
    assert settings == {}


@pytest.mark.asyncio
async def test_update_api_key_tier_updates_fields(fresh_db):
    await fresh_db.upsert_user(30, "tieruser", "Tier User")
    created = await fresh_db.create_api_key(30)
    key_id = created["id"]
    # Upgrade to pro tier (seeds settings for pro)
    await fresh_db.update_api_key_tier(key_id, 30, "pro")
    updated = await fresh_db.get_api_key_by_key(created["api_key"])
    assert updated["tier"] == "pro"
    assert updated["daily_limit"] == 500
    assert updated["rate_limit"] == 30


# ── Rate limiting (check_rate_limit) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_rate_limit_within_window(fresh_db):
    ok = await fresh_db.check_rate_limit(100, "test_action", max_count=5, window_seconds=3600)
    assert ok is True


@pytest.mark.asyncio
async def test_check_rate_limit_first_request(fresh_db):
    # Fresh user/action should always return True and create entry
    ok = await fresh_db.check_rate_limit(101, "first_action", max_count=3, window_seconds=3600)
    assert ok is True


@pytest.mark.asyncio
async def test_check_rate_limit_exceeds_max_count(fresh_db):
    user_id = 102
    action = "burst_action"
    max_count = 3
    window_seconds = 3600
    # Fill up the window
    for i in range(max_count):
        ok = await fresh_db.check_rate_limit(user_id, action, max_count=max_count, window_seconds=window_seconds)
        assert ok is True
    # Exceed
    ok = await fresh_db.check_rate_limit(user_id, action, max_count=max_count, window_seconds=window_seconds)
    assert ok is False


# ── Daily limits ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_daily_limit_within_limit(fresh_db):
    await fresh_db.upsert_user(200, "dailyuser", "Daily User")
    allowed, remaining, limit = await fresh_db.check_daily_limit(200)
    assert allowed is True
    assert remaining >= 0
    assert limit > 0


@pytest.mark.asyncio
async def test_check_daily_limit_exceeded(fresh_db):
    await fresh_db.upsert_user(201, "limituser", "Limit User")
    # Exhaust the daily limit by filling searches
    for _ in range(20):
        await fresh_db.save_search(
            user_id=201,
            search_type="phone",
            query="test",
            result_json="{}",
            cost_user=1.0,
            cost_sb=0.5,
        )
    allowed, remaining, limit = await fresh_db.check_daily_limit(201)
    assert allowed is False
    assert remaining < 0  # exceeded, 20 searches vs default limit 5


@pytest.mark.asyncio
async def test_get_daily_search_count_returns_count(fresh_db):
    await fresh_db.upsert_user(202, "countuser", "Count User")
    count_before = await fresh_db.get_daily_search_count(202)
    assert count_before == 0
    await fresh_db.save_search(202, "phone", "555-1234", "{}", 1.0, 0.5)
    await fresh_db.save_search(202, "address", "123 Main St", "{}", 2.0, 1.0)
    count_after = await fresh_db.get_daily_search_count(202)
    assert count_after == 2


# ── Searches history ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_search_creates_row(fresh_db):
    await fresh_db.upsert_user(300, "searchuser", "Search User")
    await fresh_db.save_search(
        user_id=300,
        search_type="phone",
        query="555-9999",
        result_json='{"found":true}',
        cost_user=1.5,
        cost_sb=0.75,
    )
    searches = await fresh_db.get_user_searches(300)
    assert len(searches) == 1
    assert searches[0]["search_type"] == "phone"
    assert searches[0]["query"] == "555-9999"


@pytest.mark.asyncio
async def test_get_user_searches_returns_list(fresh_db):
    await fresh_db.upsert_user(301, "histuser", "Hist User")
    await fresh_db.save_search(301, "phone", "q1", "{}", 1.0, 0.5)
    await fresh_db.save_search(301, "address", "q2", "{}", 2.0, 1.0)
    searches = await fresh_db.get_user_searches(301)
    assert isinstance(searches, list)
    assert len(searches) == 2


# ── Stats ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_stats_returns_dict(fresh_db):
    await fresh_db.upsert_user(400, "statsuser", "Stats User")
    await fresh_db.save_search(400, "phone", "test", "{}", 1.0, 0.5)
    stats = await fresh_db.get_stats()
    assert isinstance(stats, dict)
    # Verify all expected keys are present
    required_keys = [
        "users", "total_balance", "searches", "total_deposits",
        "total_revenue", "profit", "sb_active", "sb_total",
        "uf_active", "uf_total", "today_searches",
        "active_users_today",
    ]
    for key in required_keys:
        assert key in stats, f"Missing key: {key}"


# ── Cache ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_get_cache_roundtrip_within_ttl(fresh_db):
    await fresh_db.set_cache("key1", {"result": "data"}, ttl_hours=24)
    result = await fresh_db.get_cached("key1")
    assert result is not None
    assert result["result"] == "data"


@pytest.mark.asyncio
async def test_get_cache_returns_none_when_expired(fresh_db):
    # TTL=0 means already expired (expires_at = now + 0 hours)
    await fresh_db.set_cache("expired_key", {"old": True}, ttl_hours=0)
    result = await fresh_db.get_cached("expired_key")
    assert result is None


@pytest.mark.asyncio
async def test_get_cache_returns_none_for_unknown_key(fresh_db):
    result = await fresh_db.get_cached("totally_unknown_key_xyz")
    assert result is None


# ── Subscriptions ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_subscription_creates_row(fresh_db):
    await fresh_db.upsert_user(500, "subuser", "Sub User")
    # plan 1 = Basic, seeded by init_db
    sub_id = await fresh_db.create_subscription(500, plan_id=1)
    assert sub_id > 0
    sub = await fresh_db.get_subscription(500)
    assert sub is not None
    assert sub["user_id"] == 500
    assert sub["plan_id"] == 1
    assert sub["status"] == "active"


@pytest.mark.asyncio
async def test_get_subscription_returns_plan_info(fresh_db):
    await fresh_db.upsert_user(501, "planuser", "Plan User")
    await fresh_db.create_subscription(501, plan_id=2)  # Pro plan
    sub = await fresh_db.get_subscription(501)
    assert sub is not None
    assert sub["plan_name"] == "Pro"
    assert sub["tier"] == "pro"


@pytest.mark.asyncio
async def test_check_subscription_limit_within_limit(fresh_db):
    await fresh_db.upsert_user(502, "limituser2", "Limit User 2")
    allowed, remaining, limit = await fresh_db.check_subscription_limit(502)
    assert allowed is True
    assert remaining >= 0
    assert limit > 0


@pytest.mark.asyncio
async def test_increment_subscription_usage_increases_count(fresh_db):
    await fresh_db.upsert_user(503, "incsub", "Inc Sub")
    await fresh_db.create_subscription(503, plan_id=1)
    sub_before = await fresh_db.get_subscription(503)
    before = sub_before["searches_today"]
    await fresh_db.increment_subscription_usage(503)
    sub_after = await fresh_db.get_subscription(503)
    assert sub_after["searches_today"] == before + 1
