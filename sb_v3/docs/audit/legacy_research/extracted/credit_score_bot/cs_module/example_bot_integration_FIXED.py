# example_bot_integration_FIXED.py

"""
Example of how to integrate cs_module into a Telegram bot
WITH THE ASYNCIO POLICY FIX.
"""

# ---------------------------------------------------------------------------
# STEP 1: Apply the policy fix at the VERY TOP of your entry point file
# ---------------------------------------------------------------------------
# Before importing asyncio, aiogram, or any other async library.

from cs_module.policy_fix import install_uvloop_policy

install_uvloop_policy()

# Now you can import other libraries
import asyncio
import logging
from cs_module import WorkerPool, WorkerPoolConfig, JobRequest, JobResult, JobStatus, ssn_flow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step 2: Configure the worker pool (no changes here)
# ---------------------------------------------------------------------------

async def on_result(result: JobResult):
    """
    Called by the worker pool when a job completes.
    In a real bot, use bot.send_message() here.
    """
    if result.status == JobStatus.WAITING_SSN:
        print(f"[Bot → User {result.telegram_chat_id}] Please provide your SSN (XXX-XX-XXXX):")
    elif result.status == JobStatus.SUCCESS:
        print(
            f"[Bot → User {result.telegram_chat_id}] "
            f"✅ Credit Score: {result.credit_score} "
            f"(source: {result.source}, worker: #{result.worker_id})"
        )
    elif result.status == JobStatus.FAILED:
        print(
            f"[Bot → User {result.telegram_chat_id}] "
            f"❌ Failed to get credit score: {result.error}"
        )


config = WorkerPoolConfig(
    proxy_host="gate.9proxy.com",
    proxy_port=7777,
    proxy_username="YOUR_9PROXY_USERNAME",
    proxy_password="YOUR_9PROXY_PASSWORD",
    on_result=on_result,
)

pool = WorkerPool(config)


# ---------------------------------------------------------------------------
# Step 3: Main application logic (no changes here)
# ---------------------------------------------------------------------------

async def main():
    """Main application entry point."""
    print("[Main] Starting worker pool...")
    await pool.start()

    # Simulate a bot command
    job = JobRequest(
        telegram_chat_id=12345,
        telegram_message_id=1,
        telegram_user_id=111,
        first_name="Annette",
        last_name="Solano",
        street="10047 E S6",
        city="Littlerock",
        state="CA",
        zip_code="93543",
        dob="01/26/1991",
    )
    print(f"[Main] Submitting job for {job.display_name()}...")
    await pool.submit(job)

    # In a real app, the loop would run forever.
    # Here, we just wait a bit for the result to come in.
    await asyncio.sleep(120) # Wait for up to 2 minutes

    print("[Main] Shutting down worker pool...")
    await pool.stop()


if __name__ == "__main__":
    # asyncio.run() will now use the uvloop because the policy was set.
    asyncio.run(main())
