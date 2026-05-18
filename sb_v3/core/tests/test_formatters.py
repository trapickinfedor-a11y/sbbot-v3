"""
test_formatters.py — Tests for formatters.py and formatter.py
Tests formatting of SBResult objects into Telegram-friendly text.
"""
import pytest
from formatters import (
    fmt_enformion_result,
    fmt_phone_identify,
    fmt_phone_verify,
    fmt_address_verify,
    fmt_email_verify,
)
from formatter import (
    fmt_phone_result, fmt_address_result, fmt_number_address_result,
    fmt_name_result, fmt_email_result,
    fmt_background, fmt_emailrep,
    fmt_batch_summary,
    export_csv, export_txt, export_json,
    _fmt_people,
)
from sb_engine import SBResult


# ─── SBResult helpers ────────────────────────────────────────────────────────

def make_result(
    ok=True,
    search_type="phone",
    people=None,
    parsed=None,
    error="",
):
    return SBResult(
        ok=ok,
        search_type=search_type,
        query={"raw": ""},
        people=people or [],
        parsed=parsed or {},
        error=error,
    )


# ─── fmt_enformion_result ────────────────────────────────────────────────────

class TestFmtEnformionResult:
    def test_error_no_active_accounts(self):
        r = make_result(ok=False, error="NO_ACTIVE_ACCOUNTS")
        out = fmt_enformion_result(r, "320-932-0202")
        assert "Нет активных аккаунтов" in out

    def test_error_session_expired(self):
        r = make_result(ok=False, error="SESSION_EXPIRED")
        out = fmt_enformion_result(r, "320-932-0202")
        assert "Сессия истекла" in out

    def test_error_blocked(self):
        r = make_result(ok=False, error="BLOCKED")
        out = fmt_enformion_result(r, "320-932-0202")
        assert "заблокирован" in out

    def test_error_no_tokens(self):
        r = make_result(ok=False, error="NO_TOKENS")
        out = fmt_enformion_result(r, "320-932-0202")
        assert "токенов" in out

    def test_error_timeout(self):
        r = make_result(ok=False, error="TIMEOUT")
        out = fmt_enformion_result(r, "320-932-0202")
        assert "⏱" in out

    def test_error_unknown(self):
        r = make_result(ok=False, error="SOME_UNKNOWN_ERROR")
        out = fmt_enformion_result(r, "320-932-0202")
        assert "Ошибка" in out

    def test_no_results_found_message(self):
        r = make_result(ok=True, parsed={"message": "No results found"})
        out = fmt_enformion_result(r, "320-932-0202")
        assert "не найден" in out.lower()


    def test_person_with_name(self):
        r = make_result(
            search_type="phone",
            people=[{"name": "John Smith", "age": 35, "phone": "320-932-0202"}],
        )
        out = fmt_enformion_result(r, "320-932-0202")
        assert "John Smith" in out
        assert "35" in out

    def test_person_with_dob_no_age(self):
        r = make_result(
            search_type="phone",
            people=[{"name": "John Smith", "date_of_birth": "01/15/1990"}],
        )
        out = fmt_enformion_result(r, "320-932-0202")
        assert "DOB" in out

    def test_person_with_phones(self):
        r = make_result(
            search_type="phone",
            people=[{
                "name": "John Smith",
                "phones": [
                    {"phone": "320-932-0202", "phoneType": "Mobile", "carrier": "Verizon"}
                ]
            }],
        )
        out = fmt_enformion_result(r, "320-932-0202")
        assert "320-932-0202" in out
        assert "Mobile" in out
        assert "Verizon" in out

    def test_person_with_address(self):
        r = make_result(
            search_type="phone",
            people=[{"name": "John Smith", "address": "123 Main St, New York, NY 10001"}],
        )
        out = fmt_enformion_result(r, "320-932-0202")
        assert "123 Main St" in out

    def test_person_with_emails(self):
        r = make_result(
            search_type="phone",
            people=[{"name": "John Smith", "emails": ["john@example.com", "jsmith@domain.org"]}],
        )
        out = fmt_enformion_result(r, "320-932-0202")
        assert "john@example.com" in out

    def test_person_with_ssn(self):
        r = make_result(
            search_type="phone",
            people=[{"name": "John Smith", "ssn": "123-45-6789"}],
        )
        out = fmt_enformion_result(r, "320-932-0202")
        assert "123-45-6789" in out
        assert "🔢" in out

    def test_person_with_akas(self):
        r = make_result(
            search_type="phone",
            people=[{"name": "John Smith", "akas": ["Johnny Smith", "J. Smith"]}],
        )
        out = fmt_enformion_result(r, "320-932-0202")
        assert "Johnny Smith" in out
        assert "AKA" in out

    def test_person_voip_true(self):
        r = make_result(search_type="phone", people=[{"name": "John Smith", "voip": True}])
        out = fmt_enformion_result(r, "320-932-0202")
        assert "VOIP" in out
        assert "Да" in out

    def test_person_voip_false(self):
        r = make_result(search_type="phone", people=[{"name": "John Smith", "voip": False}])
        out = fmt_enformion_result(r, "320-932-0202")
        assert "VOIP" in out
        assert "Нет" in out

    def test_person_with_relatives(self):
        r = make_result(
            search_type="phone",
            people=[{"name": "John Smith", "relatives": "Jane Smith (Spouse), Bob Smith (Son)"}],
        )
        out = fmt_enformion_result(r, "320-932-0202")
        assert "Jane Smith" in out

    def test_multiple_people(self):
        r = make_result(
            search_type="phone",
            people=[{"name": "John Smith"}, {"name": "Jane Doe"}],
        )
        out = fmt_enformion_result(r, "320-932-0202")
        assert "John Smith" in out
        assert "Jane Doe" in out
        assert "2" in out

    def test_more_than_10_people_indicates_more(self):
        r = make_result(search_type="phone", people=[{"name": f"Person {i}"} for i in range(15)])
        out = fmt_enformion_result(r, "320-932-0202")
        assert "ещё" in out

    def test_parsed_raw_fallback(self):
        r = make_result(ok=True, search_type="phone", parsed={"raw": "Some raw data"})
        out = fmt_enformion_result(r, "320-932-0202")
        assert "Some raw data" in out



