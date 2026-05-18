"""
Tests for usfull_engine.py
Validates: account health scoring, circuit breaker, search methods, cache, price calculations.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

_core_dir = Path(__file__).parent
if str(_core_dir) not in sys.path:
    sys.path.insert(0, str(_core_dir))

from usfull_engine import (
    UsfullEngine, UsfullAccount,
    _normalize_dob, _normalize_dob_dl,
    HealthScore, CircuitBreaker,
)


# ── DOB normalization ──────────────────────────────────────────────────────────

class TestDobNormalization:
    @pytest.mark.parametrize("input_dob,expected", [
        ("19850115", "19850115"),
        ("1985", "1985"),
        ("01/15/1985", "19850115"),
        ("1/5/1985", "19850105"),
        ("1985-01-15", "19850115"),
        ("15.01.1985", "19851501"),
        ("", ""),
        ("  ", ""),
    ])
    def test_normalize_dob(self, input_dob, expected):
        assert _normalize_dob(input_dob) == expected

    @pytest.mark.parametrize("input_dob,expected", [
        ("01/15/1985", "01/15/1985"),
        ("15.01.1985", "15.01.1985"),
        ("1985-01-15", "1985-01-15"),
        ("19850115", "19850115"),
        ("1.5.1985", "1.5.1985"),
        ("1/5/1985", "1/5/1985"),
        ("", ""),
    ])
    def test_normalize_dob_dl(self, input_dob, expected):
        assert _normalize_dob_dl(input_dob) == expected


# ── HealthScore ───────────────────────────────────────────────────────────────

class TestHealthScore:
    def test_new_account_has_full_health(self):
        hs = HealthScore()
        assert hs.score() == 100.0

    def test_single_ok_record(self):
        hs = HealthScore()
        hs.record_ok()
        # error_window=[False], n=1, errors=0, error_rate=0
        # error_score=(1-0)*50=50, latency_score=30, ok_bonus=min(10,0.5)=0.5, error_penalty=0
        # total=80.5
        assert hs.score() == 80.5

    def test_single_error_record(self):
        hs = HealthScore()
        hs.record_error()
        # error_window=[True], n=1, errors=1, error_rate=1.0
        # error_score=0, latency_score=30, ok_bonus=0, error_penalty=1
        # total=29
        assert hs.score() == 29.0

    def test_health_resets(self):
        hs = HealthScore()
        hs.record_error()
        hs.record_error()
        hs.reset()
        assert hs.score() == 100.0
        assert hs._error_window == []

    def test_circuit_breaker_default_closed(self):
        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.allow_request() is True

    def test_circuit_breaker_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.allow_request() is False

    def test_circuit_breaker_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.0)
        for _ in range(2):
            cb.record_failure()
        # With recovery_timeout=0, accessing .state transitions to half_open
        assert cb.state == "half_open"
        assert cb.allow_request() is True

    def test_circuit_breaker_success_in_half_open_closes(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.0, half_open_max=2)
        for _ in range(2):
            cb.record_failure()
        cb._state = "half_open"
        cb.record_success()
        cb.record_success()
        assert cb.state == "closed"


# ── UsfullAccount ─────────────────────────────────────────────────────────────

class TestUsfullAccount:
    def test_default_status_is_active(self):
        acc = UsfullAccount("user", "pass", "key")
        assert acc.username == "user"
        assert acc.status == "active"
        assert acc.balance == 0.0
        assert isinstance(acc.health, HealthScore)

    def test_balance_pct_no_initial_balance(self):
        acc = UsfullAccount("u", "p", "k", balance=50.0)
        assert acc.balance_pct == 100.0

    def test_is_usable_true_for_active_with_balance(self):
        acc = UsfullAccount("u", "p", "k", status="active", balance=10.0)
        assert acc.is_usable is True

    def test_is_usable_false_for_no_balance(self):
        acc = UsfullAccount("u", "p", "k", status="active", balance=0.0)
        assert acc.is_usable is False

    def test_is_usable_false_for_blocked_status(self):
        acc = UsfullAccount("u", "p", "k", status="blocked", balance=100.0)
        assert acc.is_usable is False


# ── UsfullEngine ─────────────────────────────────────────────────────────────

class TestUsfullEngine:
    @pytest.fixture
    def engine(self):
        return UsfullEngine()

    def test_no_accounts_by_default(self, engine):
        assert len(engine.accounts) == 0

    def test_load_accounts(self, engine):
        engine.load_accounts([
            {"username": "a", "password": "p", "api_key": "k1"},
            {"username": "b", "password": "p", "api_key": "k2"},
        ])
        assert len(engine.accounts) == 2
        assert engine.accounts[0].username == "a"
        assert engine.accounts[1].api_key == "k2"

    def test_load_accounts_with_proxy(self, engine):
        engine.load_accounts([
            {"username": "a", "password": "p", "api_key": "k", "proxy": "socks5://h:p@x:1080"},
        ])
        assert engine.accounts[0].proxy == "socks5://h:p@x:1080"

    def test_load_accounts_initial_balance_from_balance(self, engine):
        engine.load_accounts([{"username": "a", "password": "p", "api_key": "k", "balance": 50.0}])
        assert engine.accounts[0].initial_balance == 50.0

    def test_active_count_empty(self, engine):
        assert engine.active_count() == 0

    def test_active_count_filters_excluded(self, engine):
        engine.load_accounts([
            {"username": "a", "password": "p", "api_key": "k", "status": "active"},
            {"username": "b", "password": "p", "api_key": "k", "status": "no_balance"},
            {"username": "c", "password": "p", "api_key": "k", "status": "blocked"},
        ])
        assert engine.active_count() == 1

    def test_clear_cache(self, engine):
        engine._cache["test:key"] = {"ok": True}
        engine.clear_cache()
        assert len(engine._cache) == 0

    def test_prices_from_module_constant(self, engine):
        from usfull_engine import USFULL_PRICES
        assert USFULL_PRICES["ssn_dob"]["success"] == 0.40
        assert USFULL_PRICES["driver_license"]["success"] == 1.00
        assert USFULL_PRICES["credit_report"]["success"] == 2.50
        assert USFULL_PRICES["credit_score"]["success"] == 2.00
        assert USFULL_PRICES["ssn_dob"]["no_result"] == 0.01
        assert USFULL_PRICES["driver_license"]["no_result"] == 0.00

    def test_markup_calculation_50_percent(self):
        base = 0.40
        assert round(base * (1 + 0.50), 2) == 0.60

    def test_markup_calculation_100_percent(self):
        base = 0.40
        assert round(base * (1 + 1.00), 2) == 0.80

    def test_get_pool_status(self, engine):
        engine.load_accounts([{"username": "a", "password": "p", "api_key": "k"}])
        status = engine.get_pool_status()
        assert len(status) == 2
        assert status[0]["username"] == "a"
        cb_entry = next((s for s in status if "circuit_breaker" in s), None)
        assert cb_entry is not None

    def test_reset_error_rate_clears_state(self, engine):
        engine._cb.record_failure()
        engine._cb.record_failure()
        assert engine._cb.failure_rate > 0
        engine.reset_error_rate()
        assert engine._cb.state == "closed"
        # failure_rate persists (total counts not cleared by reset())


# ── No accounts ────────────────────────────────────────────────────────────────

class TestUsfullEngineNoAccounts:
    @pytest.fixture
    def engine(self):
        return UsfullEngine()

    @pytest.mark.asyncio
    async def test_search_ssn_dob_no_accounts(self, engine):
        result = await engine.search_ssn_dob("John", "Doe", "CA")
        assert result["ok"] is False
        assert "no available usfull accounts" in result["error"]

    @pytest.mark.asyncio
    async def test_search_dl_no_accounts(self, engine):
        result = await engine.search_driver_license("John", "Doe", "123 Main St", "12345", "01/15/1985")
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_search_cr_no_accounts(self, engine):
        result = await engine.search_credit_report("John", "Doe", "123 Main St", "LA", "CA", "90001", "01/15/1985", "123456789")
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_search_cs_no_accounts(self, engine):
        result = await engine.search_credit_score("John", "Doe", "123 Main St", "LA", "CA", "90001", "01/15/1985")
        assert result["ok"] is False


# ── Chain helpers ─────────────────────────────────────────────────────────────

class TestExtractSsnParams:
    def test_extracts_all_fields(self):
        from usfull_engine import extract_ssn_params
        ssn_result = {
            "ok": True,
            "results": [{
                "firstname": "JOHN",
                "lastname": "DOE",
                "dob": "19850115",
                "ssn": "123456789",
                "address": "123 MAIN ST",
                "city": "LOS ANGELES",
                "st": "CA",
                "zip": "90210",
            }]
        }
        params = extract_ssn_params(ssn_result)
        assert params["first_name"] == "JOHN"
        assert params["last_name"] == "DOE"
        assert params["dob"] == "19850115"
        assert params["ssn"] == "123456789"
        assert params["city"] == "LOS ANGELES"
        assert params["state"] == "CA"

    def test_returns_empty_on_failure(self):
        from usfull_engine import extract_ssn_params
        assert extract_ssn_params({"ok": False}) == {}
        assert extract_ssn_params({}) == {}
        assert extract_ssn_params({"ok": True, "results": []}) == {}


class TestExtractPersonForSsf:
    def test_basic(self):
        from usfull_engine import extract_person_for_ssf
        params = extract_person_for_ssf({"name": "John Doe", "location": "Los Angeles, CA"})
        assert params["first_name"] == "John"
        assert params["last_name"] == "Doe"
        assert params["state"] == "CA"

    def test_single_name(self):
        from usfull_engine import extract_person_for_ssf
        params = extract_person_for_ssf({"name": "John"})
        assert params["first_name"] == "John"
        assert params["last_name"] == ""

    def test_location_parsing(self):
        from usfull_engine import extract_person_for_ssf
        params = extract_person_for_ssf({"name": "A B", "location": "New York, NY"})
        assert params["state"] == "NY"


class TestExtractPersonForDl:
    def test_basic(self):
        from usfull_engine import extract_person_for_dl
        params = extract_person_for_dl({"name": "John Doe", "address": "123 Main St, City, ST 90210"})
        assert params["first_name"] == "John"
        assert params["last_name"] == "Doe"
        assert params["address"] == "123 Main St"

    def test_uses_location_fallback(self):
        from usfull_engine import extract_person_for_dl
        params = extract_person_for_dl({"name": "John Doe", "location": "City, ST 12345"})
        assert params["first_name"] == "John"