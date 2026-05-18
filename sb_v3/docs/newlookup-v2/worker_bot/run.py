"""
Запуск Worker Bot
"""

import asyncio
from worker_bot.bot import main


if __name__ == "__main__":
    asyncio.run(main())
