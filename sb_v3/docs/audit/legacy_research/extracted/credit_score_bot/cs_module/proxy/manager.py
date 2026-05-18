"""
proxy/manager.py — 9proxy rotation manager (v2).

New Logic:
- IP rotates after N successful attempts.
- IP rotates immediately after 1 failed attempt.
"""

import random
import string
import asyncio
import aiohttp
import logging

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    Manages proxy credentials and rotation for a single worker.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        proxy_type: str = "http",
        rotate_on_success: int = 3,
        country: str = "us",
    ):
        self.host = host
        self.port = port
        self.base_username = username
        self.password = password
        self.proxy_type = proxy_type
        self.rotate_on_success_count = rotate_on_success
        self.country = country

        self._successful_attempts = 0
        self._current_session_id: str = self._new_session_id()

    def get_proxy_url(self) -> str:
        """Return the full proxy URL for the current session."""
        return self._build_url()

    def on_success(self):
        """Called by the worker after a successful job."""
        self._successful_attempts += 1
        if self._successful_attempts >= self.rotate_on_success_count:
            logger.info(
                f"[ProxyManager] Reached {self._successful_attempts} successful attempts. Rotating IP."
            )
            self._rotate()

    def on_failure(self):
        """Called by the worker after a failed job."""
        logger.info("[ProxyManager] Job failed. Forcing IP rotation.")
        self._rotate()

    @property
    def current_ip_label(self) -> str:
        return f"session:{self._current_session_id}"

    def _rotate(self):
        """Force an immediate IP rotation and reset success counter."""
        old_session = self._current_session_id
        self._current_session_id = self._new_session_id()
        self._successful_attempts = 0
        logger.info(f"[ProxyManager] IP rotated: {old_session} → {self._current_session_id}")

    def _build_url(self) -> str:
        user = f"{self.base_username}-country-{self.country}-session-{self._current_session_id}"
        scheme = self.proxy_type
        return f"{scheme}://{user}:{self.password}@{self.host}:{self.port}"

    @staticmethod
    def _new_session_id(length: int = 8) -> str:
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    async def verify(self) -> dict:
        """Check that the proxy is working."""
        proxy_url = self._build_url()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://ipinfo.io/json",
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    data = await resp.json()
                    return {"ok": True, "ip": data.get("ip"), "country": data.get("country")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

class ProxyPool:
    """Pool of ProxyManager instances — one per worker."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        proxy_type: str = "http",
        num_workers: int = 3,
        rotate_on_success: int = 3,
        country: str = "us",
    ):
        self._managers: dict[int, ProxyManager] = {
            wid: ProxyManager(
                host=host,
                port=port,
                username=username,
                password=password,
                proxy_type=proxy_type,
                rotate_on_success=rotate_on_success,
                country=country,
            )
            for wid in range(num_workers)
        }

    def get(self, worker_id: int) -> ProxyManager:
        return self._managers[worker_id]

    async def verify_all(self) -> dict[int, dict]:
        tasks = {wid: mgr.verify() for wid, mgr in self._managers.items()}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return dict(zip(tasks.keys(), results))
