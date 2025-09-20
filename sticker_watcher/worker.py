from __future__ import annotations

import asyncio
import signal

from .bot import bot
from .config import get_settings
from .logging import setup_logging
from .services.scheduler import WatchScheduler


async def main() -> None:
    settings = get_settings()
    setup_logging()
    scheduler = WatchScheduler(settings)
    await scheduler.start()

    stop_event = asyncio.Event()

    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_running_loop().add_signal_handler(sig, stop_event.set)

    await stop_event.wait()
    await scheduler.shutdown()
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