# ─── fmt_phone_identify ──────────────────────────────────────────────────────

class TestFmtPhoneIdentify:
    def test_error_no_active_accounts(self):
        r = make_result(ok=False, error="NO_ACTIVE_ACCOUNTS")
        out = fmt_phone_identify(r, "320-932-0202")
        assert "Нет активных аккаунтов" in out

    def test_person_mobile(self):
        r = make_result(
            search_type="phone_identify",
            people=[{
                "name": "John Smith",
                "phones": [{"phone": "320-932-0202", "phoneType": "Mobile", "carrier": "Verizon"}]
            }],
        )
        out = fmt_phone_identify(r, "320-932-0202")
        assert "320-932-0202" in out
        assert "Mobile" in out
        assert "Verizon" in out

    def test_person_landline(self):
        r = make_result(
            search_type="phone_identify",
            people=[{"name": "John Smith", "phones": [{"phone": "320-932-0202", "phoneType": "Landline"}]}],
        )
        out = fmt_phone_identify(r, "320-932-0202")
        assert "Landline" in out

    def test_no_results_found(self):
        r = make_result(ok=True, parsed={"message": "No results found"})
        out = fmt_phone_identify(r, "320-932-0202")
        assert "не идентифицирован" in out or "not found" in out.lower()


# ─── fmt_phone_verify ────────────────────────────────────────────────────────

class TestFmtPhoneVerify:
    def test_error(self):
        r = make_result(ok=False, error="NO_ACTIVE_ACCOUNTS")
        out = fmt_phone_verify(r, "320-932-0202")
        assert "❌" in out

    def test_active_with_names(self):
        r = make_result(
            search_type="phone_verify",
            people=[
                {"name": "John Smith", "phone": "320-932-0202"},
                {"name": "Jane Doe", "phone": "320-932-0202"},
            ],
        )
        out = fmt_phone_verify(r, "320-932-0202")
        assert "АКТИВЕН" in out
        assert "John Smith" in out
        assert "Jane Doe" in out

    def test_active_no_names(self):
        r = make_result(search_type="phone_verify", people=[{"phone": "320-932-0202"}])
        out = fmt_phone_verify(r, "320-932-0202")
        assert "АКТИВЕН" in out

    def test_inactive_no_people(self):
        r = make_result(ok=True, search_type="phone_verify", people=[])
        out = fmt_phone_verify(r, "320-932-0202")
        assert "НЕАКТИВЕН" in out or "не найден" in out


# ─── fmt_address_verify ───────────────────────────────────────────────────────

