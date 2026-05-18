"""
Complete pytest tests for api.py — SBBot v3 REST API.
Covers health, auth, limits, prices, tiers, job polling, search validation, and validators.

Uses httpx.AsyncClient with ASGITransport (starlette testclient is incompatible
with httpx 0.28 — it passes `app=` kwarg which that version rejects).
"""
import pytest
import pytest_asyncio
import sys
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

_core = Path(__file__).parent
if str(_core) not in sys.path:
    sys.path.insert(0, str(_core))

import httpx
import api as _api_module
app = _api_module.app

# ASGI transport (shared across all async clients)
_asgi_transport = httpx.ASGITransport(app=app)
_base_url = "http://test"


# ── Async HTTP client factory ──────────────────────────────────────────────────

@pytest_asyncio.fixture
async def http_client():
    """Async httpx client wired to the FastAPI app."""
    async with httpx.AsyncClient(transport=_asgi_transport, base_url=_base_url) as client:
        yield client


# ── Helper to run patched async HTTP calls ────────────────────────────────────

def _run(coro):
    """Run an async coroutine in a fresh event loop (for non-async tests)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── 1. Health endpoint ───────────────────────────────────────────────────────

class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, http_client):
        resp = await http_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "3.0"


# ── 2-4. Auth: missing / invalid / rate limited ─────────────────────────────

class TestAuthMissingKey:
    """All auth-protected endpoints reject requests without X-API-Key."""

    @pytest.mark.asyncio
    async def test_prices_without_api_key(self, http_client):
        resp = await http_client.get("/v1/prices")
        # FastAPI returns 422 for missing required Header
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_limits_without_api_key(self, http_client):
        resp = await http_client.get("/v1/limits")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_tiers_without_api_key(self, http_client):
        resp = await http_client.get("/v1/tiers")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_search_without_api_key(self, http_client):
        resp = await http_client.post("/v1/search", json={"type": "phone", "query": "5551234"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_job_without_api_key(self, http_client):
        resp = await http_client.get("/v1/jobs/some-uuid")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_batch_without_api_key(self, http_client):
        resp = await http_client.post("/v1/search/batch",
                                      json={"type": "phone", "queries": ["5551234"]})
        assert resp.status_code == 422


class TestAuthInvalidKey:
    """Auth returns 401 when the key is not found in the DB."""

    @pytest.mark.asyncio
    async def test_prices_invalid_key(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m:
            m.return_value = None
            resp = await http_client.get("/v1/prices", headers={"X-API-Key": "bad-key"})
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_limits_invalid_key(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m:
            m.return_value = None
            resp = await http_client.get("/v1/limits", headers={"X-API-Key": "bad-key"})
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_search_invalid_key(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m:
            m.return_value = None
            resp = await http_client.post("/v1/search",
                                        json={"type": "phone", "query": "5551234"},
                                        headers={"X-API-Key": "bad-key"})
            assert resp.status_code == 401


class TestAuthRateLimit:
    """Auth returns 429 when rate limit check fails."""

    @pytest.mark.asyncio
    async def test_prices_rate_limited(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate:
            m_key.return_value = {"id": 1, "tier": "starter", "api_key": "x", "daily_limit": 100}
            m_rate.return_value = (False, 0, 10)
            resp = await http_client.get("/v1/prices", headers={"X-API-Key": "x"})
            assert resp.status_code == 429

    @pytest.mark.asyncio
    async def test_limits_rate_limited(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate:
            m_key.return_value = {"id": 1, "tier": "starter", "api_key": "x", "daily_limit": 100}
            m_rate.return_value = (False, 0, 10)
            resp = await http_client.get("/v1/limits", headers={"X-API-Key": "x"})
            assert resp.status_code == 429


# ── 5. Limits endpoint ───────────────────────────────────────────────────────

class TestLimitsEndpoint:
    @pytest.mark.asyncio
    async def test_limits_returns_correct_fields(self, http_client):
        pro_key = {
            "id": 2, "user_id": 99, "api_key": "pro-key",
            "tier": "pro", "daily_limit": 500,
            "searches_today": 42, "total_requests": 100,
        }
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate:
            m_key.return_value = pro_key
            m_rate.return_value = (True, 458, 30)
            resp = await http_client.get("/v1/limits", headers={"X-API-Key": "pro-key"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["tier"] == "pro"
            assert data["daily_limit"] == 500
            assert data["remaining_today"] == 458
            assert data["rate_limit_per_min"] == 30
            assert data["total_requests"] == 100
            assert data["searches_today"] == 42


# ── 6. Prices endpoint ───────────────────────────────────────────────────────

class TestPricesEndpoint:
    @pytest.mark.asyncio
    async def test_prices_includes_all_12_types(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate:
            m_key.return_value = {"id": 1, "tier": "starter", "api_key": "x", "daily_limit": 100}
            m_rate.return_value = (True, 99, 10)
            resp = await http_client.get("/v1/prices", headers={"X-API-Key": "x"})
            assert resp.status_code == 200
            data = resp.json()
            prices = data["prices"]
            expected = {
                "phone", "address", "background", "phone_identify",
                "phone_verify", "address_verify", "email_verify", "emailrep",
                "ssn_dob", "driver_license", "credit_report", "credit_score",
            }
            assert set(prices.keys()) == expected


# ── 7. Tiers endpoint ───────────────────────────────────────────────────────

class TestTiersEndpoint:
    @pytest.mark.asyncio
    async def test_tiers_includes_required_tiers(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate, \
             patch.object(_api_module.db, 'get_api_tier_settings', new_callable=AsyncMock) as m_tier:
            m_key.return_value = {"id": 1, "tier": "starter", "api_key": "x", "daily_limit": 100}
            m_rate.return_value = (True, 99, 10)
            m_tier.side_effect = lambda t: {"cost": 0, "daily": 100, "rate": 10}
            resp = await http_client.get("/v1/tiers", headers={"X-API-Key": "x"})
            assert resp.status_code == 200
            data = resp.json()
            for tier in ("starter", "pro", "enterprise", "unlimited"):
                assert tier in data
                assert "cost_monthly" in data[tier]
                assert "daily_limit" in data[tier]
                assert "rate_limit_per_min" in data[tier]


# ── 8-10. Job polling ───────────────────────────────────────────────────────

class TestJobPolling:
    @pytest.mark.asyncio
    async def test_job_pending(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate:
            m_key.return_value = {"id": 1, "tier": "starter", "api_key": "x", "daily_limit": 100}
            m_rate.return_value = (True, 99, 10)

            mock_result = MagicMock()
            mock_result.state = "PENDING"
            with patch.object(_api_module, 'AsyncResult', return_value=mock_result):
                resp = await http_client.get("/v1/jobs/uuid-abc123", headers={"X-API-Key": "x"})
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "pending"
                assert data["job_id"] == "uuid-abc123"

    @pytest.mark.asyncio
    async def test_job_success(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate:
            m_key.return_value = {"id": 1, "tier": "starter", "api_key": "x", "daily_limit": 100}
            m_rate.return_value = (True, 99, 10)

            mock_result = MagicMock()
            mock_result.state = "SUCCESS"
            mock_result.result = {"ok": True, "data": {"foo": "bar"}}
            with patch.object(_api_module, 'AsyncResult', return_value=mock_result):
                resp = await http_client.get("/v1/jobs/uuid-success", headers={"X-API-Key": "x"})
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "success"
                assert data["result"]["ok"] is True

    @pytest.mark.asyncio
    async def test_job_failure(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate:
            m_key.return_value = {"id": 1, "tier": "starter", "api_key": "x", "daily_limit": 100}
            m_rate.return_value = (True, 99, 10)

            mock_result = MagicMock()
            mock_result.state = "FAILURE"
            mock_result.info = Exception("timeout")
            with patch.object(_api_module, 'AsyncResult', return_value=mock_result):
                resp = await http_client.get("/v1/jobs/uuid-failure", headers={"X-API-Key": "x"})
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "failure"
                assert "timeout" in data["error"]


# ── 11. Search type validation — unknown type ─────────────────────────────────

class TestSearchTypeValidation:
    @pytest.mark.asyncio
    async def test_unknown_search_type(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate:
            m_key.return_value = {"id": 1, "tier": "starter", "api_key": "x", "daily_limit": 100}
            m_rate.return_value = (True, 99, 10)
            resp = await http_client.post("/v1/search",
                                         json={"type": "unknown_type", "query": "something"},
                                         headers={"X-API-Key": "x"})
            assert resp.status_code == 400
            assert "Unknown search type" in resp.json()["detail"]


# ── 12-13. validate_phone ────────────────────────────────────────────────────

class TestValidatePhone:
    @pytest.mark.parametrize("raw,expected", [
        ("+1 555 123 4567", "15551234567"),
        ("555-1234", "5551234"),
        ("(555) 123-4567", "5551234567"),
        ("+44 20 7946 0958", "442079460958"),
    ])
    def test_valid_phone(self, raw, expected):
        result = _api_module.validate_phone(raw)
        assert result == expected

    def test_phone_too_short(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_phone("123456")
        assert "7 digits" in str(exc_info.value.detail)

    def test_phone_too_long(self):
        long_phone = "1" * 20
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_phone(long_phone)
        assert "15 digits" in str(exc_info.value.detail)

    def test_phone_empty_required(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_phone("")
        assert "required field is empty" in str(exc_info.value.detail)


# ── 14-15. validate_name ──────────────────────────────────────────────────────

class TestValidateName:
    @pytest.mark.parametrize("name", [
        "John",
        "Mary Jane",
        "O'Connor",
        "Smith-Jones",
        "Jo",
    ])
    def test_valid_name(self, name):
        result = _api_module.validate_name(name, "test_field")
        assert len(result) >= 2

    def test_name_empty_required(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_name("", "test_field", required=True)
        assert "required field is empty" in str(exc_info.value.detail)

    def test_name_too_short(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_name("J", "test_field")
        assert "at least 2 characters" in str(exc_info.value.detail)

    def test_name_too_long(self):
        long_name = "A" * 51
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_name(long_name, "test_field")
        assert "at most 50 characters" in str(exc_info.value.detail)

    def test_name_invalid_chars(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_name("John123!", "test_field")
        assert "invalid characters" in str(exc_info.value.detail)


# ── 16-17. validate_state ────────────────────────────────────────────────────

class TestValidateState:
    def test_state_valid_uppercase(self):
        assert _api_module.validate_state("CA") == "CA"
        assert _api_module.validate_state("NY") == "NY"

    def test_state_auto_uppercase(self):
        assert _api_module.validate_state("ca") == "CA"
        assert _api_module.validate_state("Tx") == "TX"

    def test_state_empty_allowed(self):
        assert _api_module.validate_state("") == ""
        assert _api_module.validate_state(None) == ""

    def test_state_invalid_non_2_letter(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_state("California")
        assert "2-letter US state code" in str(exc_info.value.detail)

    def test_state_invalid_1_letter(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_state("X")
        assert "2-letter US state code" in str(exc_info.value.detail)


# ── 18-19. validate_dob ──────────────────────────────────────────────────────

class TestValidateDob:
    @pytest.mark.parametrize("dob", [
        "01.15.1985",
        "01/15/1985",
        "1985-01-15",
        "1985/01/15",
    ])
    def test_valid_dob_formats(self, dob):
        result = _api_module.validate_dob(dob)
        assert result == dob

    def test_dob_empty_allowed(self):
        assert _api_module.validate_dob("") == ""

    def test_dob_wrong_format(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_dob("15-01-1985")
        assert "invalid format" in str(exc_info.value.detail)

    def test_dob_year_too_old(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_dob("01.01.1800")
        assert "year must be 1900-2010" in str(exc_info.value.detail)

    def test_dob_year_too_recent(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_dob("01.01.2020")
        assert "year must be 1900-2010" in str(exc_info.value.detail)


# ── 20-21. validate_ssn ──────────────────────────────────────────────────────

class TestValidateSsn:
    def test_valid_ssn_full(self):
        result = _api_module.validate_ssn("123-45-6789")
        assert result == "123-45-6789"

    def test_valid_ssn_last4(self):
        result = _api_module.validate_ssn("6789")
        assert result == "6789"

    def test_valid_ssn_last4_with_dashes(self):
        result = _api_module.validate_ssn("67-89")
        assert result == "6789"

    def test_ssn_empty_allowed(self):
        assert _api_module.validate_ssn("") == ""

    def test_ssn_wrong_digit_count(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_ssn("1234567")
        assert "must be 9 digits" in str(exc_info.value.detail)

    def test_ssn_full_without_dashes(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_ssn("123456789")
        assert "XXX-XX-XXXX with dashes" in str(exc_info.value.detail)


# ── 22-23. validate_email ────────────────────────────────────────────────────

class TestValidateEmail:
    def test_valid_email(self):
        result = _api_module.validate_email("john.doe@example.com")
        assert result == "john.doe@example.com"

    def test_valid_email_uppercase_normalized(self):
        result = _api_module.validate_email("John@EXAMPLE.COM")
        assert result == "john@example.com"

    def test_email_empty_required(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_email("", required=True)
        assert "required field is empty" in str(exc_info.value.detail)

    def test_email_no_at_symbol(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_email("notanemail.com")
        assert "invalid format" in str(exc_info.value.detail)

    def test_email_too_long(self):
        local = "a" * 65
        long_email = f"{local}@example.com"
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_email(long_email)
        assert "local part too long" in str(exc_info.value.detail)


# ── 24-25. validate_zip ──────────────────────────────────────────────────────

class TestValidateZip:
    def test_valid_zip_5_digits(self):
        assert _api_module.validate_zip("90210") == "90210"

    def test_valid_zip_9_digits(self):
        assert _api_module.validate_zip("90210-1234") == "902101234"

    def test_zip_empty_allowed(self):
        assert _api_module.validate_zip("") == ""

    def test_zip_wrong_length(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_zip("1234")
        assert "must be 5 or 9 digits" in str(exc_info.value.detail)

    def test_zip_7_digits_rejected(self):
        with pytest.raises(_api_module.ValidationError) as exc_info:
            _api_module.validate_zip("1234567")
        assert "must be 5 or 9 digits" in str(exc_info.value.detail)


# ── 26-27. Batch search limits ────────────────────────────────────────────────

class TestBatchSearchLimits:
    @pytest.mark.asyncio
    async def test_batch_max_20(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate:
            m_key.return_value = {"id": 1, "tier": "starter", "api_key": "x", "daily_limit": 100}
            m_rate.return_value = (True, 500, 10)
            queries = [{"query": f"555{str(i).zfill(4)}"} for i in range(21)]
            resp = await http_client.post("/v1/search/batch",
                                         json={"type": "phone", "queries": queries},
                                         headers={"X-API-Key": "x"})
            assert resp.status_code == 400
            assert "maximum 20 items" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_batch_empty_queries(self, http_client):
        with patch.object(_api_module.db, 'get_api_key_by_key', new_callable=AsyncMock) as m_key, \
             patch.object(_api_module.db, 'check_api_rate_limit', new_callable=AsyncMock) as m_rate:
            m_key.return_value = {"id": 1, "tier": "starter", "api_key": "x", "daily_limit": 100}
            m_rate.return_value = (True, 500, 10)
            resp = await http_client.post("/v1/search/batch",
                                         json={"type": "phone", "queries": []},
                                         headers={"X-API-Key": "x"})
            assert resp.status_code == 400
            assert "at least 1 item" in resp.json()["detail"]