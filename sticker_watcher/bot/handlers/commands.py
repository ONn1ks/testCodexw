from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import StringIO

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import and_, select

from ...config import get_settings
from ...db import SessionLocal
from ...models import tables as db_models
from ...services import repository

router = Router()
settings = get_settings()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    async with SessionLocal() as session:
        await repository.ensure_user(session, message.from_user.id, settings.timezone)
        await session.commit()
    await message.answer(
        "Привет! Я наблюдаю за floor выбранных коллекций. Используй /watch, чтобы добавить коллекцию."
    )


@router.message(Command("watch"))
async def cmd_watch(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer("Использование: /watch <market> <collection_code> [threshold]")
        return
    market_code = parts[1].lower()
    collection_code = parts[2]
    threshold = None
    if len(parts) >= 4:
        try:
            threshold = Decimal(parts[3])
        except InvalidOperation:
            await message.answer("Некорректное значение порога.")
            return

    async with SessionLocal() as session:
        user = await repository.ensure_user(session, message.from_user.id, settings.timezone)
        collection = await repository.get_collection(session, market_code, collection_code)
        if not collection:
            await message.answer("Коллекция не найдена. Обнови конфигурацию в БД.")
            return
        await repository.add_watch(session, user, collection, threshold)
        await session.commit()
    await message.answer(f"Коллекция {collection.name} добавлена в наблюдение.")


@router.message(Command("unwatch"))
async def cmd_unwatch(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer("Использование: /unwatch <market> <collection_code>")
        return
    market_code = parts[1].lower()
    collection_code = parts[2]

    async with SessionLocal() as session:
        user = await repository.ensure_user(session, message.from_user.id, settings.timezone)
        collection = await repository.get_collection(session, market_code, collection_code)
        if not collection:
            await message.answer("Коллекция не найдена.")
            return
        await repository.remove_watch(session, user, collection)
        await session.commit()
    await message.answer("Наблюдение отключено.")


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    async with SessionLocal() as session:
        user = await repository.ensure_user(session, message.from_user.id, settings.timezone)
        watches = await repository.list_watches(session, user)
    if not watches:
        await message.answer("Список пуст.")
        return
    lines = ["Текущие наблюдения:"]
    for collection, market, watch in watches:
        threshold = f", порог {watch.threshold_ton}" if watch.threshold_ton else ""
        lines.append(f"• {market.code.upper()} — {collection.name} ({collection.code}){threshold}")
    await message.answer("\n".join(lines))


@router.message(Command("mute"))
async def cmd_mute(message: Message) -> None:
    parts = (message.text or "").split()
    minutes = int(parts[1]) if len(parts) >= 2 else 60
    until = datetime.now(UTC) + timedelta(minutes=minutes)
    async with SessionLocal() as session:
        user = await repository.ensure_user(session, message.from_user.id, settings.timezone)
        await repository.set_mute(session, user, until)
        await session.commit()
    await message.answer(f"Уведомления заглушены до {until:%H:%M UTC}.")


@router.message(Command("unmute"))
async def cmd_unmute(message: Message) -> None:
    async with SessionLocal() as session:
        user = await repository.ensure_user(session, message.from_user.id, settings.timezone)
        await repository.set_mute(session, user, None)
        await session.commit()
    await message.answer("Уведомления включены.")


@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) < 4:
        await message.answer("Использование: /export <market> <collection_code> <days>")
        return
    market_code = parts[1].lower()
    collection_code = parts[2]
    days = int(parts[3])
    since = datetime.now(UTC) - timedelta(days=days)

    async with SessionLocal() as session:
        await repository.ensure_user(session, message.from_user.id, settings.timezone)
        collection = await repository.get_collection(session, market_code, collection_code)
        if not collection:
            await message.answer("Коллекция не найдена.")
            return
        stmt = (
            select(db_models.Price)
            .where(
                and_(
                    db_models.Price.collection_id == collection.id,
                    db_models.Price.ts >= since,
                )
            )
            .order_by(db_models.Price.ts)
        )
        rows = (await session.execute(stmt)).scalars().all()

    if not rows:
        await message.answer("Нет данных за выбранный период.")
        return

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["timestamp", "floor", "depth_5", "spread"])
    for row in rows:
        writer.writerow([row.ts.isoformat(), row.floor, row.depth_5, row.spread])
    buffer.seek(0)

    document = BufferedInputFile(buffer.getvalue().encode("utf-8"), filename=f"{market_code}_{collection_code}.csv")
    await message.answer_document(document=document, caption="Экспорт данных")