class TestFmtAddressVerify:
    def test_error(self):
        r = make_result(ok=False, error="BLOCKED")
        out = fmt_address_verify(r, "123 Main St")
        assert "❌" in out

    def test_addresses_found(self):
        r = make_result(
            search_type="address_verify",
            people=[{"name": "John Smith", "addresses": ["123 Main St, NY 10001", "456 Oak Ave, NY 10002"]}],
        )
        out = fmt_address_verify(r, "123 Main St")
        assert "Найдено адресов" in out
        assert "123 Main St" in out

    def test_no_addresses_names_only(self):
        r = make_result(search_type="address_verify", people=[{"name": "John Smith"}])
        out = fmt_address_verify(r, "123 Main St")
        assert "найдено" in out.lower()

    def test_with_dob_and_ssn(self):
        r = make_result(
            search_type="address_verify",
            people=[{"name": "John Smith", "date_of_birth": "01/15/1990", "ssn": "123-45-6789"}],
        )
        out = fmt_address_verify(r, "123 Main St")
        assert "DOB" in out
        assert "SSN" in out

    def test_not_found(self):
        r = make_result(ok=True, search_type="address_verify", people=[])
        out = fmt_address_verify(r, "123 Main St")
        assert "Не найдено" in out


# ─── fmt_email_verify ────────────────────────────────────────────────────────

class TestFmtEmailVerify:
    def test_error(self):
        r = make_result(ok=False, error="NO_ACTIVE_ACCOUNTS")
        out = fmt_email_verify(r, "user@example.com")
        assert "❌" in out

    def test_people_found(self):
        r = make_result(
            search_type="email_verify",
            people=[
                {"name": "John Smith", "age": 35, "phones": [{"phone": "320-932-0202"}]},
                {"name": "Jane Doe", "date_of_birth": "01/15/1990"},
            ],
        )
        out = fmt_email_verify(r, "user@example.com")
        assert "найдено" in out.lower()
        assert "John Smith" in out

    def test_not_found(self):
        r = make_result(ok=True, search_type="email_verify", people=[])
        out = fmt_email_verify(r, "user@example.com")
        assert "Не найдено" in out


# ─── fmt_phone_result / fmt_address_result / etc ─────────────────────────────

class TestFmtPhoneResult:
    def test_phone_result_with_person(self):
        r = make_result(search_type="phone", people=[{"name": "John Smith", "phone": "320-932-0202"}])
        out = fmt_phone_result(r, "320-932-0202")
        assert "📞" in out
        assert "John Smith" in out

    def test_address_result_with_person(self):
        r = make_result(search_type="address", people=[{"name": "John Smith", "address": "123 Main St"}])
        out = fmt_address_result(r, "123 Main St")
        assert "🏠" in out
        assert "123 Main St" in out

    def test_name_result(self):
        r = make_result(search_type="name", people=[{"name": "John Smith"}])
        out = fmt_name_result(r, "John Smith")
        assert "👤" in out

    def test_email_result(self):
        r = make_result(search_type="email", people=[{"name": "John Smith", "email": "john@example.com"}])
        out = fmt_email_result(r, "john@example.com")
        assert "📧" in out

    def test_number_address_result(self):
        r = make_result(search_type="number_address", people=[{"name": "John Smith"}])
        out = fmt_number_address_result(r, "320-932-0202")
        assert "🔢" in out


# ─── fmt_background ───────────────────────────────────────────────────────────

class TestFmtBackground:
    def test_background_result(self):
        r = make_result(search_type="background", people=[{"name": "John Smith", "age": 30}])
        out = fmt_background(r, "John Smith")
        assert "🔍" in out
        assert "John Smith" in out


# ─── fmt_emailrep ─────────────────────────────────────────────────────────────

