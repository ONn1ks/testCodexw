from __future__ import annotations

import asyncio

import redis.asyncio as redis

from .config import get_settings

_settings = get_settings()

redis_client = redis.from_url(_settings.redis_dsn, encoding="utf-8", decode_responses=True)
lock = asyncio.Lock()

__all__ = ["redis_client", "lock"]
