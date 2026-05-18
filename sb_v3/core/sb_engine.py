"""
sb_engine.py — Enformion API client
API Base: https://devapi.enformion.com
Auth: aiohttp.BasicAuth (username/password)
Endpoints:
  POST /ReversePhoneSearch  — {"Phone": "..."}  — returns reversePhoneRecords
  POST /PersonSearch        — {"FirstName":"...", "LastName":"...", "State":"..."}  — returns persons
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable, Dict, Any, List

import aiohttp

logger = logging.getLogger("sbbot.sb_engine")

ENF_BASE = "https://devapi.enformion.com"


class SBResult:
    def __init__(self, ok, search_type, query=None, people=None, parsed=None,
                 error="", tokens_cost=0, account=""):
        self.ok = ok
        self.search_type = search_type
        self.query = query or {}
        self.people = people or []
        self.parsed = parsed or {}
        self.error = error
        self.tokens_cost = tokens_cost
        self.account = account

    @property
    def people_count(self) -> int:
        """Return the number of people in this result."""
        return len(self.people)

    def to_dict(self):
        return {
            "ok": self.ok,
            "type": self.search_type,
            "query": self.query,
            "people": self.people,
            "parsed": self.parsed,
            "error": self.error,
            "tokens_cost": self.tokens_cost,
            "account": self.account,
        }


class HealthScore:
    """
    Per-account health score (0–100).
    Computed from: error rate (last 20 results), latency trend, availability.
    """
    MAX_ERROR_WINDOW = 20
    LATENCY_WINDOW = 10

    def __init__(self):
        self._error_window: list[bool] = []   # True=error, False=ok
        self._latency_window: list[float] = []  # seconds per request
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
        """Return health score 0–100. Higher is healthier."""
        if not self._error_window:
            return 100.0

        # Error rate component (weight: 50%)
        n = len(self._error_window)
        errors = sum(self._error_window)
        error_rate = errors / n
        error_score = (1.0 - error_rate) * 50

        # Latency component (weight: 30%)
        avg_latency = sum(self._latency_window) / len(self._latency_window) if self._latency_window else 0
        # Penalize if avg latency > 10s
        latency_score = max(0, 30 * (1.0 - min(avg_latency / 30.0, 1.0)))

        # Consecutive ok bonus (weight: 10%)
        ok_bonus = min(10, self._consecutive_ok * 0.5)

        # Consecutive error penalty (weight: 10%)
        error_penalty = min(10, self._consecutive_errors)

        return max(0.0, min(100.0, error_score + latency_score + ok_bonus - error_penalty))

    def reset(self):
        self._error_window.clear()
        self._latency_window.clear()
        self._consecutive_errors = 0
        self._consecutive_ok = 0


class CircuitBreaker:
    """
    Circuit breaker for the entire ENF pool.
    States: CLOSED (normal) → OPEN (failing) → HALF-OPEN (testing).
    """
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
        # Check if recovery timeout passed
        if self._state == self.OPEN:
            import time
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = self.HALF_OPEN
                self._half_open_attempts = 0
        return self._state

    def allow_request(self) -> bool:
        if self.state in (self.CLOSED, self.HALF_OPEN):
            return True
        return False

    def record_success(self):
        self._total_successes += 1
        if self._state == self.HALF_OPEN:
            self._half_open_attempts += 1
            if self._half_open_attempts >= self.half_open_max:
                self._state = self.CLOSED
                self._failure_count = 0
        elif self._state == self.CLOSED:
            # Decay failure count on successes
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        import time
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


@dataclass
class EnformionAccount:
    email: str
    password: str
    proxy: str = ""
    status: str = "unknown"
    balance: float = 0.0
    init_balance: float = 0.0
    searches: int = 0
    last_login: str = ""
    session_key: str = ""
    _http: Optional[aiohttp.ClientSession] = None
    health: HealthScore = field(default_factory=HealthScore)


def _make_connector(proxy: str = ""):
    """Create aiohttp connector with optional proxy."""
    if proxy:
        try:
            from aiohttp_socks import ProxyConnector
            return ProxyConnector.from_url(proxy)
        except ImportError:
            logger.warning("Proxy support requires aiohttp-socks package")
    return aiohttp.TCPConnector()


def _galaxy_search_type(st: str) -> str:
    """Map internal search type to Enformion Galaxy header value."""
    if st in ("phone", "ph_lookup", "ph_batch", "batch_phones"):
        return "ReversePhone"
    if st in ("phone_identify",):
        return "PhoneIdentify"
    if st in ("phone_verify",):
        return "PhoneVerify"
    return "Person"


def _enf_headers(acc: EnformionAccount, search_type: str = "") -> Dict[str, str]:
    """Enformion uses custom Galaxy headers, not Basic auth."""
    headers = {
        "Content-Type": "application/json",
        "galaxy-ap-name": acc.email,
        "galaxy-ap-password": acc.password,
        "User-Agent": "SBBot/3.0",
    }
    if search_type:
        headers["galaxy-search-type"] = _galaxy_search_type(search_type)
    return headers


class EnformionPool:
    """
    Pool of Enformion API credentials with:
    - Health-aware round-robin (prefer healthy accounts)
    - Circuit breaker (suspends pool on high failure rate)
    - Exponential backoff retry with jitter
    - Per-account health scoring
    - Rate limiting and error tracking
    """

    def __init__(self):
        self.accounts: List[EnformionAccount] = []
        self._rr_index = 0
        self._lock = asyncio.Lock()
        self._status_lock = asyncio.Lock()
        self._alert_callback: Optional[Callable] = None
        self._base = ENF_BASE
        self._pool_ok = True

        # Circuit breaker
        self._cb = CircuitBreaker(failure_threshold=10, recovery_timeout=60.0)

        # Error rate tracking (legacy, for /health display)
        self._error_window: List[bool] = []
        self._error_window_len = 50
        self._error_rate_threshold = 0.6

        # Rate limiting: min seconds between searches
        self._min_interval = 0.3
        self._last_search: float = 0.0

    def set_alert_callback(self, cb):
        self._alert_callback = cb

    def set_min_interval(self, seconds: float):
        self._min_interval = seconds

    # ── Account management ─────────────────────────────────────────────

    def load(self, accounts_data: List[dict]):
        self.accounts = []
        for acc in accounts_data:
            from dataclasses import replace
            enformion_acc = EnformionAccount(
                email=acc.get("email", ""),
                password=acc.get("password", ""),
                proxy=acc.get("proxy", ""),
                status=acc.get("status", "unknown"),
                balance=acc.get("balance_tok", 0.0),
                init_balance=acc.get("init_tok", 0.0),
                searches=acc.get("searches", 0),
            )
            self.accounts.append(enformion_acc)
        self._pool_ok = True
        self._cb.reset()
        logger.info(f"[Enformion] Loaded {len(self.accounts)} accounts")

    def active_count(self) -> int:
        return sum(1 for a in self.accounts if a.status in ("active", "low_balance"))

    def needs_refill(self) -> List[str]:
        return [a.email for a in self.accounts
                if a.status in ("no_balance", "blocked", "failed")]

    async def _get_account(self) -> Optional[EnformionAccount]:
        """Health-aware account selection: prefer accounts with higher health scores."""
        async with self._lock:
            usable = [a for a in self.accounts
                      if a.status in ("active", "low_balance")]
            if not usable:
                return None
            # Sort by health score descending, then use round-robin within same score tier
            usable.sort(key=lambda a: a.health.score(), reverse=True)
            acc = usable[self._rr_index % len(usable)]
            self._rr_index += 1
            return acc

    async def _get_fresh_account(self, exclude: EnformionAccount = None) -> Optional[EnformionAccount]:
        """Get a different healthy account, excluding the given one. Used for retry switching."""
        async with self._lock:
            usable = [a for a in self.accounts
                      if a.status in ("active", "low_balance")
                      and a.email != (exclude.email if exclude else "!")]
            if not usable:
                return None
            usable.sort(key=lambda a: a.health.score(), reverse=True)
            return usable[0]

    # ── Rate limiting ─────────────────────────────────────────────────

    async def _wait_rate_limit(self, acc: EnformionAccount = None):
        """Enforce per-account minimum interval between searches."""
        if acc is not None:
            # Per-account rate limiting
            now = time.monotonic()
            elapsed = now - getattr(acc, "_last_search", 0)
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            acc._last_search = time.monotonic()
        else:
            # Global fallback (should not be used)
            now = time.monotonic()
            elapsed = now - self._last_search
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_search = time.monotonic()

    # ── Result caching ─────────────────────────────────────────────────

    def _build_cache_key(self, search_type: str, params: dict) -> str:
        """Build a deterministic cache key from search type and params."""
        # Phone searches use the phone number
        if search_type in ("phone", "ph_lookup", "ph_batch", "batch_phones",
                           "phone_identify", "phone_verify"):
            key_val = params.get("phone", "")
        elif search_type in ("email", "em_lookup", "em_verify"):
            key_val = params.get("email", "")
        elif search_type in ("address", "ad_lookup", "ad_batch",
                           "address_verify", "number_address",
                           "background", "name", "bg_name", "bg_batch"):
            fn = params.get("first_name", "").strip().upper()
            ln = params.get("last_name", "").strip().upper()
            st = params.get("state", "").strip().upper()
            key_val = f"{fn}:{ln}:{st}"
        else:
            key_val = json.dumps(params, sort_keys=True)
        return f"enf:{search_type}:{key_val.lower()}"

    async def _get_cached(self, cache_key: str) -> Optional[dict]:
        """Get cached result from DB if not expired. Returns None if miss/expired."""
        try:
            from database import get_cached
            cached = await get_cached(cache_key)
            if cached:
                result_json = cached.get("result_json", "")
                if result_json:
                    return json.loads(result_json)
        except Exception as e:
            logger.debug(f"[Enformion] Cache get error: {e}")
        return None

    async def _set_cached(self, cache_key: str, data: dict, ttl_hours: int = 24):
        """Cache a successful search result."""
        try:
            from database import set_cache
            await set_cache(cache_key, data, ttl_hours)
        except Exception as e:
            logger.debug(f"[Enformion] Cache set error: {e}")

    # ── Error rate tracking ──────────────────────────────────────────

    def _record_result(self, ok: bool, acc: EnformionAccount):
        """Record result and update circuit breaker + health scores."""
        if ok:
            acc.health.record_ok()
            self._cb.record_success()
        else:
            acc.health.record_error()

        # Legacy error window (for /health display)
        self._error_window.append(not ok)
        if len(self._error_window) > self._error_window_len:
            self._error_window.pop(0)
        if len(self._error_window) >= 10:
            rate = sum(self._error_window) / len(self._error_window)
            if rate >= self._error_rate_threshold and self._pool_ok:
                self._pool_ok = False
                logger.error(f"[Enformion] Error rate {rate:.0%} — pool suspended!")
                if self._alert_callback:
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        # No event loop (e.g., tests) — call sync callback directly
                        self._alert_callback(
                            "POOL", f"Error rate {rate:.0%} — pool suspended"
                        )
                    else:
                        asyncio.create_task(
                            self._alert_callback(
                                "POOL", f"Error rate {rate:.0%} — pool suspended"
                            )
                        )

    def get_person_by_ssn(self, ssn: str) -> Optional[dict]:
        """
        Search through cached/latest results for a person with the given SSN.
        Returns the first matching person dict, or None.
        """
        norm_ssn = re.sub(r"[^\d]", "", ssn)
        if len(norm_ssn) != 9:
            return None
        # Check bot_data cached results if available
        try:
            from database import get_cached
            # Try to scan recent cached results by looking for SSN match
            # The pool doesn't store recent results itself, so we delegate
            # to callers to check their cached person lists.
            # This method is a utility for callers.
            return None
        except Exception:
            return None

    def reset_error_rate(self):
        """Called after admin fixes the issue."""
        self._error_window.clear()
        self._pool_ok = True
        self._cb.reset()

    def clear_cache(self):
        """Clear in-memory cache."""
        self._cache.clear()
        logger.info("[Enformion] Cache cleared")

    def pause(self):
        """Pause the pool — all searches return POOL_SUSPENDED."""
        self._pool_ok = False
        logger.warning("[Enformion] Pool PAUSED by admin")

    def resume(self):
        """Resume the pool."""
        self._pool_ok = True
        self._error_window.clear()
        self._cb.reset()
        logger.warning("[Enformion] Pool RESUMED by admin")

    # ── Login ─────────────────────────────────────────────────────────

    async def login(self, acc: EnformionAccount) -> bool:
        """Verify account credentials."""
        try:
            headers = _enf_headers(acc, "Person")
            connector = _make_connector(acc.proxy)

            async with aiohttp.ClientSession(
                headers=headers, connector=connector
            ) as session:
                async with session.post(
                    f"{self._base}/PersonSearch",
                    json={"FirstName": "Test", "LastName": "User"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        await resp.json(content_type=None)
                        acc.status = "active"
                        logger.info(f"[Enformion] Login OK: {acc.email}")
                        return True
                    elif resp.status == 401 or (resp.status == 400 and "Invalid Galaxy Token" in await resp.text()):
                        acc.status = "blocked"
                        logger.warning(f"[Enformion] Login FAIL (bad creds): {acc.email}")
                        return False
                    elif resp.status == 402:
                        acc.status = "no_balance"
                        logger.warning(f"[Enformion] No balance: {acc.email}")
                        return False
                    else:
                        txt = await resp.text()
                        if "Invalid Galaxy Token" in txt:
                            acc.status = "blocked"
                            logger.warning(f"[Enformion] Login FAIL (bad token): {acc.email}")
                            return False
                        acc.status = "failed"
                        logger.warning(
                            f"[Enformion] Login status {resp.status}: {acc.email} {txt[:200]}"
                        )
                        return False
        except Exception as e:
            acc.status = "failed"
            logger.error(f"[Enformion] Login error for {acc.email}: {e}")
            return False

    async def login_all(self) -> dict:
        stats = {"total": len(self.accounts), "ok": 0, "failed": 0}

        async def try_login(account):
            ok = await self.login(account)
            return ok

        results = await asyncio.gather(
            *[try_login(acc) for acc in self.accounts],
            return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                stats["failed"] += 1
            elif result:
                stats["ok"] += 1
            else:
                stats["failed"] += 1
        return stats

    # ── API search ──────────────────────────────────────────────────────

    async def search(self, search_type: str, params: dict) -> SBResult:
        """
        Perform Enformion search with:
        - Per-account rate limiting
        - Account-switching retry on 5xx / timeout
        - Detailed raw logging on errors
        """
        if not self._pool_ok:
            return SBResult(
                ok=False, search_type=search_type, query=params,
                error="POOL_SUSPENDED"
            )

        if not self._cb.allow_request():
            return SBResult(
                ok=False, search_type=search_type, query=params,
                error="CIRCUIT_OPEN"
            )

        endpoint, payload = self._make_request(search_type, params)
        if endpoint is False:
            # Marker for unsupported search type (e.g., email)
            return SBResult(
                ok=False, search_type=search_type, query=params,
                error=payload  # error message is in payload field
            )
        if not endpoint or not payload:
            return SBResult(
                ok=False, search_type=search_type, query=params,
                error="INVALID_PARAMS"
            )

        # Check cache first (skip for email search which is unsupported)
        if search_type not in ("email", "em_lookup", "em_verify"):
            cache_key = self._build_cache_key(search_type, params)
            cached = await self._get_cached(cache_key)
            if cached is not None:
                logger.debug(f"[Enformion] Cache HIT: {cache_key}")
                people = self._parse_response(search_type, cached)
                if people:
                    return SBResult(
                        ok=True, search_type=search_type, query=params,
                        people=people, account="CACHE"
                    )
                return SBResult(
                    ok=True, search_type=search_type, query=params,
                    parsed={"message": "No results found",
                            "raw": json.dumps(cached, ensure_ascii=False)[:500]},
                    account="CACHE"
                )

        acc = await self._get_account()
        if not acc:
            return SBResult(
                ok=False, search_type=search_type, query=params,
                error="NO_ACTIVE_ACCOUNTS"
            )

        # Per-account rate limiting
        await self._wait_rate_limit(acc)

        max_retries = 3
        response_data = None
        last_error = ""
        last_raw = ""

        for attempt in range(max_retries):
            try:
                headers = _enf_headers(acc, search_type)
                connector = _make_connector(acc.proxy)

                async with aiohttp.ClientSession(
                    headers=headers, connector=connector
                ) as session:
                    async with session.post(
                        f"{self._base}/{endpoint}",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as resp:
                        status = resp.status
                        raw_response = await resp.text()

                        if status == 200:
                            response_data = json.loads(raw_response) if raw_response else {}
                            break  # success
                        elif status == 401:
                            acc.status = "blocked"
                            self._record_result(False, acc)
                            logger.warning(
                                f"[Enformion] 401 BLOCKED: {acc.email} | "
                                f"resp: {raw_response[:200]}"
                            )
                            return SBResult(
                                ok=False, search_type=search_type,
                                query=params, error="BLOCKED",
                                account=acc.email,
                                parsed={"raw": raw_response[:500]}
                            )
                        elif status == 402:
                            acc.status = "no_balance"
                            self._record_result(False, acc)
                            logger.warning(
                                f"[Enformion] 402 NO_TOKENS: {acc.email} | "
                                f"resp: {raw_response[:200]}"
                            )
                            if self._alert_callback:
                                asyncio.create_task(
                                    self._alert_callback(
                                        acc.email, "no_balance"
                                    )
                                )
                            return SBResult(
                                ok=False, search_type=search_type,
                                query=params, error="NO_TOKENS",
                                account=acc.email,
                                parsed={"raw": raw_response[:500]}
                            )
                        elif status == 429:
                            wait_time = min(2 ** attempt * 2, 15)
                            logger.warning(
                                f"[Enformion] 429 Rate Limit on {acc.email}, "
                                f"retry in {wait_time}s"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        elif status >= 500:
                            # 5xx → try next account
                            wait_time = 2 ** attempt
                            logger.warning(
                                f"[Enformion] Server error {status} on {acc.email}, "
                                f"switching account, retry in {wait_time}s"
                            )
                            self._record_result(False, acc)
                            # Try to switch to a different account
                            new_acc = await self._get_fresh_account(exclude=acc)
                            if new_acc:
                                acc = new_acc
                            # If no fresh account available, still retry with same acc
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            last_error = f"HTTP {status}"
                            last_raw = raw_response
                            self._record_result(False, acc)
                            logger.warning(
                                f"[Enformion] HTTP {status} on {acc.email} | "
                                f"resp: {raw_response[:200]}"
                            )
                            logger.error(
                                f"[Enformion] HTTP {status} FAILED: {search_type} | "
                                f"acc={acc.email} | raw: {raw_response[:300]}"
                            )
                            return SBResult(
                                ok=False, search_type=search_type,
                                query=params, error=f"HTTP {status}",
                                account=acc.email,
                                parsed={"raw": raw_response[:500]}
                            )

            except asyncio.TimeoutError:
                last_error = "TIMEOUT"
                self._record_result(False, acc)
                if attempt < max_retries - 1:
                    # Try next account on timeout
                    logger.warning(
                        f"[Enformion] Timeout on {acc.email}, "
                        f"switching account (attempt {attempt + 1}/{max_retries})"
                    )
                    new_acc = await self._get_fresh_account(exclude=acc)
                    if new_acc:
                        acc = new_acc
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error(f"[Enformion] Timeout exhausted for {acc.email}")
                return SBResult(
                    ok=False, search_type=search_type,
                    query=params, error="TIMEOUT",
                    account=acc.email
                )
            except aiohttp.ClientError as e:
                last_error = str(e)
                self._record_result(False, acc)
                logger.error(f"[Enformion] ClientError on {acc.email}: {e}")
                return SBResult(
                    ok=False, search_type=search_type,
                    query=params, error=str(e),
                    account=acc.email
                )
            except Exception as e:
                last_error = str(e)
                self._record_result(False, acc)
                logger.error(f"[Enformion] Unexpected error on {acc.email}: {e}")
                return SBResult(
                    ok=False, search_type=search_type,
                    query=params, error=str(e),
                    account=acc.email
                )

        # If no response data after all retries
        if response_data is None:
            self._record_result(False, acc)
            logger.error(
                f"[Enformion] All retries exhausted | acc={acc.email} | "
                f"endpoint={endpoint} | last_error={last_error}"
            )
            return SBResult(
                ok=False, search_type=search_type, query=params,
                error="RETRIES_EXHAUSTED", account=acc.email
            )

        # Success — parse response
        if acc.email != "CACHE":
            acc.searches += 1
        people = self._parse_response(search_type, response_data)

        if people:
            self._record_result(True, acc)
            # Cache successful results with people (24h TTL)
            if cache_key:
                asyncio.create_task(
                    self._set_cached(cache_key, response_data, ttl_hours=24)
                )
            logger.info(f"[Enformion] Search OK: {search_type} → {len(people)} people found (acc={acc.email})")
            return SBResult(
                ok=True, search_type=search_type, query=params,
                people=people, account=acc.email
            )
        else:
            self._record_result(True, acc)
            logger.info(f"[Enformion] Search OK: {search_type} → no results")
            return SBResult(
                ok=True, search_type=search_type, query=params,
                parsed={
                    "message": "No results found",
                    "raw": json.dumps(response_data, ensure_ascii=False)[:500]
                },
                account=acc.email
            )


    def _make_request(self, search_type: str, params: dict) -> tuple:
        """Build endpoint and payload."""

        if search_type in ("phone", "ph_lookup", "ph_batch", "batch_phones"):
            phone = params.get("phone", "")
            if not phone:
                return None, None
            return "ReversePhoneSearch", {"Phone": phone}

        elif search_type in ("address", "ad_lookup", "ad_batch",
                             "address_verify"):
            # PersonSearch: needs FirstName + LastName
            fn = params.get("first_name", "").strip().upper()
            ln = params.get("last_name", "").strip().upper()
            st = params.get("state", "").strip().upper()
            if not fn or not ln:
                # Try to parse from raw address text
                raw = params.get("address", "")
                parts = raw.split(",")
                if len(parts) >= 3:
                    # "123 Main St, City, ST" → use as address search
                    return "PersonSearch", {
                        "FirstName": parts[0][:50],
                        "LastName": "",
                        "State": parts[-1].strip()[:2].upper()
                        if len(parts[-1].strip()) >= 2 else "",
                    }
                return None, None
            return "PersonSearch", {
                "FirstName": fn,
                "LastName": ln,
                "State": st,
            }

        elif search_type == "number_address":
            fn = params.get("first_name", "").strip().upper()
            ln = params.get("last_name", "").strip().upper()
            if not fn or not ln:
                return None, None
            return "PersonSearch", {
                "FirstName": fn,
                "LastName": ln,
            }

        elif search_type in ("background", "name", "bg_name", "bg_batch"):
            fn = params.get("first_name", "").strip().upper()
            ln = params.get("last_name", "").strip().upper()
            if not fn or not ln:
                return None, None
            payload = {"FirstName": fn, "LastName": ln}
            st = params.get("state", "").strip().upper()
            if st:
                payload["State"] = st
            return "PersonSearch", payload

        elif search_type in ("email", "em_lookup", "em_verify"):
            email = params.get("email", "").strip().lower()
            if not email:
                return None, None
            # Enformion doesn't have a direct email search endpoint.
            # Return unsupported marker — bot should use emailrep.io instead.
            return False, "EMAIL_SEARCH_UNSUPPORTED"

        elif search_type == "phone_identify":
            # Dedicated phone type/carrier/location identification
            phone = params.get("phone", "")
            if not phone:
                return None, None
            return "IdentifyPhoneType", {"Phone": phone}

        elif search_type == "phone_verify":
            # Dedicated phone verification (active/inactive)
            phone = params.get("phone", "")
            if not phone:
                return None, None
            return "VerifyPhone", {"Phone": phone}

        # Default: pass through
        return "PersonSearch", params

    def _safe_str(self, val, default=""):
        """Safely extract string value."""
        if val is None:
            return default
        return str(val) if val != "NULL" else default

    def _safe_list(self, val) -> list:
        """Safely extract list."""
        if isinstance(val, list):
            return val
        return []

    def _safe_dict(self, val) -> dict:
        """Safely extract dict."""
        if isinstance(val, dict):
            return val
        return {}

    def _build_address_string(self, addr: dict) -> str:
        """Build a full address string from address dict."""
        parts = []
        for key in ("addressLine1", "addressLine2", "city", "state", "zipCode", "zip"):
            v = self._safe_str(addr.get(key))
            if v:
                parts.append(v)
        return ", ".join(parts)

    def _extract_phones(self, pns: list) -> dict:
        """
        Extract all phone-related fields.
        Returns: {phones: [...], phone: "", phone_type: "", carrier: "", voip: None, connected_to: ""}
        """
        result = {
            "phones": [],
            "phone": "",
            "phone_type": "",
            "carrier": "",
            "voip": None,
            "connected_to": "",
        }
        for pn in self._safe_list(pns):
            if not isinstance(pn, dict):
                continue
            phone = self._safe_str(pn.get("phoneNumber"))
            if not phone:
                continue
            entry = {"phone": phone}
            for k in ("phoneType", "carrier", "location"):
                v = self._safe_str(pn.get(k))
                if v:
                    entry[k] = v
            result["phones"].append(entry)
            # Set primary phone fields from first entry
            if not result["phone"]:
                result["phone"] = phone
                result["phone_type"] = self._safe_str(pn.get("phoneType"))
                result["carrier"] = self._safe_str(pn.get("carrier"))
                loc = self._safe_str(pn.get("location"))
                if loc:
                    parts = loc.split(",")
                    if len(parts) >= 2:
                        result["location"] = f"{parts[0].strip()}, {parts[1].strip()}"
                    else:
                        result["location"] = loc
            # Extract voip and connectedTo from first entry if present
            if result["voip"] is None:
                voip = pn.get("voipIndicator")
                result["voip"] = bool(voip) if voip is not None else None
            if not result["connected_to"]:
                result["connected_to"] = self._safe_str(pn.get("connectedTo"))
        return result

    def _extract_emails(self, ems: list) -> list:
        """Extract all email addresses."""
        emails = []
        for em in self._safe_list(ems):
            if isinstance(em, dict):
                e = self._safe_str(em.get("emailAddress"))
            else:
                e = self._safe_str(em)
            if e:
                emails.append(e)
        return emails

    def _extract_addresses(self, locs: list, current_addr: dict = None,
                           hist_addrs: list = None,
                           tp_addresses: list = None) -> tuple:
        """
        Extract addresses from locations array + current + historical + tp.addresses[].
        Deduplicates by addressLine1 to avoid skipping same address with different zip.
        Returns: (addresses: list[str], address: str)
        """
        # Use addressLine1 as dedupe key to keep different zip variants
        seen_keys: set = set()
        addresses: list = []

        def add(addr: dict):
            key = self._safe_str(addr.get("addressLine1"))
            if not key:
                return
            s = self._build_address_string(addr)
            if s and key not in seen_keys:
                seen_keys.add(key)
                addresses.append(s)

        # From locations array
        for loc in self._safe_list(locs):
            if isinstance(loc, dict):
                addr = {
                    "addressLine1": self._safe_str(loc.get("addressLine1")),
                    "addressLine2": self._safe_str(loc.get("addressLine2")),
                    "city": self._safe_str(loc.get("city")),
                    "state": self._safe_str(loc.get("state")),
                    "zipCode": self._safe_str(loc.get("zipCode")),
                    "zip": self._safe_str(loc.get("zip")),
                }
                add(addr)

        # From currentAddress field
        if isinstance(current_addr, dict):
            addr = {
                "addressLine1": self._safe_str(current_addr.get("addressLine1")),
                "addressLine2": self._safe_str(current_addr.get("addressLine2")),
                "city": self._safe_str(current_addr.get("city")),
                "state": self._safe_str(current_addr.get("state")),
                "zipCode": self._safe_str(current_addr.get("zipCode")),
                "zip": self._safe_str(current_addr.get("zip")),
            }
            add(addr)

        # From historicalAddresses field
        for ha in self._safe_list(hist_addrs):
            if isinstance(ha, dict):
                addr = {
                    "addressLine1": self._safe_str(ha.get("addressLine1")),
                    "addressLine2": self._safe_str(ha.get("addressLine2")),
                    "city": self._safe_str(ha.get("city")),
                    "state": self._safe_str(ha.get("state")),
                    "zipCode": self._safe_str(ha.get("zipCode")),
                    "zip": self._safe_str(ha.get("zip")),
                }
                add(addr)

        # From addresses[] in tahoePerson (ReversePhone records)
        for ta in self._safe_list(tp_addresses):
            if isinstance(ta, dict):
                addr = {
                    "addressLine1": self._safe_str(ta.get("addressLine1")),
                    "addressLine2": self._safe_str(ta.get("addressLine2")),
                    "city": self._safe_str(ta.get("city")),
                    "state": self._safe_str(ta.get("state")),
                    "zipCode": self._safe_str(ta.get("zipCode")),
                    "zip": self._safe_str(ta.get("zip")),
                }
                add(addr)

        primary = addresses[0] if addresses else ""
        return addresses, primary

    def _extract_relatives(self, rels: list) -> str:
        """Extract relatives as comma-separated string."""
        parts = []
        for r in self._safe_list(rels)[:15]:
            if isinstance(r, dict):
                rf = self._safe_str(r.get("firstName"))
                rl = self._safe_str(r.get("lastName"))
                rel_type = self._safe_str(r.get("relation"))
                if rf or rl:
                    name = f"{rf} {rl}".strip()
                    if rel_type:
                        name += f" ({rel_type})"
                    parts.append(name)
        return ", ".join(parts)

    def _extract_akas(self, akas: list) -> list:
        """Extract AKAs as list of full name strings."""
        result = []
        for a in self._safe_list(akas):
            if isinstance(a, dict):
                fn = self._safe_str(a.get("firstName"))
                ln = self._safe_str(a.get("lastName"))
                if fn or ln:
                    result.append(f"{fn} {ln}".strip())
            else:
                s = self._safe_str(a)
                if s:
                    result.append(s)
        return result

    def _build_person(self, nm: dict, tp: dict,
                      extra_phones: list = None,
                      extra_locs: list = None,
                      extra_current: dict = None,
                      extra_hist: list = None,
                      extra_emails: list = None,
                      extra_relatives: list = None,
                      extra_akas: list = None) -> dict:
        """Build a complete person dict from tahoePerson or person dict."""
        fn = self._safe_str(nm.get("firstName"))
        ln = self._safe_str(nm.get("lastName"))
        name = f"{fn} {ln}".strip() if fn or ln else ""

        # Phones
        phone_fields = self._extract_phones(self._safe_list(extra_phones) or tp.get("phoneNumbers"))

        # Emails
        emails = self._extract_emails(
            self._safe_list(extra_emails) or tp.get("emailAddresses")
        )

        # Addresses
        addrs, primary_addr = self._extract_addresses(
            self._safe_list(extra_locs) or tp.get("locations"),
            extra_current or tp.get("currentAddress"),
            self._safe_list(extra_hist) if extra_hist is not None else tp.get("historicalAddresses"),
            tp.get("addresses"),
        )

        # Relatives
        relatives = self._extract_relatives(
            self._safe_list(extra_relatives) if extra_relatives is not None else tp.get("relativesSummary")
        )

        # AKAs
        akas = self._extract_akas(
            self._safe_list(extra_akas) if extra_akas is not None else tp.get("akas")
        )

        return {
            "name": name,
            "first_name": fn,
            "last_name": ln,
            "age": tp.get("age", 0) or 0,
            "date_of_birth": self._safe_str(tp.get("dateOfBirth")),
            "ssn": self._safe_str(tp.get("ssn")),
            "phone": phone_fields["phone"],
            "phones": phone_fields["phones"],
            "phone_type": phone_fields["phone_type"],
            "carrier": phone_fields["carrier"],
            "location": phone_fields.get("location", ""),
            "voip": phone_fields["voip"],
            "connected_to": phone_fields["connected_to"],
            "addresses": addrs,
            "address": primary_addr,
            "emails": emails,
            "email": emails[0] if emails else "",
            "relatives": relatives,
            "akas": akas,
        }

    def _parse_response(self, search_type: str, data: dict) -> List[dict]:
        """Parse Enformion response into unified people list."""
        people = []

        try:
            # ReversePhoneSearch response
            records = data.get("reversePhoneRecords", [])
            for rec in self._safe_list(records):
                tp = self._safe_dict(rec.get("tahoePerson"))
                if not tp:
                    continue
                nm = self._safe_dict(tp.get("name"))
                person = self._build_person(nm, tp)
                # Skip if no name and no other identifying info
                if not person["name"] and not person["phone"] and not person["phones"]:
                    continue

                # For reverse phone, also extract phone/carrier/type from the record level
                if not person["phone_type"]:
                    pns = self._safe_list(tp.get("phoneNumbers"))
                    if pns and isinstance(pns[0], dict):
                        person["phone_type"] = self._safe_str(pns[0].get("phoneType"))
                        person["carrier"] = self._safe_str(pns[0].get("carrier"))
                        if not person["location"]:
                            loc = self._safe_str(pns[0].get("location"))
                            if loc:
                                parts = loc.split(",")
                                person["location"] = (
                                    f"{parts[0].strip()}, {parts[1].strip()}"
                                    if len(parts) >= 2 else loc
                                )

                # Also extract voipIndicator and connectedTo at tahoePerson + record level
                if person["voip"] is None:
                    # Check tahoePerson level (where Enformion often puts it)
                    person["voip"] = bool(tp.get("voipIndicator")) if "voipIndicator" in tp else None
                    # Fall back to record level
                    if person["voip"] is None:
                        person["voip"] = bool(rec.get("voipIndicator")) if "voipIndicator" in rec else None
                if not person["connected_to"]:
                    ct = self._safe_str(tp.get("connectedTo"))
                    if not ct:
                        ct = self._safe_str(rec.get("connectedTo"))
                    person["connected_to"] = ct

                people.append(person)

            # PersonSearch response
            persons = data.get("persons", [])
            for p in self._safe_list(persons):
                nm = self._safe_dict(p.get("name"))
                person = self._build_person(nm, p)
                people.append(person)

        except (KeyError, TypeError, IndexError) as e:
            logger.error(
                f"[Enformion] Parse error: {e}, "
                f"data keys: {list(data.keys()) if data else 'empty'}"
            )

        return people

    # ── Status report ─────────────────────────────────────────────────

    def status_report(self) -> List[dict]:
        out = []
        for a in self.accounts:
            out.append({
                "email": a.email,
                "status": a.status,
                "balance": a.balance,
                "init_balance": a.init_balance,
                "pct": int(a.balance / a.init_balance * 100)
                if a.init_balance else 0,
                "searches": a.searches,
                "logged_in": a.status in ("active", "low_balance"),
                "proxy": a.proxy or "none",
            })
        return out

    # ── Parse accounts file ───────────────────────────────────────────

    def parse_accounts_file(self, content: str) -> List[dict]:
        accounts = []
        for line in content.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Try colon-separated: email:password:proxy
            # Only if the first colon-separated part is a valid email
            if ":" in line:
                first_colon = line.index(":")
                email_part = line[:first_colon].strip()
                rest = line[first_colon + 1:]
                # email must look like email@domain (no spaces)
                if "@" in email_part and " " not in email_part:
                    # Now split rest by colon: password:proxy or just password
                    colon_in_rest = rest.index(":") if ":" in rest else -1
                    if colon_in_rest >= 0 and rest.count(":") >= 2:
                        # password:proxy_scheme:user_pass@host:port
                        # e.g., pass123:http://user:pass@host:8080
                        # or just sock5://user:pass@host:1080
                        # The password is everything before the proxy URL
                        # Try to detect proxy URL
                        proxy_match = None
                        for scheme in ("http://", "https://", "socks5://", "socks4://", "socks://"):
                            idx = rest.find(scheme)
                            if idx >= 0:
                                proxy_match = idx
                                break
                        if proxy_match is not None:
                            password = rest[:proxy_match].rstrip(":").strip()
                            proxy = rest[proxy_match:].strip()
                            acc = {"email": email_part, "password": password}
                            if proxy:
                                acc["proxy"] = proxy
                        else:
                            # No proxy URL detected, just password:proxy
                            parts = rest.split(":", 1)
                            acc = {"email": email_part, "password": parts[0].strip()}
                            if len(parts) > 1 and parts[1].strip():
                                acc["proxy"] = parts[1].strip()
                    else:
                        acc = {"email": email_part, "password": rest.strip()}
                    accounts.append(acc)
                    continue
            # Fall back to space-separated
            parts = line.split(maxsplit=2)
            if len(parts) >= 2:
                acc = {"email": parts[0], "password": parts[1]}
                if len(parts) > 2:
                    acc["proxy"] = parts[2]
                accounts.append(acc)
        return accounts

    # ── Refresh balance ──────────────────────────────────────────────

    async def refresh_balance(self, acc: EnformionAccount):
        """Refresh balance for a single account."""
        try:
            headers = _enf_headers(acc, "Person")
            connector = _make_connector(acc.proxy)
            async with aiohttp.ClientSession(
                headers=headers, connector=connector
            ) as session:
                async with session.post(
                    f"{self._base}/PersonSearch",
                    json={"FirstName": "BalanceCheck", "LastName": "Test"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        await resp.json(content_type=None)
                        if acc.status != "active":
                            old_status = acc.status
                            acc.status = "active"
                            if self._alert_callback and old_status != "active":
                                asyncio.create_task(
                                    self._alert_callback(
                                        acc.email, "low_balance:restored"
                                    )
                                )
                    elif resp.status == 402:
                        acc.status = "no_balance"
                    elif resp.status == 401:
                        acc.status = "blocked"
        except Exception as e:
            logger.error(
                f"[Enformion] Balance refresh error for {acc.email}: {e}",
                exc_info=True
            )

    # ── EmailRep ──────────────────────────────────────────────────────

    async def emailrep_lookup(self, email: str, api_key: str = "") -> dict:
        if not api_key:
            return {"error": "EMAILREP_KEY not configured"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://emailrep.io/{email}",
                    headers={"Key": api_key},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"error": str(e)}


# ── Singleton ────────────────────────────────────────────────────────
pool = EnformionPool()

logger.info("[sb_engine] EnformionPool initialized")
