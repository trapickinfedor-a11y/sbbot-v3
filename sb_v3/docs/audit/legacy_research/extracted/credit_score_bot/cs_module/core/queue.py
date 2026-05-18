"""
core/queue.py — Job queue and worker pool manager.

WorkerPool manages 5 async workers, each with its own:
  - ProxyManager (rotates IP every 3 attempts)
  - FingerprintRotator (new profile per request)
  - Shared asyncio.Queue for jobs
  - Separate result queue

Usage from Telegram bot:
    pool = WorkerPool(config)
    await pool.start()

    job = JobRequest(...)
    await pool.submit(job)

    # Results come back via callback or result queue
    result = await pool.get_result()

    await pool.stop()
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable
from aiogram import Bot

from ..bot_interface.models import JobRequest, JobResult, JobStatus
from ..proxy.manager import ProxyPool
from ..workers.cs_worker import CreditScoreWorker

logger = logging.getLogger(__name__)

NUM_WORKERS = 5


class WorkerPoolConfig:
    """Configuration for the worker pool."""

    def __init__(
        self,
        # 9proxy settings
        proxy_host: str,
        proxy_port: int,
        proxy_username: str,
        proxy_password: str,
        proxy_type: str = "http",
        proxy_country: str = "us",
        rotate_every: int = 3,

        # Worker settings
        num_workers: int = NUM_WORKERS,
        headless: bool = True,
        screenshot_dir: str = "/tmp/cs_screenshots",

        # Result callback (optional)
        on_result: Optional[Callable[[JobResult], Awaitable[None]]] = None,
    ):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.proxy_type = proxy_type
        self.proxy_country = proxy_country
        self.rotate_every = rotate_every
        self.num_workers = num_workers
        self.headless = headless
        self.screenshot_dir = screenshot_dir
        self.on_result = on_result


class WorkerPool:
    def __init__(self, config: WorkerPoolConfig, bot_instance: Bot = None):
    """
    Manages a pool of CreditScoreWorker instances.
    Accepts JobRequest items and dispatches them to available workers.
    """

    def __init__(self, config: WorkerPoolConfig):
        self.config = config
        self.bot_instance = bot_instance
        self._job_queue: asyncio.Queue = asyncio.Queue()
        self._result_queue: asyncio.Queue = asyncio.Queue()
        self._workers: list = []
        self._tasks: list = []
        self._result_dispatcher_task: Optional[asyncio.Task] = None
        self._running = False

        # Create proxy pool (one ProxyManager per worker)
        self._proxy_pool = ProxyPool(
            host=config.proxy_host,
            port=config.proxy_port,
            username=config.proxy_username,
            password=config.proxy_password,
            proxy_type=config.proxy_type,
            num_workers=config.num_workers,
            rotate_every=config.rotate_every,
            country=config.proxy_country,
        )

    async def start(self):
        """Start all workers and the result dispatcher."""
        if self._running:
            return
        self._running = True

        # Verify proxies
        logger.info("[WorkerPool] Verifying proxies...")
        results = await self._proxy_pool.verify_all()
        for wid, res in results.items():
            if isinstance(res, dict) and res.get("ok"):
                logger.info(
                    f"[WorkerPool] Worker {wid} proxy OK: "
                    f"{res.get('ip')} ({res.get('country')})"
                )
            else:
                logger.warning(f"[WorkerPool] Worker {wid} proxy FAILED: {res}")

        # Create and start workers
        for wid in range(self.config.num_workers):
            worker = CreditScoreWorker(
                worker_id=wid,
                job_queue=self._job_queue,
                result_queue=self._result_queue,
                proxy_manager=self._proxy_pool.get(wid),
                bot=self.bot_instance,
                screenshot_dir=self.config.screenshot_dir,
                headless=self.config.headless,
            )
            self._workers.append(worker)
            task = asyncio.create_task(worker.run(), name=f"worker_{wid}")
            self._tasks.append(task)

        # Start result dispatcher if callback provided
        if self.config.on_result:
            self._result_dispatcher_task = asyncio.create_task(
                self._dispatch_results(), name="result_dispatcher"
            )

        logger.info(f"[WorkerPool] Started {self.config.num_workers} workers")

    async def stop(self):
        """Gracefully stop all workers."""
        if not self._running:
            return
        self._running = False

        # Send shutdown sentinels (one per worker)
        for _ in range(self.config.num_workers):
            await self._job_queue.put(None)

        # Wait for all workers to finish
        await asyncio.gather(*self._tasks, return_exceptions=True)

        if self._result_dispatcher_task:
            self._result_dispatcher_task.cancel()

        logger.info("[WorkerPool] All workers stopped")

    async def submit(self, job: JobRequest) -> str:
        """
        Submit a job to the queue.
        Returns the job_id for tracking.
        """
        if not self._running:
            raise RuntimeError("WorkerPool is not running. Call start() first.")
        await self._job_queue.put(job)
        logger.info(f"[WorkerPool] Job {job.job_id} queued for {job.display_name()}")
        return job.job_id

    async def get_result(self, timeout: Optional[float] = None):
        """
        Get the next result from the result queue.
        Returns None on timeout.
        """
        try:
            return await asyncio.wait_for(self._result_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    @property
    def queue_size(self) -> int:
        return self._job_queue.qsize()

    @property
    def result_queue_size(self) -> int:
        return self._result_queue.qsize()

    async def _dispatch_results(self):
        """Background task that calls on_result callback for each result."""
        while True:
            result = await self._result_queue.get()
            try:
                await self.config.on_result(result)
            except Exception as e:
                logger.error(f"[WorkerPool] Result callback error: {e}")
            self._result_queue.task_done()
