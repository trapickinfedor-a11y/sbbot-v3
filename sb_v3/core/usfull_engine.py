"""
usfull_engine.py — API client for usfull.pro
Supports: SSN/DOB Search, Driver License, Credit Report, Credit Score, Balance

API Base: https://usfull.pro
Auth: X-API-KEY header + optional HTTPBasicAuth
"""

import asyncio
import logging
import time
import aiohttp
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

USFULL_BASE = "https://usfull.pro"


# ─── Health scoring & circuit breaker ────────────────────────────────────────

class HealthScore:
    MAX_ERROR_WINDOW = 20
    LATENCY_WINDOW = 10

    def __init__(self):
        self._error_window: list[bool] = []
        self._latency_window: list[float] = []
        self._consecutive_errors: int = 0
        self._consecutive_ok: int = 0
        self._last_latency: float = 0.0

    def record_ok(self, latency: float = 0.0):
        self._error_window.append(False)
        self._latency_window.append(latency)
        if len(self._error_window) > self.MAX_ERROR_WINDOW:
            self._error_window.pop(0)
        if len(self._latency_window) > self.LATENCY_WINDOW:
            self._latency_window.pop(0)
        self._consecutive_ok += 1
        self._consecutive_errors = 0
        self._last_latency = latency

    def record_error(self, latency: float = 0.0):
        self._error_window.append(True)
        self._latency_window.append(latency)
        if len(self._error_window) > self.MAX_ERROR_WINDOW:
            self._error_window.pop(0)
        if len(self._latency_window) > self.LATENCY_WINDOW:
            self._latency_window.pop(0)
        self._consecutive_errors += 1
        self._consecutive_ok = 0
        self._last_latency = latency

    def score(self) -> float:
        if not self._error_window:
            return 100.0
        n = len(self._error_window)
        errors = sum(self._error_window)
        error_rate = errors / n
        error_score = (1.0 - error_rate) * 50
        avg_latency = sum(self._latency_window) / len(self._latency_window) if self._latency_window else 0
        latency_score = max(0, 30 * (1.0 - min(avg_latency / 30.0, 1.0)))
        ok_bonus = min(10, self._consecutive_ok * 0.5)
        error_penalty = min(10, self._consecutive_errors)
        return max(0.0, min(100.0, error_score + latency_score + ok_bonus - error_penalty))

    def reset(self):
        self._error_window.clear()
        self._latency_window.clear()
        self._consecutive_errors = 0
        self._consecutive_ok = 0


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 10,
        recovery_timeout: float = 60.0,
        half_open_max: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_attempts = 0
        self._total_failures = 0
        self._total_successes = 0

    @property
    def state(self) -> str:
        if self._state == self.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = self.HALF_OPEN
                self._half_open_attempts = 0
        return self._state

    def allow_request(self) -> bool:
        return self.state in (self.CLOSED, self.HALF_OPEN)

    def record_success(self):
        self._total_successes += 1
        if self._state == self.HALF_OPEN:
            self._half_open_attempts += 1
            if self._half_open_attempts >= self.half_open_max:
                self._state = self.CLOSED
                self._failure_count = 0
        elif self._state == self.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._state == self.HALF_OPEN:
            self._state = self.OPEN
        elif self._state == self.CLOSED and self._failure_count >= self.failure_threshold:
            self._state = self.OPEN

    @property
    def failure_rate(self) -> float:
        total = self._total_failures + self._total_successes
        if total == 0:
            return 0.0
        return self._total_failures / total

    def reset(self):
        self._state = self.CLOSED
        self._failure_count = 0
        self._half_open_attempts = 0

# ─── Pricing ────────────────────────────────────────────────────────────────
USFULL_PRICES = {
    "ssn_dob":        {"success": 0.40, "no_result": 0.01},
    "driver_license": {"success": 1.00, "no_result": 0.00},
    "credit_report":  {"success": 2.50, "no_result": 0.00},
    "credit_score":   {"success": 2.00, "no_result": 0.00},
}


# ─── Account dataclass ───────────────────────────────────────────────────────
@dataclass
class UsfullAccount:
    username: str
    password: str
    api_key: str
    balance: float = 0.0
    initial_balance: float = 0.0
    status: str = "active"   # active | low_balance | no_balance | blocked | failed
    requests_done: int = 0
    proxy: Optional[str] = None
    last_checked: Optional[datetime] = None
    health: HealthScore = field(default_factory=HealthScore)

    @property
    def balance_pct(self) -> float:
        if self.initial_balance <= 0:
            return 100.0
        return (self.balance / self.initial_balance) * 100.0

    @property
    def is_usable(self) -> bool:
        return self.status in ("active", "low_balance") and self.balance > 0


