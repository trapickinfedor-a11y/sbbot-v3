# policy_fix.py

"""
This module provides a targeted fix for the asyncio policy conflict
that occurs when aiogram (with uvloop) and Playwright are used together
in a process where the event loop is created before the policy is set.

Problem:
  1. Main app starts with a standard asyncio loop.
  2. aiogram is imported, which installs uvloop's policy globally.
  3. Playwright (in a worker) tries to create a subprocess.
  4. It calls get_child_watcher(), which fails because the running
     loop (standard) is incompatible with the new global policy (uvloop).

Solution:
  Install the uvloop policy *before* any asyncio loop is created.
  This function should be called at the very top of your application's
  entry point (e.g., run_local.py).
"""

import asyncio
import sys

def install_uvloop_policy():
    """
    Checks for uvloop and installs it as the default asyncio event loop policy.
    This ensures that any new asyncio event loop will be a uvloop, which is
    compatible with both aiogram and Playwright's subprocess requirements.
    
    Call this function ONCE at the very beginning of your application entry point.
    """
    try:
        # Only run this on Linux-based systems where uvloop is effective
        if "linux" in sys.platform.lower():
            import uvloop
            uvloop.install()
            print("[Policy Fix] Successfully installed uvloop as the asyncio event loop policy.")
        else:
            print("[Policy Fix] Skipping uvloop installation on non-Linux OS.")
    except ImportError:
        print("[Policy Fix] uvloop not found. Continuing with the default asyncio policy.")
    except Exception as e:
        print(f"[Policy Fix] An error occurred while trying to install uvloop: {e}")

