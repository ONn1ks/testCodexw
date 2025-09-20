import asyncio

from sticker_watcher.db import engine
from sticker_watcher.models import tables  # noqa: F401
from sticker_watcher.models.base import Base


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(main())