class TestFmtEmailrep:
    def test_emailrep_with_data(self):
        data = {
            "email": "user@example.com",
            "reputation": "medium",
            "suspicious": False,
            "references": 42,
            "details": {
                "email_provider": "gmail.com",
                "disposable": False,
                "free_provider": True,
                "deliverable": True,
                "spam": False,
                "blacklisted": False,
                "domain_reputation": "neutral",
                "profiles": ["Twitter", "LinkedIn"],
            },
        }
        out = fmt_emailrep(data, "user@example.com")
        assert "user@example.com" in out
        assert "gmail.com" in out
        assert "neutral" in out
        assert "Twitter" in out

    def test_emailrep_error(self):
        data = {"error": "Email not found"}
        out = fmt_emailrep(data, "user@example.com")
        # Error is rendered verbatim from API: "Email not found"
        assert "email not found" in out.lower()

    def test_emailrep_suspicious_true(self):
        data = {"email": "user@example.com", "suspicious": True}
        out = fmt_emailrep(data, "user@example.com")
        assert "⚠️" in out or "ДА" in out

    def test_emailrep_suspicious_false(self):
        data = {"email": "user@example.com", "suspicious": False}
        out = fmt_emailrep(data, "user@example.com")
        assert "✅" in out or "НЕТ" in out

    def test_emailrep_disposable(self):
        data = {"email": "user@example.com", "details": {"disposable": True}}
        out = fmt_emailrep(data, "user@example.com")
        assert "Одноразовый" in out

    def test_emailrep_blacklisted(self):
        data = {"email": "user@example.com", "details": {"blacklisted": True}}
        out = fmt_emailrep(data, "user@example.com")
        assert "чёрном списке" in out


# ─── fmt_batch_summary ────────────────────────────────────────────────────────

class TestFmtBatchSummary:
    def test_batch_summary_all_ok(self):
        # fmt_batch_summary expects dict-like objects with .get(), not SBResult
        results = [
            {"ok": True, "people": [{"name": "John"}]},
            {"ok": True, "people": [{"name": "Jane"}]},
        ]
        out = fmt_batch_summary(results, "phone")
        assert "Обработано: 2/2" in out

    def test_batch_summary_partial(self):
        results = [
            {"ok": True, "people": [{"name": "John"}]},
            {"ok": False, "error": "TIMEOUT"},
        ]
        out = fmt_batch_summary(results, "phone")
        assert "Обработано: 1/2" in out
        assert "Ошибок: 1" in out

    def test_batch_summary_all_errors(self):
        results = [
            {"ok": False, "error": "NO_TOKENS"},
            {"ok": False, "error": "TIMEOUT"},
        ]
        out = fmt_batch_summary(results, "phone")
        assert "Обработано: 0/2" in out
        assert "Ошибок: 2" in out

    def test_batch_summary_address_type(self):
        results = [{"ok": True, "people": [{}]}]
        out = fmt_batch_summary(results, "address")
        assert "Address Lookup" in out


# ─── _fmt_people ─────────────────────────────────────────────────────────────

class TestFmtPeople:
    def test_people_header(self):
        r = make_result(people=[{"name": "John Smith", "age": 30}])
        out = _fmt_people(r, "Test Header\n")
        assert "Test Header" in out
        assert "John Smith" in out
        assert "30" in out

    def test_empty_people(self):
        r = make_result(people=[])
        out = _fmt_people(r, "Test Header\n")
        assert "Test Header" in out


# ─── export functions ─────────────────────────────────────────────────────────

class TestExportFunctions:
    def test_export_csv_with_people(self):
        results = [
            {"ok": True, "people": [{"name": "John Smith", "phone": "320-932-0202"}]},
            {"ok": True, "people": [{"name": "Jane Doe", "phone": "555-123-4567"}]},
        ]
        buf = export_csv(results, "phone")
        content = buf.getvalue().decode("utf-8-sig")
        assert "John Smith" in content
        assert "320-932-0202" in content

    def test_export_csv_with_parsed(self):
        results = [{"ok": True, "parsed": {"name": "John Smith", "phone": "320-932-0202"}}]
        buf = export_csv(results, "phone")
        content = buf.getvalue().decode("utf-8-sig")
        assert "John Smith" in content

    def test_export_csv_no_results(self):
        results = []
        buf = export_csv(results, "phone")
        content = buf.getvalue().decode("utf-8-sig")
        assert "No results" in content

    def test_export_txt(self):
        results = [{"ok": True, "people": [{"name": "John Smith", "phone": "320-932-0202"}]}]
        buf = export_txt(results, "phone")
        content = buf.getvalue().decode("utf-8")
        assert "John Smith" in content
        assert "320-932-0202" in content
        assert "SearchBug Results" in content

    def test_export_json(self):
        results = [{"ok": True, "people": [{"name": "John Smith", "phone": "320-932-0202"}]}]
        buf = export_json(results)
        content = buf.getvalue().decode("utf-8")
        assert "John Smith" in content
        assert "320-932-0202" in content