# ─── Main engine ─────────────────────────────────────────────────────────────
class UsfullEngine:
    """
    Manages a pool of usfull.pro accounts with round-robin load balancing.
    Each account is permanently bound to one proxy.
    Health-aware account selection, circuit breaker, rate limiting.
    """

    def __init__(self):
        self.accounts: List[UsfullAccount] = []
        self._rr_index = 0
        self._lock = asyncio.Lock()
        self._alert_callback = None   # async fn(account, event_type)
        self.api_key: str = ""        # fallback API key when no accounts loaded

        # Circuit breaker
        self._cb = CircuitBreaker(failure_threshold=10, recovery_timeout=60.0)

        # Rate limiting
        self._min_interval = 0.3
        self._last_request: float = 0.0

        # In-memory cache
        self._cache: Dict[str, dict] = {}
        self._cache_ttl: int = 3600  # 1 hour

    def set_alert_callback(self, cb):
        self._alert_callback = cb

    def set_min_interval(self, seconds: float):
        self._min_interval = seconds

    # ── Account management ─────────────────────────────────────────────────────

    def load_accounts(self, accounts_data: List[dict]):
        """Load accounts from list of dicts (from DB)."""
        self.accounts = []
        for acc in accounts_data:
            enformion_acc = UsfullAccount(
                username=acc.get("username", ""),
                password=acc.get("password", ""),
                api_key=acc.get("api_key", ""),
                balance=acc.get("balance", 0.0),
                initial_balance=acc.get("initial_balance", acc.get("balance", 0.0)),
                status=acc.get("status", "active"),
                proxy=acc.get("proxy"),
            )
            self.accounts.append(enformion_acc)
        self._cb.reset()
        logger.info(f"[USFULL] Loaded {len(self.accounts)} accounts")

    def active_count(self) -> int:
        return sum(1 for a in self.accounts if a.status in ("active", "low_balance"))

    def _record_result(self, ok: bool, acc: UsfullAccount):
        """Record result and update circuit breaker + health scores."""
        if ok:
            acc.health.record_ok()
            self._cb.record_success()
        else:
            acc.health.record_error()

    def reset_error_rate(self):
        """Reset after admin fixes the issue."""
        self._cb.reset()

    def clear_cache(self):
        """Clear in-memory cache."""
        self._cache.clear()
        logger.info("[USFULL] Cache cleared")

    def add_account(self, username: str, password: str, api_key: str,
                    proxy: Optional[str] = None, balance: float = 0.0):
        acc = UsfullAccount(
            username=username,
            password=password,
            api_key=api_key,
            balance=balance,
            initial_balance=balance,
            proxy=proxy,
        )
        self.accounts.append(acc)
        logger.info(f"[USFULL] Added account {username}")
        return acc

    async def _get_account(self) -> Optional[UsfullAccount]:
        """Health-aware account selection: prefer accounts with higher health scores."""
        if not self._cb.allow_request():
            return None
        async with self._lock:
            usable = [a for a in self.accounts if a.is_usable]
            if not usable:
                # Fallback: use global api_key as a single synthetic account
                if self.api_key:
                    acc = UsfullAccount(
                        username="__global__",
                        password="",
                        api_key=self.api_key,
                    )
                    acc.status = "active"
                    acc.balance = 999999.0
                    return acc
                return None
            # Sort by health score descending, then round-robin within same score tier
            usable.sort(key=lambda a: a.health.score(), reverse=True)
            acc = usable[self._rr_index % len(usable)]
            self._rr_index += 1
            return acc

    async def _wait_rate_limit(self):
        """Enforce minimum interval between requests."""
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()

    def _make_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
            "User-Agent": "SBBot/2.0",
        }

    async def _post(self, endpoint: str, data: Dict, account: UsfullAccount) -> Dict:
        url = f"{USFULL_BASE}{endpoint}"
        headers = self._make_headers(account.api_key)
        connector = None
        if account.proxy:
            try:
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(account.proxy)
            except ImportError:
                connector = aiohttp.TCPConnector()
        else:
            connector = aiohttp.TCPConnector()

        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    result = await resp.json(content_type=None)
                    http_status = resp.status
                    result["_http_status"] = http_status
                    logger.info(f"[USFULL] {endpoint} → HTTP {http_status} | acc={account.username}")
                    return result
        except asyncio.TimeoutError:
            logger.error(f"[USFULL] {endpoint} TIMEOUT | acc={account.username}")
            return {"_http_status": 0, "status": "error", "message": "Timeout"}
        except Exception as e:
            logger.error(f"[USFULL] {endpoint} EXCEPTION: {e} | acc={account.username}", exc_info=True)
            return {"_http_status": 0, "status": "error", "message": str(e)}

    async def _get(self, endpoint: str, account: UsfullAccount) -> Dict:
        url = f"{USFULL_BASE}{endpoint}"
        headers = self._make_headers(account.api_key)
        connector = None
        if account.proxy:
            try:
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(account.proxy)
            except ImportError:
                connector = aiohttp.TCPConnector()
        else:
            connector = aiohttp.TCPConnector()

        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    result = await resp.json(content_type=None)
                    result["_http_status"] = resp.status
                    logger.info(f"[USFULL] GET {endpoint} → HTTP {resp.status} | acc={account.username}")
                    return result
        except Exception as e:
            logger.error(f"[USFULL] GET {endpoint} EXCEPTION: {e} | acc={account.username}", exc_info=True)
            return {"_http_status": 0, "status": "error", "message": str(e)}

    async def _update_balance_after(self, account: UsfullAccount):
        """Refresh balance after a request and trigger alerts if needed."""
        result = await self._get("/api/get_balance/", account)
        if result.get("_http_status") == 200:
            old_balance = account.balance
            new_balance = float(result.get("balance", account.balance))
            account.balance = new_balance
            account.last_checked = datetime.now()

            # Update status
            old_status = account.status
            if new_balance <= 0:
                account.status = "no_balance"
            elif account.balance_pct <= 30:
                account.status = "low_balance"
            else:
                account.status = "active"

            # Fire alert if status changed
            if self._alert_callback and old_status != account.status:
                asyncio.create_task(
                    self._alert_callback(account, account.status)
                )

    # ─── Public API methods ──────────────────────────────────────────────────

    async def search_ssn_dob(
        self,
        first_name: str,
        last_name: str,
        dob: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        phone: Optional[str] = None,
        ssn: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        SSN/DOB Search — POST /api/search/
        Returns list of matching persons with SSN, DOB, address, phone.
        Cost: $0.40 success / $0.01 no result
        """
        await self._wait_rate_limit()
        account = await self._get_account()
        if not account:
            return {"ok": False, "error": "CIRCUIT_OPEN or no available usfull accounts", "results": []}

        # Cache check
        import hashlib, json as _json
        cache_key = f"usfull:ssn_dob:{hashlib.md5(_json.dumps(data, sort_keys=True).encode()).hexdigest()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        data: Dict[str, Any] = {
            "firstname": first_name.upper(),
            "lastname": last_name.upper(),
        }
        if dob:
            data["dob"] = _normalize_dob(dob)
        if city:
            data["city"] = city.upper()
        if state:
            data["st"] = state.upper()
        if zip_code:
            data["zip"] = zip_code
        if phone:
            cleaned = "".join(c for c in phone if c.isdigit())
            if cleaned.startswith("1") and len(cleaned) == 11:
                cleaned = cleaned[1:]
            data["phone"] = int(cleaned) if cleaned else None
        if ssn:
            cleaned_ssn = "".join(c for c in ssn if c.isdigit())
            data["ssn"] = int(cleaned_ssn) if cleaned_ssn else None

        result = await self._post("/api/search/", data, account)
        account.requests_done += 1
        asyncio.create_task(self._update_balance_after(account))

        http_status = result.get("_http_status", 0)
        if http_status == 200:
            results = result.get("results", [])
            self._record_result(True, account)

            # Fallback: if first attempt with state fails or has 0 results, retry without state
            if not results and state:
                result_retry = await self.search_ssn_dob(
                    first_name=first_name, last_name=last_name,
                    dob=dob, city=city, state=None, zip_code=zip_code,
                    phone=phone, ssn=ssn
                )
                if result_retry.get("ok") and result_retry.get("results"):
                    result_retry["_fallback"] = True
                    self._cache[cache_key] = result_retry
                    return result_retry

            # Fallback: if still no results, try with city only
            if not results and city and not state:
                result_city = await self.search_ssn_dob(
                    first_name=first_name, last_name=last_name,
                    dob=dob, city=city, state=None, zip_code=zip_code,
                    phone=phone, ssn=ssn
                )
                if result_city.get("ok") and result_city.get("results"):
                    result_city["_fallback"] = True
                    self._cache[cache_key] = result_city
                    return result_city

            ret = {
                "ok": True,
                "results": results,
                "count": result.get("count", len(results)),
                "account": account.username,
            }
            self._cache[cache_key] = ret
            return ret
        elif http_status == 403:
            account.status = "blocked"
            self._record_result(False, account)
            return {"ok": False, "error": "Account blocked or invalid API key", "results": []}
        elif http_status == 402:
            account.status = "no_balance"
            self._record_result(False, account)
            return {"ok": False, "error": "Insufficient balance", "results": []}
        else:
            self._record_result(False, account)
            return {"ok": False, "error": result.get("message", f"HTTP {http_status}"), "results": []}

    async def search_ssn_by_ssn_direct(self, ssn: str) -> Dict[str, Any]:
        """Direct SSN search when SSN is already known from previous result."""
        return {"ok": False, "error": "Direct SSN search requires name+DOB+address"}

    async def search_driver_license(
        self,
        first_name: str,
        last_name: str,
        address: str,
        zipcode: str,
        dob: str,
    ) -> Dict[str, Any]:
        """
        Driver License Search — POST /api/dl/
        Returns license number and state.
        Cost: $1.00 success
        """
        account = await self._get_account()
        if not account:
            return {"ok": False, "error": "No available usfull accounts"}

        # Cache check
        import hashlib, json as _json
        cache_data = {
            "first_name": first_name[:15].upper(),
            "last_name": last_name[:15].upper(),
            "address": address[:50].upper(),
            "zipcode": zipcode,
            "dob": _normalize_dob_dl(dob),
        }
        cache_key = f"usfull:driver_license:{hashlib.md5(_json.dumps(cache_data, sort_keys=True).encode()).hexdigest()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        data = {
            "first_name": first_name[:15].upper(),
            "last_name": last_name[:15].upper(),
            "address": address[:50].upper(),
            "zipcode": zipcode,
            "dob": _normalize_dob_dl(dob),
        }

        result = await self._post("/api/dl/", data, account)
        account.requests_done += 1
        asyncio.create_task(self._update_balance_after(account))

        http_status = result.get("_http_status", 0)
        if http_status == 200 and result.get("status") == "success":
            self._record_result(True, account)
            ret = {
                "ok": True,
                "license_number": result.get("license_number"),
                "license_state": result.get("license_state"),
                "balance_deducted": result.get("balance_deducted"),
                "remaining_balance": result.get("remaining_balance"),
                "account": account.username,
            }
            self._cache[cache_key] = ret
            return ret
        elif http_status == 401:
            account.status = "blocked"
            self._record_result(False, account)
            return {"ok": False, "error": "Invalid API key"}
        elif http_status == 402:
            account.status = "no_balance"
            self._record_result(False, account)
            return {"ok": False, "error": "Insufficient balance"}
        else:
            self._record_result(False, account)
            return {"ok": False, "error": result.get("message", f"HTTP {http_status}")}

    async def search_credit_report(
        self,
        first_name: str,
        last_name: str,
        street_address: str,
        city: str,
        state: str,
        zip_code: str,
        dob: str,
        ssn: str,
    ) -> Dict[str, Any]:
        """
        Credit Report Search — POST /api/cr/
        Cost: $2.50 success
        """
        account = await self._get_account()
        if not account:
            return {"ok": False, "error": "No available usfull accounts"}

        # Cache check
        import hashlib, json as _json
        ssn_clean = "".join(c for c in ssn if c.isdigit())
        cache_data = {
            "first_name": first_name.upper(),
            "last_name": last_name.upper(),
            "street_address": street_address.upper(),
            "city": city.upper(),
            "state": state.upper(),
            "zip_code": zip_code,
            "dob": _normalize_dob_dl(dob),
            "ssn": ssn_clean,
        }
        cache_key = f"usfull:credit_report:{hashlib.md5(_json.dumps(cache_data, sort_keys=True).encode()).hexdigest()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        data = {
            "first_name": first_name.upper(),
            "last_name": last_name.upper(),
            "street_address": street_address.upper(),
            "city": city.upper(),
            "state": state.upper(),
            "zip_code": zip_code,
            "dob": _normalize_dob_dl(dob),
            "ssn": ssn_clean,
        }

        result = await self._post("/api/cr/", data, account)
        account.requests_done += 1
        asyncio.create_task(self._update_balance_after(account))

        http_status = result.get("_http_status", 0)
        if http_status == 200:
            self._record_result(True, account)
            ret = {"ok": True, "data": result, "account": account.username}
            self._cache[cache_key] = ret
            return ret
        elif http_status == 402:
            account.status = "no_balance"
            self._record_result(False, account)
            return {"ok": False, "error": "Insufficient balance"}
        else:
            self._record_result(False, account)
            return {"ok": False, "error": result.get("message", f"HTTP {http_status}")}

    async def search_credit_score(
        self,
        first_name: str,
        last_name: str,
        street_address: str,
        city: str,
        state: str,
        zip_code: str,
        dob: str,
        ssn: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Credit Score Search — POST /api/credit-score/
        Cost: $2.00 success
        """
        account = await self._get_account()
        if not account:
            return {"ok": False, "error": "No available usfull accounts"}

        # Cache check
        import hashlib, json as _json
        cache_data = {
            "first_name": first_name.upper(),
            "last_name": last_name.upper(),
            "street_address": street_address.upper(),
            "city": city.upper(),
            "state": state.upper(),
            "zip_code": zip_code,
            "dob": _normalize_dob_dl(dob),
        }
        if ssn:
            cache_data["ssn"] = "".join(c for c in ssn if c.isdigit())
        cache_key = f"usfull:credit_score:{hashlib.md5(_json.dumps(cache_data, sort_keys=True).encode()).hexdigest()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        data = {
            "first_name": first_name.upper(),
            "last_name": last_name.upper(),
            "street_address": street_address.upper(),
            "city": city.upper(),
            "state": state.upper(),
            "zip_code": zip_code,
            "dob": _normalize_dob_dl(dob),
        }
        if ssn:
            data["ssn"] = "".join(c for c in ssn if c.isdigit())

        result = await self._post("/api/credit-score/", data, account)
        account.requests_done += 1
        asyncio.create_task(self._update_balance_after(account))

        http_status = result.get("_http_status", 0)
        if http_status == 200:
            self._record_result(True, account)
            ret = {"ok": True, "data": result, "account": account.username}
            self._cache[cache_key] = ret
            return ret
        elif http_status == 402:
            account.status = "no_balance"
            self._record_result(False, account)
            return {"ok": False, "error": "Insufficient balance"}
        else:
            self._record_result(False, account)
            return {"ok": False, "error": result.get("message", f"HTTP {http_status}")}

    async def get_balance(self, account: UsfullAccount) -> Optional[float]:
        """Fetch balance for a specific account."""
        result = await self._get("/api/get_balance/", account)
        if result.get("_http_status") == 200:
            balance = float(result.get("balance", 0))
            account.balance = balance
            account.last_checked = datetime.now()
            return balance
        return None

    async def refresh_all_balances(self):
        """Refresh balances for all accounts."""
        tasks = [self.get_balance(acc) for acc in self.accounts]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def create_token(self, username: str, password: str) -> Optional[str]:
        """
        Create API token — POST /api/create_token/
        Returns the new token string.
        """
        url = f"{USFULL_BASE}/api/create_token/"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SBBot/2.0",
        }
        data = {"username": username, "password": password}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        result = await resp.json(content_type=None)
                        token = result.get("token") or result.get("api_key") or result.get("key")
                        return token
        except Exception as e:
            logger.error(f"[USFULL] create_token error: {e}")
        return None

    def get_pool_status(self) -> List[Dict]:
        """Return status of all accounts."""
        out = []
        for acc in self.accounts:
            out.append({
                "username": acc.username,
                "status": acc.status,
                "balance": acc.balance,
                "balance_pct": round(acc.balance_pct, 1),
                "requests_done": acc.requests_done,
                "proxy": acc.proxy or "none",
                "health_score": round(acc.health.score(), 1),
                "last_checked": acc.last_checked.strftime("%H:%M:%S") if acc.last_checked else "never",
            })
        out.append({
            "circuit_breaker": self._cb.state,
            "cb_failure_rate": round(self._cb.failure_rate * 100, 1),
        })
        return out

    # ─── Batch helpers ───────────────────────────────────────────────────────

    async def batch_ssn_dob(
        self,
        queries: List[Dict],
        concurrency: int = 5,
        progress_cb=None,
    ) -> List[Dict]:
        """
        Process multiple SSN/DOB queries in parallel.
        Each query: {first_name, last_name, dob?, city?, state?, zip?, phone?, ssn?}
        """
        sem = asyncio.Semaphore(concurrency)
        results = []
        total = len(queries)
        done = 0

        async def _one(q: Dict, idx: int):
            nonlocal done
            async with sem:
                r = await self.search_ssn_dob(**q)
                r["_query_index"] = idx
                r["_input"] = q
                done += 1
                if progress_cb:
                    await progress_cb(done, total)
                return r

        tasks = [_one(q, i) for i, q in enumerate(queries)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if not isinstance(r, Exception) else {"ok": False, "error": str(r)} for r in results]


