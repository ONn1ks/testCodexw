from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters import Listing, MarketAdapter
from ..config import Settings, get_settings
from ..db import SessionLocal
from ..models import tables as db_models
from .events import EventType
from .metrics import (
    RollingSeries,
    calculate_depth,
    calculate_floor,
    calculate_median_floor,
    calculate_volatility,
)
from .types import AlertEvent

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WatcherContext:
    collection: db_models.Collection
    market: db_models.Market
    adapter: MarketAdapter
    floor_history: RollingSeries
    volatility_history: RollingSeries


class CollectionWatcher:
    def __init__(self, context: WatcherContext, settings: Settings | None = None) -> None:
        self.context = context
        self.settings = settings or get_settings()
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        async with SessionLocal() as session:
            await self._load_history(session)

    async def poll(self) -> Sequence[AlertEvent]:
        async with self._lock:
            now = datetime.now(UTC)
            listings = await self.context.adapter.fetch_active_listings(self.context.collection.code)
            if not listings:
                return []
            floor = calculate_floor(listings)
            if floor is None:
                return []
            depth_5 = calculate_depth(listings, floor, self.settings.alerts.depth_delta_pct)
            self.context.floor_history.add(now, floor)
            self.context.volatility_history.add(now, floor)
            volatility = calculate_volatility(self.context.volatility_history.values())
            median_floor_24h = calculate_median_floor(self.context.floor_history.values())
            events = await self._detect_events(
                listings=listings,
                now=now,
                floor=floor,
                depth_5=depth_5,
                median_floor=median_floor_24h,
                volatility=volatility,
            )
            await self._persist_price(now, floor, depth_5, volatility)
            return events

    async def _load_history(self, session: AsyncSession) -> None:
        stmt = (
            select(db_models.Price.ts, db_models.Price.floor)
            .where(db_models.Price.collection_id == self.context.collection.id)
            .order_by(db_models.Price.ts.desc())
            .limit(500)
        )
        rows = (await session.execute(stmt)).all()
        for ts, floor in reversed(rows):
            if floor is None:
                continue
            self.context.floor_history.add(ts, Decimal(floor))
            self.context.volatility_history.add(ts, Decimal(floor))

    async def _persist_price(self, ts: datetime, floor: Decimal, depth_5: int, volatility: Decimal) -> None:
        async with SessionLocal() as session:
            stmt = insert(db_models.Price).values(
                collection_id=self.context.collection.id,
                ts=ts,
                floor=floor,
                depth_5=depth_5,
                spread=None,
                src=self.context.market.code,
            )
            await session.execute(stmt)
            await session.commit()

    async def _detect_events(
        self,
        listings: Sequence[Listing],
        now: datetime,
        floor: Decimal,
        depth_5: int,
        median_floor: Decimal | None,
        volatility: Decimal,
    ) -> Sequence[AlertEvent]:
        watchers = await self._load_watchers(now)
        if not watchers:
            return []
        events: list[AlertEvent] = []
        triggered_watches = [
            watch
            for watch in watchers
            if watch.threshold_ton is not None and floor <= watch.threshold_ton
        ]
        if triggered_watches:
            floor_below_users = [watch.user_id for watch in triggered_watches]
            min_threshold = min(Decimal(watch.threshold_ton) for watch in triggered_watches if watch.threshold_ton is not None)
            events.append(
                AlertEvent(
                    type=EventType.FLOOR_BELOW,
                    collection_id=self.context.collection.id,
                    market_code=self.context.market.code,
                    collection_code=self.context.collection.code,
                    collection_name=self.context.collection.name,
                    payload={
                        "floor": str(floor),
                        "depth_5": depth_5,
                        "median_floor_24h": str(median_floor) if median_floor else None,
                        "threshold": str(min_threshold),
                    },
                    ts=now,
                    user_ids=tuple(floor_below_users),
                    notify_instantly=True,
                )
            )
        if median_floor is not None:
            under_floor_listings = [
                listing
                for listing in listings
                if listing.price <= median_floor * (Decimal(1) - Decimal(self.settings.alerts.under_floor_pct) / Decimal(100))
            ]
            if under_floor_listings:
                events.append(
                    AlertEvent(
                        type=EventType.UNDER_FLOOR_RARE,
                        collection_id=self.context.collection.id,
                        market_code=self.context.market.code,
                        collection_code=self.context.collection.code,
                        collection_name=self.context.collection.name,
                        payload={
                            "floor": str(floor),
                            "median_floor_24h": str(median_floor),
                            "listings": [
                                {"asset_id": listing.asset_id, "price": str(listing.price)}
                                for listing in under_floor_listings
                            ],
                        },
                        ts=now,
                        user_ids=tuple(watch.user_id for watch in watchers),
                        notify_instantly=True,
                    )
                )
        if depth_5 <= self.settings.alerts.thin_floor_min_lots:
            events.append(
                AlertEvent(
                    type=EventType.THIN_FLOOR,
                    collection_id=self.context.collection.id,
                    market_code=self.context.market.code,
                    collection_code=self.context.collection.code,
                    collection_name=self.context.collection.name,
                    payload={
                        "floor": str(floor),
                        "depth_5": depth_5,
                    },
                    ts=now,
                    user_ids=tuple(watch.user_id for watch in watchers),
                    notify_instantly=False,
                )
            )
        drop_reference = self.context.floor_history.value_ago(timedelta(minutes=15))
        if drop_reference and drop_reference > 0:
            drop_pct = (floor - drop_reference) / drop_reference * Decimal(100)
            if drop_pct <= Decimal(-3):
                events.append(
                    AlertEvent(
                        type=EventType.DROP_SPIKE,
                        collection_id=self.context.collection.id,
                        market_code=self.context.market.code,
                        collection_code=self.context.collection.code,
                        collection_name=self.context.collection.name,
                        payload={
                            "floor": str(floor),
                            "drop_pct": float(drop_pct),
                            "reference_floor": str(drop_reference),
                        },
                        ts=now,
                        user_ids=tuple(watch.user_id for watch in watchers),
                        notify_instantly=True,
                    )
                )
        return events

    async def _load_watchers(self, now: datetime) -> Sequence[db_models.Watch]:
        async with SessionLocal() as session:
            stmt = (
                select(db_models.Watch)
                .where(
                    and_(
                        db_models.Watch.collection_id == self.context.collection.id,
                        db_models.Watch.enabled.is_(True),
                        or_(
                            db_models.User.mute_until.is_(None),
                            db_models.User.mute_until < now,
                        ),
                    )
                )
                .join(db_models.User, db_models.User.id == db_models.Watch.user_id)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]


__all__ = ["CollectionWatcher", "WatcherContext"]
