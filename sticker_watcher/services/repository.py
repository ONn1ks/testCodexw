from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import tables as db_models


async def ensure_user(session: AsyncSession, tg_id: int, tz: str) -> db_models.User:
    stmt = select(db_models.User).where(db_models.User.tg_id == tg_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        if user.tz != tz:
            user.tz = tz
        return user
    user = db_models.User(tg_id=tg_id, tz=tz)
    session.add(user)
    await session.flush()
    return user


async def get_market(session: AsyncSession, code: str) -> db_models.Market | None:
    stmt = select(db_models.Market).where(db_models.Market.code == code)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_collection(
    session: AsyncSession,
    market_code: str,
    collection_code: str,
) -> db_models.Collection | None:
    stmt = (
        select(db_models.Collection)
        .join(db_models.Market)
        .where(
            and_(
                db_models.Market.code == market_code,
                db_models.Collection.code == collection_code,
            )
        )
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def add_watch(
    session: AsyncSession,
    user: db_models.User,
    collection: db_models.Collection,
    threshold: Decimal | None,
) -> db_models.Watch:
    stmt = (
        insert(db_models.Watch)
        .values(
            user_id=user.id,
            collection_id=collection.id,
            threshold_ton=threshold,
            enabled=True,
        )
        .on_conflict_do_update(
            index_elements=[db_models.Watch.user_id, db_models.Watch.collection_id],
            set_={"threshold_ton": threshold, "enabled": True},
        )
        .returning(db_models.Watch)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def remove_watch(
    session: AsyncSession,
    user: db_models.User,
    collection: db_models.Collection,
) -> None:
    stmt = (
        select(db_models.Watch)
        .where(
            and_(
                db_models.Watch.user_id == user.id,
                db_models.Watch.collection_id == collection.id,
            )
        )
    )
    watch = (await session.execute(stmt)).scalar_one_or_none()
    if watch:
        watch.enabled = False


async def list_watches(session: AsyncSession, user: db_models.User) -> Sequence[tuple[db_models.Collection, db_models.Market, db_models.Watch]]:
    stmt = (
        select(db_models.Collection, db_models.Market, db_models.Watch)
        .join(db_models.Watch, db_models.Watch.collection_id == db_models.Collection.id)
        .join(db_models.Market, db_models.Market.id == db_models.Collection.market_id)
        .where(
            and_(
                db_models.Watch.user_id == user.id,
                db_models.Watch.enabled.is_(True),
            )
        )
        .order_by(db_models.Market.code, db_models.Collection.code)
    )
    return (await session.execute(stmt)).all()


async def set_mute(session: AsyncSession, user: db_models.User, until: datetime | None) -> None:
    user.mute_until = until


async def get_enabled_digest_users(session: AsyncSession) -> Sequence[db_models.User]:
    stmt = select(db_models.User).where(db_models.User.mute_until.is_(None))
    return (await session.execute(stmt)).scalars().all()


__all__ = [
    "add_watch",
    "ensure_user",
    "get_collection",
    "get_enabled_digest_users",
    "get_market",
    "list_watches",
    "remove_watch",
    "set_mute",
]
