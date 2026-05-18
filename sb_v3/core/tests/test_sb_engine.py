"""
Tests for sb_engine.py (Enformion client)
Validates: account parsing, pool selection, response parsing, retry logic.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

_core_dir = Path(__file__).parent
if str(_core_dir) not in sys.path:
    sys.path.insert(0, str(_core_dir))

from sb_engine import (
    EnformionPool, EnformionAccount, SBResult,
    _enf_headers, _galaxy_search_type, _make_connector,
)


# ── FakeResp ──────────────────────────────────────────────────────────────────
# Real response objects needed because aiohttp uses async-with with
# status attribute access that breaks AsyncMock.

class FakeResp:
    def __init__(self, status, text_val, json_val=None):
        self.status = status
        self._text = text_val
        self._json = json_val

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def text(self):
        return self._text

    async def json(self, **kwargs):
        if self._json is not None:
            return self._json
        import json
        return json.loads(self._text)


# ── Header helpers ─────────────────────────────────────────────────────────────

class TestEnfHeaders:
    def test_basic_headers(self):
        acc = EnformionAccount("test@example.com", "pass", "")
        h = _enf_headers(acc, "Person")
        assert h["galaxy-ap-name"] == "test@example.com"
        assert h["galaxy-ap-password"] == "pass"
        assert h["galaxy-search-type"] == "Person"
        assert h["Content-Type"] == "application/json"
        assert h["User-Agent"] == "SBBot/3.0"

    def test_headers_without_search_type(self):
        acc = EnformionAccount("a@b.com", "p", "")
        h = _enf_headers(acc, "")
        assert "galaxy-search-type" not in h

    def test_headers_phone(self):
        acc = EnformionAccount("test@example.com", "pass", "")
        h = _enf_headers(acc, "phone")
        assert h["galaxy-search-type"] == "ReversePhone"


class TestGalaxySearchType:
    @pytest.mark.parametrize("st,expected", [
        ("phone", "ReversePhone"),
        ("ph_lookup", "ReversePhone"),
        ("ph_batch", "ReversePhone"),
        ("batch_phones", "ReversePhone"),
        ("phone_identify", "PhoneIdentify"),
        ("phone_verify", "PhoneVerify"),
        ("background", "Person"),
        ("bg_batch", "Person"),
        ("address", "Person"),
        ("unknown", "Person"),
        ("", "Person"),
    ])
    def test_mapping(self, st, expected):
        assert _galaxy_search_type(st) == expected


# ── EnformionAccount ──────────────────────────────────────────────────────────

class TestEnformionAccount:
    def test_default_state(self):
        acc = EnformionAccount("a@b.com", "pass", "")
        assert acc.email == "a@b.com"
        assert acc.password == "pass"
        assert acc.status == "unknown"
        assert acc.balance == 0.0
        assert acc.searches == 0

    def test_with_proxy(self):
        acc = EnformionAccount("a@b.com", "pass", "http://proxy:8080")
        assert acc.proxy == "http://proxy:8080"


# ── Account file parsing ───────────────────────────────────────────────────────

class TestParseAccountsFile:
    @pytest.fixture
    def pool(self):
        return EnformionPool()

    def test_colon_email_password(self, pool):
        result = pool.parse_accounts_file("user@example.com:secretpass")
        assert len(result) == 1
        assert result[0] == {"email": "user@example.com", "password": "secretpass"}

    def test_colon_with_proxy(self, pool):
        result = pool.parse_accounts_file("user@example.com:secretpass:http://proxy:8080")
        assert result[0] == {"email": "user@example.com", "password": "secretpass", "proxy": "http://proxy:8080"}

    def test_colon_with_socks5_proxy(self, pool):
        result = pool.parse_accounts_file("user@example.com:secretpass:socks5://user:pass@proxyhost:1080")
        assert result[0]["email"] == "user@example.com"
        assert result[0]["proxy"] == "socks5://user:pass@proxyhost:1080"

    def test_space_separated(self, pool):
        result = pool.parse_accounts_file("user@example.com secretpass http://proxy:8080")
        assert result[0]["email"] == "user@example.com"
        assert result[0]["password"] == "secretpass"
        assert result[0]["proxy"] == "http://proxy:8080"

    def test_space_separated_no_proxy(self, pool):
        result = pool.parse_accounts_file("user@example.com secretpass")
        assert result[0] == {"email": "user@example.com", "password": "secretpass"}

    def test_multiple_lines(self, pool):
        content = "\n".join([
            "a@a.com:pass1:http://p1:8080",
            "b@b.com:pass2",
            "c@c.com pass3 http://p3:8080",
        ])
        result = pool.parse_accounts_file(content)
        assert len(result) == 3

    def test_skips_comments_and_empty(self, pool):
        content = "# comment\n\n  \n  valid@example.com:pass\n"
        result = pool.parse_accounts_file(content)
        assert len(result) == 1
        assert result[0]["email"] == "valid@example.com"

    def test_skips_non_email_lines(self, pool):
        content = "justapassword\nalsoinvalid\n"
        result = pool.parse_accounts_file(content)
        assert len(result) == 0


# ── SBResult ───────────────────────────────────────────────────────────────────

class TestSBResult:
    def test_success_result(self):
        r = SBResult(ok=True, search_type="phone", query={"phone": "123"}, people=[{"name": "John"}])
        assert r.ok is True
        assert len(r.people) == 1

    def test_failure_result(self):
        r = SBResult(ok=False, search_type="phone", query={"phone": "123"}, error="TIMEOUT")
        assert r.ok is False
        assert r.error == "TIMEOUT"

    def test_result_no_people_on_failure(self):
        r = SBResult(ok=False, search_type="phone", query={}, error="BLOCKED")
        assert r.people == []


# ── EnformionPool basics ───────────────────────────────────────────────────────

class TestEnformionPool:
    @pytest.fixture
    def pool(self):
        return EnformionPool()

    def test_base_url(self, pool):
        assert pool._base == "https://devapi.enformion.com"

    def test_no_accounts_by_default(self, pool):
        assert len(pool.accounts) == 0

    def test_load_accounts(self, pool):
        pool.load([
            {"email": "a@a.com", "password": "p1"},
            {"email": "b@b.com", "password": "p2"},
        ])
        assert len(pool.accounts) == 2
        assert pool.accounts[0].email == "a@a.com"
        assert pool.accounts[1].password == "p2"

    def test_load_with_proxy(self, pool):
        pool.load([{"email": "a@a.com", "password": "p", "proxy": "socks5://x:1080"}])
        assert pool.accounts[0].proxy == "socks5://x:1080"

    def test_load_maps_balance_tok(self, pool):
        pool.load([{"email": "a@a.com", "password": "p", "balance_tok": 75.0, "init_tok": 100.0}])
        assert pool.accounts[0].balance == 75.0
        assert pool.accounts[0].init_balance == 100.0

    def test_active_count_empty(self, pool):
        assert pool.active_count() == 0

    def test_active_count(self, pool):
        pool.load([
            {"email": "a@a.com", "password": "p", "status": "active"},
            {"email": "b@b.com", "password": "p", "status": "no_balance"},
        ])
        assert pool.active_count() == 1

    def test_needs_refill(self, pool):
        pool.load([
            {"email": "a@a.com", "password": "p", "status": "active"},
            {"email": "b@b.com", "password": "p", "status": "no_balance"},
        ])
        refill = pool.needs_refill()
        assert refill == ["b@b.com"]

    def test_status_report(self, pool):
        pool.load([{"email": "a@a.com", "password": "p", "balance_tok": 50.0, "init_tok": 100.0}])
        report = pool.status_report()
        assert len(report) == 1
        assert report[0]["email"] == "a@a.com"
        assert report[0]["pct"] == 50

    def test_status_report_no_init_balance(self, pool):
        pool.load([{"email": "a@a.com", "password": "p"}])
        report = pool.status_report()
        assert report[0]["pct"] == 0

    def test_pause_resume(self, pool):
        pool.pause()
        assert pool._pool_ok is False
        pool.resume()
        assert pool._pool_ok is True


# ── Response parsing ───────────────────────────────────────────────────────────

class TestResponseParsing:
    @pytest.fixture
    def pool(self):
        return EnformionPool()

    def _person(self, first="J", last="D", **kwargs):
        defaults = {
            "phoneNumbers": [], "locations": [], "emailAddresses": [],
            "relativesSummary": [], "akas": [], "addresses": [],
        }
        defaults.update(kwargs)
        return {"name": {"firstName": first, "lastName": last}, **defaults}

    def test_reverse_phone_single(self, pool):
        data = {
            "reversePhoneRecords": [{
                "tahoePerson": {
                    "name": {"firstName": "JOHN", "lastName": "DOE"},
                    "phoneNumbers": [{"phoneNumber": "2125551234", "phoneType": "Mobile"}],
                    "locations": [], "emailAddresses": [], "relativesSummary": [], "akas": [], "addresses": [],
                }
            }]
        }
        people = pool._parse_response("phone", data)
        assert len(people) == 1
        assert people[0]["name"] == "JOHN DOE"
        assert people[0]["phone"] == "2125551234"
        assert people[0]["phone_type"] == "Mobile"

    def test_reverse_phone_multiple(self, pool):
        data = {
            "reversePhoneRecords": [
                {"tahoePerson": self._person("A", "B", phoneNumbers=[{"phoneNumber": "111"}])},
                {"tahoePerson": self._person("C", "D", phoneNumbers=[{"phoneNumber": "222"}])},
            ]
        }
        people = pool._parse_response("phone", data)
        assert len(people) == 2
        assert people[0]["phone"] == "111"
        assert people[1]["phone"] == "222"

    def test_person_search_parsed(self, pool):
        data = {
            "persons": [{
                "name": {"firstName": "JOHN", "lastName": "DOE"},
                "age": 38,
                "locations": [{"addressLine1": "123 Main St", "city": "LA", "state": "CA"}],
                "phoneNumbers": [], "emailAddresses": [], "relativesSummary": [], "akas": [], "addresses": [],
            }]
        }
        people = pool._parse_response("background", data)
        assert len(people) == 1
        assert people[0]["name"] == "JOHN DOE"
        assert people[0]["age"] == 38

    def test_empty_response(self, pool):
        assert pool._parse_response("phone", {}) == []
        assert pool._parse_response("phone", {"reversePhoneRecords": None}) == []
        assert pool._parse_response("phone", {"persons": None}) == []

    def test_addresses_deduplication(self, pool):
        data = {
            "persons": [{
                "name": {"firstName": "J", "lastName": "D"},
                "currentAddress": {"addressLine1": "123 MAIN ST", "city": "LA", "state": "CA"},
                "historicalAddresses": [
                    {"addressLine1": "123 MAIN ST", "city": "LA", "state": "CA"},
                    {"addressLine1": "456 ELM ST", "city": "SF", "state": "CA"},
                ],
                "phoneNumbers": [], "emailAddresses": [], "relativesSummary": [], "akas": [], "addresses": [],
            }]
        }
        people = pool._parse_response("background", data)
        assert len(people[0]["addresses"]) == 2

    def test_null_fields_handled(self, pool):
        data = {"persons": [{"name": None, "age": None, "phoneNumbers": None, "locations": None, "currentAddress": None}]}
        people = pool._parse_response("background", data)
        assert isinstance(people, list)

    def test_null_in_lists(self, pool):
        data = {"persons": [{"name": {"firstName": "J"}, "phoneNumbers": [None], "locations": [{"city": None}], "emailAddresses": [], "relativesSummary": [], "akas": [], "addresses": []}]}
        people = pool._parse_response("background", data)
        assert isinstance(people, list)

    def test_null_string_handled(self, pool):
        data = {"persons": [{"name": {"firstName": "NULL", "lastName": "DOE"}, "phoneNumbers": [{"phoneNumber": "NULL"}], "locations": [], "emailAddresses": [], "relativesSummary": [], "akas": [], "addresses": []}]}
        people = pool._parse_response("background", data)
        assert people[0]["first_name"] == ""
        assert people[0]["phone"] == ""

    def test_voip_and_connected_to_extracted(self, pool):
        data = {"reversePhoneRecords": [{"tahoePerson": {"name": {"firstName": "J", "lastName": "D"}, "voipIndicator": True, "connectedTo": "Jane Doe", "phoneNumbers": [], "locations": [], "emailAddresses": [], "relativesSummary": [], "akas": [], "addresses": []}}]}
        people = pool._parse_response("phone", data)
        assert people[0]["voip"] is True
        assert people[0]["connected_to"] == "Jane Doe"

    def test_skips_records_with_no_identifying_info(self, pool):
        data = {"reversePhoneRecords": [{"tahoePerson": {"name": {}, "phoneNumbers": [], "locations": [], "emailAddresses": [], "relativesSummary": [], "akas": [], "addresses": []}}]}
        people = pool._parse_response("phone", data)
        assert len(people) == 0


# ── Endpoint/payload building ─────────────────────────────────────────────────

class TestMakeRequest:
    @pytest.fixture
    def pool(self):
        return EnformionPool()

    def test_phone_endpoint(self, pool):
        endpoint, payload = pool._make_request("phone", {"phone": "2125551234"})
        assert endpoint == "ReversePhoneSearch"
        assert payload == {"Phone": "2125551234"}

    def test_phone_empty(self, pool):
        endpoint, payload = pool._make_request("phone", {"phone": ""})
        assert endpoint is None

    def test_person_search_full(self, pool):
        endpoint, payload = pool._make_request("background", {"first_name": "John", "last_name": "Doe", "state": "CA"})
        assert endpoint == "PersonSearch"
        assert payload["FirstName"] == "JOHN"
        assert payload["LastName"] == "DOE"
        assert payload["State"] == "CA"

    def test_person_search_no_state(self, pool):
        endpoint, payload = pool._make_request("background", {"first_name": "John", "last_name": "Doe"})
        assert endpoint == "PersonSearch"
        assert "State" not in payload

    def test_phone_verify(self, pool):
        endpoint, _ = pool._make_request("phone_verify", {"phone": "123"})
        assert endpoint == "VerifyPhone"

    def test_phone_identify(self, pool):
        endpoint, _ = pool._make_request("phone_identify", {"phone": "123"})
        assert endpoint == "IdentifyPhoneType"

    def test_email_unsupported(self, pool):
        endpoint, payload = pool._make_request("email", {"email": "a@b.com"})
        assert endpoint is False
        assert payload == "EMAIL_SEARCH_UNSUPPORTED"

    def test_unknown_defaults_to_person(self, pool):
        endpoint, _ = pool._make_request("unknown_type", {"foo": "bar"})
        assert endpoint == "PersonSearch"

    def test_address_raw_parse(self, pool):
        endpoint, payload = pool._make_request("address", {"address": "123 Main St, City, ST"})
        assert endpoint == "PersonSearch"
        # Raw address used as FirstName (no uppercase applied by engine)
        assert payload["FirstName"] == "123 Main St"
        assert payload["State"] == "ST"

    def test_address_no_name_no_raw(self, pool):
        endpoint, payload = pool._make_request("address", {"address": ""})
        assert endpoint is None


# ── No accounts ────────────────────────────────────────────────────────────────

class TestPoolNoAccounts:
    @pytest.fixture
    def pool(self):
        return EnformionPool()

    @pytest.mark.asyncio
    async def test_search_no_accounts(self, pool):
        result = await pool.search("phone", {"phone": "1234567890"})
        assert result.ok is False


# ── 401/402 handling ──────────────────────────────────────────────────────────

class TestHttpErrorHandling:
    @pytest.fixture
    def pool(self):
        p = EnformionPool()
        p.load([{"email": "a@a.com", "password": "p", "status": "active"}])
        return p

    @pytest.mark.asyncio
    async def test_401_sets_blocked(self, pool):
        mock_ctx = MagicMock()
        mock_ctx.post = MagicMock(return_value=FakeResp(401, '{"error": "bad"}'))
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_ctx.__aexit__ = AsyncMock()
        with patch("aiohttp.ClientSession", return_value=mock_ctx):
            result = await pool.search("phone", {"phone": "123"})
            assert result.ok is False
            assert result.error == "BLOCKED"
            assert pool.accounts[0].status == "blocked"

    @pytest.mark.asyncio
    async def test_402_sets_no_balance(self, pool):
        mock_ctx = MagicMock()
        mock_ctx.post = MagicMock(return_value=FakeResp(402, '{"error": "no tokens"}'))
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_ctx.__aexit__ = AsyncMock()
        with patch("aiohttp.ClientSession", return_value=mock_ctx):
            result = await pool.search("phone", {"phone": "123"})
            assert result.ok is False
            assert result.error == "NO_TOKENS"
            assert pool.accounts[0].status == "no_balance"


# ── EmailRep ─────────────────────────────────────────────────────────────────

class TestEmailRep:
    @pytest.fixture
    def pool(self):
        return EnformionPool()

    @pytest.mark.asyncio
    async def test_emailrep_no_key(self, pool):
        result = await pool.emailrep_lookup("a@b.com", api_key="")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_emailrep_success(self, pool):
        mock_ctx = MagicMock()
        mock_ctx.get = MagicMock(return_value=FakeResp(200, '{"reputation": "high"}', {"email": "a@b.com", "reputation": "high"}))
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_ctx.__aexit__ = AsyncMock()
        with patch("aiohttp.ClientSession", return_value=mock_ctx):
            result = await pool.emailrep_lookup("a@b.com", api_key="test_key")
            assert result.get("reputation") == "high"