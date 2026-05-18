"""Tests for celery_worker.py — helpers and task logic."""
import pytest, sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

_core = Path(__file__).parent
if str(_core) not in sys.path:
    sys.path.insert(0, str(_core))

# Import helpers directly — no celery app (connects to Redis)
from celery_worker import (
    _digits, _phone, _name, _state, _dob, _ssn, _email, _addr,
    TASK_MAP,
)


# ── 1. _digits ──────────────────────────────────────────────────────────

class TestDigits:
    def test_strips_nondigits(self):
        assert _digits("+1 (555) 123-4567") == "15551234567"

    def test_empty_string(self):
        assert _digits("") == ""
        assert _digits(None) == ""

    def test_passthrough_digits(self):
        assert _digits("12345") == "12345"


# ── 2. _phone valid ─────────────────────────────────────────────────────

class TestPhoneValid:
    @pytest.mark.parametrize("input_val,expected", [
        ("15551234567", "15551234567"),
        ("+1-555-123-4567", "15551234567"),
        ("5551234567", "5551234567"),
        ("+44 20 7946 0958", "442079460958"),
    ])
    def test_phone_valid(self, input_val, expected):
        assert _phone(input_val) == expected


# ── 3. _phone invalid ────────────────────────────────────────────────────

class TestPhoneInvalid:
    def test_too_short(self):
        with pytest.raises(ValueError, match=r"phone must have 7-15 digits"):
            _phone("123456")

    def test_too_long(self):
        with pytest.raises(ValueError, match=r"phone must have 7-15 digits"):
            _phone("1" * 16)

    def test_empty(self):
        with pytest.raises(ValueError, match=r"phone must have 7-15 digits"):
            _phone("")

    def test_non_digits_only(self):
        with pytest.raises(ValueError, match=r"phone must have 7-15 digits"):
            _phone("abcdefg")


# ── 4. _name valid ──────────────────────────────────────────────────────

class TestNameValid:
    def test_normal_name(self):
        assert _name("John", "first_name") == "John"
        assert _name("  Jane  ", "last_name") == "Jane"
        assert _name("Mary-Jane", "middle_name") == "Mary-Jane"


# ── 5. _name invalid ────────────────────────────────────────────────────

class TestNameInvalid:
    def test_too_short(self):
        with pytest.raises(ValueError, match=r"at least 2 chars"):
            _name("J", "first_name")

    def test_empty_required(self):
        with pytest.raises(ValueError, match=r"at least 2 chars"):
            _name("", "first_name")

    def test_too_long(self):
        with pytest.raises(ValueError, match=r"max 50 chars"):
            _name("A" * 51, "first_name")

    def test_none_value(self):
        with pytest.raises(ValueError, match=r"at least 2 chars"):
            _name(None, "first_name")


# ── 6. _state ───────────────────────────────────────────────────────────

class TestState:
    def test_uppercase_unchanged(self):
        assert _state("CA") == "CA"

    def test_lowercase_normalized(self):
        assert _state("ca") == "CA"
        assert _state("tx") == "TX"

    def test_strips_whitespace(self):
        assert _state(" ny ") == "NY"

    def test_empty(self):
        assert _state("") == ""
        assert _state(None) == ""


# ── 7. _dob valid ──────────────────────────────────────────────────────

class TestDobValid:
    @pytest.mark.parametrize("input_val,expected", [
        ("01.15.1985", "01.15.1985"),
        ("1985-01-15", "1985-01-15"),
        ("01/15/1985", "01/15/1985"),
        ("1985/01/15", "1985/01/15"),
    ])
    def test_dob_valid(self, input_val, expected):
        assert _dob(input_val) == expected


# ── 8. _dob invalid ────────────────────────────────────────────────────

class TestDobInvalid:
    def test_bad_format(self):
        with pytest.raises(ValueError, match=r"bad dob format"):
            _dob("1985/1/5")

    def test_empty(self):
        with pytest.raises(ValueError, match=r"bad dob format"):
            _dob("")

    def test_none(self):
        with pytest.raises(ValueError, match=r"bad dob format"):
            _dob(None)


