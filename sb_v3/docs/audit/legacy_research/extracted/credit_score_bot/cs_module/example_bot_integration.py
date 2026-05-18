"""
example_bot_integration.py — Example of how to integrate cs_module into a Telegram bot.

This is a REFERENCE EXAMPLE only — not a runnable bot.
Shows the exact API calls needed to integrate the module.

Bot flow:
  1. User sends applicant data (name, address, DOB)
  2. Bot creates JobRequest and submits to pool
  3. Worker processes the request asynchronously
  4. If SSN needed: bot asks user, user replies, bot calls ssn_flow.provide_ssn()
  5. Result arrives via on_result callback
  6. Bot sends credit score back to user
"""

import asyncio
import logging
from cs_module import WorkerPool, WorkerPoolConfig, JobRequest, JobResult, JobStatus, ssn_flow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step 1: Configure the worker pool
# ---------------------------------------------------------------------------

async def on_result(result: JobResult):
    """
    Called by the worker pool when a job completes.
    In a real bot, use bot.send_message() here.
    """
    if result.status == JobStatus.WAITING_SSN:
        # Ask user for SSN
        print(f"[Bot → User {result.telegram_chat_id}] Please provide your SSN (XXX-XX-XXXX):")
        # Store job_id so we know which job to resume when user replies
        # pending_ssn_jobs[result.telegram_chat_id] = result.job_id

    elif result.status == JobStatus.SUCCESS:
        print(
            f"[Bot → User {result.telegram_chat_id}] "
            f"✅ Credit Score: {result.credit_score} "
            f"(source: {result.source}, "
            f"worker: #{result.worker_id}, "
            f"time: {result.duration_seconds}s)"
        )

    elif result.status == JobStatus.FAILED:
        print(
            f"[Bot → User {result.telegram_chat_id}] "
            f"❌ Failed to get credit score: {result.error}"
        )


config = WorkerPoolConfig(
    # 9proxy credentials
    proxy_host="gate.9proxy.com",
    proxy_port=7777,
    proxy_username="YOUR_9PROXY_USERNAME",
    proxy_password="YOUR_9PROXY_PASSWORD",
    proxy_type="http",
    proxy_country="us",
    rotate_every=3,          # Rotate IP every 3 attempts per worker

    # Worker settings
    num_workers=5,
    headless=True,
    screenshot_dir="/tmp/cs_screenshots",

    # Result callback
    on_result=on_result,
)

pool = WorkerPool(config)


# ---------------------------------------------------------------------------
# Step 2: Bot command handler — /check
# ---------------------------------------------------------------------------

async def handle_check_command(
    chat_id: int,
    message_id: int,
    user_id: int,
    first_name: str,
    last_name: str,
    street: str,
    city: str,
    state: str,
    zip_code: str,
    dob: str,
    annual_income: str = "32000",
    ssn: str = None,
):
    """
    Called when user sends applicant data to the bot.
    Creates and submits a JobRequest.
    """
    job = JobRequest(
        telegram_chat_id=chat_id,
        telegram_message_id=message_id,
        telegram_user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        street=street,
        city=city,
        state=state,
        zip_code=zip_code,
        dob=dob,
        annual_income=annual_income,
        ssn=ssn,
    )
    job_id = await pool.submit(job)
    print(f"[Bot] Job {job_id} submitted for {first_name} {last_name}")
    return job_id


# ---------------------------------------------------------------------------
# Step 3: SSN reply handler
# ---------------------------------------------------------------------------

async def handle_ssn_reply(job_id: str, raw_ssn: str) -> bool:
    """
    Called when user replies with their SSN.
    Returns True if SSN was valid and job was resumed.
    """
    success = ssn_flow.provide_ssn(job_id, raw_ssn)
    if not success:
        print("[Bot → User] Invalid SSN format. Please use XXX-XX-XXXX format.")
    return success


# ---------------------------------------------------------------------------
# Step 4: Startup / shutdown
# ---------------------------------------------------------------------------

async def startup():
    """Call this when the bot starts."""
    await pool.start()
    logger.info("Credit score worker pool started")


async def shutdown():
    """Call this when the bot stops."""
    await pool.stop()
    logger.info("Credit score worker pool stopped")


# ---------------------------------------------------------------------------
# Demo run
# ---------------------------------------------------------------------------

async def demo():
    await startup()

    # Submit a test job
    job_id = await handle_check_command(
        chat_id=123456789,
        message_id=1,
        user_id=987654321,
        first_name="Annette",
        last_name="Solano",
        street="10047 E S6",
        city="Littlerock",
        state="CA",
        zip_code="93543",
        dob="01/26/1991",
        annual_income="35000",
    )
    print(f"Submitted job: {job_id}")

    # Wait for result (up to 5 minutes)
    result = await pool.get_result(timeout=300)
    if result:
        print(f"Result: {result.summary()}")
    else:
        print("Timeout waiting for result")

    await shutdown()


if __name__ == "__main__":
    asyncio.run(demo())
