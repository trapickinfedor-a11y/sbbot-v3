import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main_bot.app.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())

