from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import and_, select

from ..config import Settings, get_settings
from ..db import SessionLocal
from ..models import tables as db_models
from . import repository
from .notifier import Notifier
from .types import AlertEvent


class DigestManager:
    def __init__(self, notifier: Notifier, redis: Redis, settings: Settings | None = None) -> None:
        self.notifier = notifier
        self.redis = redis
        self.settings = settings or get_settings()

    async def handle_event(self, event: AlertEvent, deeplink: str | None) -> None:
        if event.notify_instantly:
            await self.notifier.handle_event(event, deeplink)
            return
        await self._queue_event(event)

    async def _queue_event(self, event: AlertEvent) -> None:
        record = {
            "collection_id": event.collection_id,
            "collection_code": event.collection_code,
            "collection_name": event.collection_name,
            "market_code": event.market_code,
            "payload": dict(event.payload),
            "event_type": event.type.value,
            "ts": event.ts.isoformat(),
        }
        data = json.dumps(record)
        for user_id in event.user_ids:
            key = f"digest:15m:{user_id}"
            await self.redis.rpush(key, data)

    async def flush_quarter(self) -> None:
        keys = await self.redis.keys("digest:15m:*")
        for key in keys:
            user_id = int(key.split(":")[-1])
            items = await self.redis.lrange(key, 0, -1)
            await self.redis.delete(key)
            if not items:
                continue
            summary = self._aggregate_quarter_items(items)
            text_lines = ["🧩 15-мин отчёт"]
            for entry in summary:
                events = ", ".join(f"{etype}:{count}" for etype, count in entry["events"].items())
                text_lines.append(
                    f"• {entry['market']} | {entry['collection']}: floor {entry['floor']} TON, depth5 {entry['depth']}; {events}"
                )
            await self.notifier.send_digest(user_id, "\n".join(text_lines), key="15m")

    def _aggregate_quarter_items(self, items: Iterable[str]) -> Iterable[dict[str, str]]:
        grouped: dict[tuple[str, str], dict[str, object]] = {}
        for raw in items:
            payload = json.loads(raw)
            key = (payload["market_code"], payload["collection_name"])
            entry = grouped.setdefault(
                key,
                {
                    "market": payload["market_code"].upper(),
                    "collection": payload["collection_name"],
                    "floor": payload["payload"].get("floor"),
                    "depth": payload["payload"].get("depth_5"),
                    "events": Counter(),
                },
            )
            entry["events"][payload["event_type"]] += 1
            if payload["payload"].get("floor"):
                entry["floor"] = payload["payload"].get("floor")
            if payload["payload"].get("depth_5") is not None:
                entry["depth"] = payload["payload"].get("depth_5")
        return grouped.values()

    async def send_daily_digest(self, label: str) -> None:
        async with SessionLocal() as session:
            users = await repository.get_enabled_digest_users(session)  # type: ignore[name-defined]
        for user in users:
            text = await self._build_daily_digest_text(user)
            if text:
                await self.notifier.send_digest(user.tg_id, text, key=f"daily:{label}")

    async def _build_daily_digest_text(self, user: db_models.User) -> str | None:
        async with SessionLocal() as session:
            watches = await repository.list_watches(session, user)
            if not watches:
                return None
            lines = ["📰 Дайджест"]
            for collection, market, _ in watches:
                latest_price = await self._fetch_latest_price(session, collection.id)
                change = await self._compute_change(session, collection.id)
                if latest_price is None:
                    continue
                change_str = f", Δ24ч {change:+.2f}%" if change is not None else ""
                lines.append(
                    f"• {market.code.upper()} | {collection.name}: floor {latest_price:.2f} TON{change_str}"
                )
            return "\n".join(lines)

    async def _fetch_latest_price(self, session, collection_id: int) -> float | None:
        stmt = (
            select(db_models.Price.floor)
            .where(db_models.Price.collection_id == collection_id)
            .order_by(db_models.Price.ts.desc())
            .limit(1)
        )
        value = (await session.execute(stmt)).scalar_one_or_none()
        return float(value) if value is not None else None

    async def _compute_change(self, session, collection_id: int) -> float | None:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        stmt = (
            select(db_models.Price.ts, db_models.Price.floor)
            .where(
                and_(
                    db_models.Price.collection_id == collection_id,
                    db_models.Price.ts >= cutoff,
                )
            )
            .order_by(db_models.Price.ts.asc())
        )
        rows = (await session.execute(stmt)).all()
        if len(rows) < 2:
            return None
        start = Decimal(rows[0][1])
        end = Decimal(rows[-1][1])
        if start == 0:
            return None
        return float((end - start) / start * Decimal(100))


__all__ = ["DigestManager"]