# ─── DOB normalization helpers ───────────────────────────────────────────────

def _normalize_dob(dob: str) -> str:
    """Normalize DOB to YYYYMMDD for /api/search/"""
    if not dob:
        return ""
    dob = dob.strip()
    # Already YYYYMMDD
    if len(dob) == 8 and dob.isdigit():
        return dob
    # YYYY only
    if len(dob) == 4 and dob.isdigit():
        return dob
    # MM/DD/YYYY
    import re
    m = re.match(r'^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$', dob)
    if m:
        month, day, year = m.groups()
        return f"{year}{int(month):02d}{int(day):02d}"
    # YYYY-MM-DD
    m = re.match(r'^(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})$', dob)
    if m:
        year, month, day = m.groups()
        return f"{year}{int(month):02d}{int(day):02d}"
    return dob


def _normalize_dob_dl(dob: str) -> str:
    """Normalize DOB for /api/dl/ — accepts DD.MM.YYYY, MM/DD/YYYY, YYYY-MM-DD, YYYYMMDD"""
    if not dob:
        return ""
    dob = dob.strip()
    import re
    # MM/DD/YYYY → keep as is (accepted)
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', dob):
        return dob
    # DD.MM.YYYY → keep as is (accepted)
    if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', dob):
        return dob
    # YYYY-MM-DD → keep as is (accepted)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', dob):
        return dob
    # YYYYMMDD → keep as is (accepted)
    if re.match(r'^\d{8}$', dob):
        return dob
    # Try to convert from other formats
    m = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$', dob)
    if m:
        p1, p2, year = m.groups()
        return f"{int(p1):02d}/{int(p2):02d}/{year}"
    return dob


