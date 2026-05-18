"""
cs_module — Credit Score Parser Module for Telegram Bot.

Public API:
    from cs_module import WorkerPool, WorkerPoolConfig, JobRequest, JobResult, JobStatus, ssn_flow

Quick start:
    config = WorkerPoolConfig(
        proxy_host="gate.9proxy.com",
        proxy_port=7777,
        proxy_username="your_user",
        proxy_password="your_pass",
        on_result=my_result_handler,
    )
    pool = WorkerPool(config)
    await pool.start()

    job = JobRequest(
        telegram_chat_id=123456,
        telegram_message_id=1,
        telegram_user_id=789,
        first_name="John",
        last_name="Doe",
        street="123 Main St",
        city="Los Angeles",
        state="CA",
        zip_code="90001",
        dob="01/15/1990",
        annual_income="45000",
    )
    await pool.submit(job)
"""

from .core.queue import WorkerPool, WorkerPoolConfig
from .bot_interface.models import JobRequest, JobResult, JobStatus
from .bot_interface.ssn_flow import ssn_flow

__all__ = [
    "WorkerPool",
    "WorkerPoolConfig",
    "JobRequest",
    "JobResult",
    "JobStatus",
    "ssn_flow",
]

__version__ = "1.0.0"
