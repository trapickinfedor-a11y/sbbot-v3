"""
Shared pytest fixtures for sb_v3 tests.
"""
import pytest
import sys
from pathlib import Path

# Ensure the core/ directory is on the path
_core_dir = Path(__file__).parent
if str(_core_dir) not in sys.path:
    sys.path.insert(0, str(_core_dir))


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"