# ─── Singleton ───────────────────────────────────────────────────────────────
usfull_engine = UsfullEngine()


# ─── Chain helpers ────────────────────────────────────────────────────────────

def extract_ssn_params(ssn_result: dict) -> dict:
    """Extract params for Credit Report from SSN/DOB result."""
    if not ssn_result.get("ok") or not ssn_result.get("results"):
        return {}
    rec = ssn_result["results"][0]
    return {
        "first_name": rec.get("firstname", "") or "",
        "last_name": rec.get("lastname", "") or "",
        "dob": rec.get("dob", "") or "",
        "ssn": str(rec.get("ssn", "") or ""),
        "address": rec.get("address", "") or "",
        "city": rec.get("city", "") or "",
        "state": rec.get("st", "") or "",
        "zip": rec.get("zip", "") or "",
    }


def extract_person_for_ssf(person: dict) -> dict:
    """Extract SSN search params from Enformion person."""
    name = person.get("name", "")
    parts = name.split()
    return {
        "first_name": parts[0] if parts else "",
        "last_name": " ".join(parts[1:]) if len(parts) > 1 else "",
        "state": person.get("location", "").split(",")[-1].strip()[:2] if person.get("location") else "",
    }


def extract_person_for_dl(person: dict) -> dict:
    """Extract DL search params from Enformion person."""
    name = person.get("name", "")
    parts = name.split()
    addr = person.get("address", "") or person.get("location", "")
    addr_parts = addr.split(",") if addr else ["", "", ""]
    return {
        "first_name": parts[0] if parts else "",
        "last_name": " ".join(parts[1:]) if len(parts) > 1 else "",
        "address": addr_parts[0].strip() if addr_parts else "",
        "zip": addr_parts[-1].strip()[:10] if len(addr_parts) > 2 else "",
        "dob": person.get("dob", "") or "",
    }
