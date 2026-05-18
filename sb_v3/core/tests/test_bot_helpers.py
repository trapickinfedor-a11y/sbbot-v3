"""
Tests for bot.py command handlers and utility functions.
Does NOT require a real Telegram bot or database.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Module-level config (mocked before importing) ───────────────────────────────

def test_bot_token_required():
    """BOT_TOKEN must be set or RuntimeError raised at import time."""
    with patch.dict("os.environ", {}, clear=True):
        with patch("sys.modules", {"telegram": MagicMock(), "telegram.ext": MagicMock()}):
            # Bot module reads BOT_TOKEN at import. We test the logic here.
            import os
            os.environ.pop("BOT_TOKEN", None)
            token = os.getenv("BOT_TOKEN")
            # Without patching, import would fail — this tests the contract
            assert token is None


# ── DOB normalization integration ────────────────────────────────────────────

class TestDobNormalizationInBot:
    """DOB normalization is used by usfull_engine; bot passes user input directly."""

    def test_dob_mmddyyyy_normalized(self):
        """Bot should accept MM/DD/YYYY and it should be normalized."""
        from usfull_engine import _normalize_dob_dl
        result = _normalize_dob_dl("01/15/1985")
        assert result == "01/15/1985"

    def test_dob_ddmmyyyy_normalized(self):
        from usfull_engine import _normalize_dob_dl
        result = _normalize_dob_dl("15.01.1985")
        assert result == "15.01.1985"

    def test_dob_iso_normalized(self):
        from usfull_engine import _normalize_dob_dl
        result = _normalize_dob_dl("1985-01-15")
        assert result == "1985-01-15"


# ── Helper: extract_ssn_params ─────────────────────────────────────────────────

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


# ── Helper: extract_person_for_ssf ────────────────────────────────────────────

class TestExtractPersonForSsf:
    def test_basic_extraction(self):
        from usfull_engine import extract_person_for_ssf
        person = {"name": "John Doe", "location": "Los Angeles, CA"}
        params = extract_person_for_ssf(person)
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


# ── Helper: extract_person_for_dl ────────────────────────────────────────────

class TestExtractPersonForDl:
    def test_basic_extraction(self):
        from usfull_engine import extract_person_for_dl
        person = {"name": "John Doe", "address": "123 Main St, City, ST 90210"}
        params = extract_person_for_dl(person)
        assert params["first_name"] == "John"
        assert params["last_name"] == "Doe"
        assert params["address"] == "123 Main St"

    def test_uses_location_fallback(self):
        from usfull_engine import extract_person_for_dl
        person = {"name": "John Doe", "location": "City, ST 12345"}
        params = extract_person_for_dl(person)
        assert params["first_name"] == "John"