from __future__ import annotations

from datetime import datetime

from redis.asyncio import Redis

from ..config import Settings


class AntiSpam:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def allow_push(self, user_id: int, event_key: str, now: datetime) -> bool:
        if await self._user_on_cooldown(user_id, now):
            return False
        if await self._event_on_cooldown(user_id, event_key, now):
            return False
        await self._mark_user(user_id, now)
        await self._mark_event(user_id, event_key, now)
        return True

    async def _user_on_cooldown(self, user_id: int, now: datetime) -> bool:
        key = f"user:cooldown:{user_id}"
        ttl = await self.redis.ttl(key)
        if ttl > 0:
            return True
        return False

    async def _event_on_cooldown(self, user_id: int, event_key: str, now: datetime) -> bool:
        key = f"event:cooldown:{user_id}:{event_key}"
        ttl = await self.redis.ttl(key)
        return ttl > 0

    async def _mark_user(self, user_id: int, now: datetime) -> None:
        key = f"user:cooldown:{user_id}"
        await self.redis.set(
            key,
            int(now.timestamp()),
            ex=self.settings.alerts.min_interval_sec,
        )

    async def _mark_event(self, user_id: int, event_key: str, now: datetime) -> None:
        key = f"event:cooldown:{user_id}:{event_key}"
        await self.redis.set(
            key,
            int(now.timestamp()),
            ex=self.settings.alerts.same_event_cooldown_sec,
        )


__all__ = ["AntiSpam"]
