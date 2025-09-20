from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from ..bot import bot
from ..config import Settings, get_settings
from ..db import SessionLocal
from ..models import tables as db_models
from ..redis import redis_client
from .adapter_factory import AdapterFactory
from .anti_spam import AntiSpam
from .digest import DigestManager
from .metrics import RollingSeries
from .notifier import Notifier
from .watchers import CollectionWatcher, WatcherContext

logger = logging.getLogger(__name__)

POLL_INTERVALS = {
    "harbor": 15,
    "mrkt": 25,
    "palace": 25,
    "pixel": 25,
}


class WatchScheduler:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.scheduler = AsyncIOScheduler(timezone=ZoneInfo(self.settings.timezone))
        self.adapter_factory = AdapterFactory()
        self.watchers: dict[int, CollectionWatcher] = {}
        anti_spam = AntiSpam(redis_client, self.settings)
        self.notifier = Notifier(bot, anti_spam, self.settings)
        self.digest_manager = DigestManager(self.notifier, redis_client, self.settings)

    async def start(self) -> None:
        await self._load_watchers()
        self.scheduler.add_job(self.digest_manager.flush_quarter, CronTrigger(minute="*/15", second=5))
        for time_str in self.settings.digest.times:
            hour, minute = map(int, time_str.split(":"))
            self.scheduler.add_job(
                self.digest_manager.send_daily_digest,
                CronTrigger(hour=hour, minute=minute, second=0),
                args=(time_str,),
            )
        self.scheduler.start()

    async def shutdown(self) -> None:
        await self.scheduler.shutdown(wait=False)
        await asyncio.gather(*(watcher.context.adapter.close() for watcher in self.watchers.values()))

    async def _load_watchers(self) -> None:
        async with SessionLocal() as session:
            stmt = (
                select(db_models.Collection, db_models.Market)
                .join(db_models.Market, db_models.Market.id == db_models.Collection.market_id)
                .join(db_models.Watch, db_models.Watch.collection_id == db_models.Collection.id)
                .where(db_models.Watch.enabled.is_(True))
                .group_by(db_models.Collection.id, db_models.Market.id)
            )
            result = await session.execute(stmt)
            rows = result.all()

        for collection, market in rows:
            if collection.id in self.watchers:
                continue
            adapter = self.adapter_factory.create(market.code, collection.meta)
            context = WatcherContext(
                collection=collection,
                market=market,
                adapter=adapter,
                floor_history=RollingSeries(maxlen=500, ttl=timedelta(hours=24)),
                volatility_history=RollingSeries(maxlen=500, ttl=timedelta(hours=2)),
            )
            watcher = CollectionWatcher(context, self.settings)
            await watcher.initialize()
            self.watchers[collection.id] = watcher
            interval = POLL_INTERVALS.get(market.code, 30)
            self.scheduler.add_job(
                self._poll_collection,
                IntervalTrigger(seconds=interval, jitter=5),
                args=(collection.id,),
                id=f"collection-{collection.id}",
                replace_existing=True,
            )

    async def _poll_collection(self, collection_id: int) -> None:
        watcher = self.watchers.get(collection_id)
        if not watcher:
            return
        events = await watcher.poll()
        if not events:
            return
        for event in events:
            meta = watcher.context.collection.meta or {}
            deeplink = meta.get("deeplink")
            await self.digest_manager.handle_event(event, deeplink)


__all__ = ["WatchScheduler"]