# ── 9. _ssn valid ─────────────────────────────────────────────────────

class TestSsnValid:
    def test_full_ssn(self):
        assert _ssn("123-45-6789") == "123-45-6789"
        assert _ssn("  123-45-6789  ") == "123-45-6789"

    def test_last4(self):
        assert _ssn("6789") == "6789"


# ── 10. _ssn invalid ───────────────────────────────────────────────────

class TestSsnInvalid:
    def test_wrong_length(self):
        with pytest.raises(ValueError, match=r"ssn must be 9 or 4 digits"):
            _ssn("12345678")

    def test_empty(self):
        with pytest.raises(ValueError, match=r"ssn must be 9 or 4 digits"):
            _ssn("")


# ── 11. _email ─────────────────────────────────────────────────────────

class TestEmail:
    def test_valid_email(self):
        assert _email("Test@Example.COM") == "test@example.com"

    def test_no_at_sign(self):
        with pytest.raises(ValueError, match=r"bad email"):
            _email("notanemail")

    def test_empty(self):
        with pytest.raises(ValueError, match=r"bad email"):
            _email("")


# ── 12. _addr ──────────────────────────────────────────────────────────

class TestAddr:
    def test_valid_address(self):
        assert _addr("123 Main Street") == "123 Main Street"

    def test_too_short(self):
        with pytest.raises(ValueError, match=r"addr min 5 chars"):
            _addr("1234")

    def test_empty(self):
        with pytest.raises(ValueError, match=r"addr min 5 chars"):
            _addr("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match=r"addr min 5 chars"):
            _addr("     ")


# ── 13. TASK_MAP completeness ───────────────────────────────────────────

class TestTaskMap:
    def test_all_12_search_types_present(self):
        expected = {
            "phone", "phone_identify", "phone_verify",
            "address", "address_verify", "background",
            "email_verify", "emailrep",
            "ssn_dob", "driver_license", "credit_report", "credit_score",
        }
        assert set(TASK_MAP.keys()) == expected


# ── 14. task_phone mocked ───────────────────────────────────────────────

class TestTaskPhone:
    def test_task_phone_mocked(self):
        from celery_worker import task_phone

        mock_r = MagicMock()
        mock_r.ok = True
        mock_r.to_dict.return_value = {"people": []}

        with patch("celery_worker._run_async") as mock_run:
            mock_run.return_value = mock_r

            result = task_phone(1, "15551234567", {})

        assert result == {"ok": True, "data": {"people": []}}
        # task_phone calls _run_async twice: search + increment_api_usage
        assert mock_run.call_count == 2
        # First call is search coroutine
        first_call_args = str(mock_run.call_args_list[0][0][0])
        assert "search" in first_call_args or "phone" in first_call_args


# ── 15. task_address mocked ─────────────────────────────────────────────

class TestTaskAddress:
    def test_task_address_mocked(self):
        from celery_worker import task_address

        mock_r = MagicMock()
        mock_r.ok = True
        mock_r.to_dict.return_value = {"addresses": []}

        with patch("celery_worker._run_async") as mock_run:
            mock_run.return_value = mock_r

            result = task_address(
                1,
                "",
                {"first_name": "John", "last_name": "Doe",
                 "state": "CA", "address": "123 Main St"},
            )

        assert result == {"ok": True, "data": {"addresses": []}}
        # task_address calls _run_async twice: search + increment_api_usage
        assert mock_run.call_count == 2
        # First call is search coroutine
        first_call_args = str(mock_run.call_args_list[0][0][0])
        assert "search" in first_call_args or "address" in first_call_args


# ── 16. task_emailrep mocked ────────────────────────────────────────────

class TestTaskEmailrep:
    def test_task_emailrep_mocked(self):
        from celery_worker import task_emailrep

        mock_r = {"reputation": "high"}

        with patch("celery_worker._run_async") as mock_run:
            mock_run.return_value = mock_r

            result = task_emailrep(1, "test@example.com", {})

        assert result["ok"] is True
        assert result["data"] == {"reputation": "high"}