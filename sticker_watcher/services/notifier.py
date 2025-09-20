from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.dialects.postgresql import insert

from ..config import Settings, get_settings
from ..db import SessionLocal
from ..models import tables as db_models
from .anti_spam import AntiSpam
from .formatter import format_event
from .types import AlertEvent

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, bot: Bot, anti_spam: AntiSpam, settings: Settings | None = None) -> None:
        self.bot = bot
        self.anti_spam = anti_spam
        self.settings = settings or get_settings()

    async def handle_event(self, event: AlertEvent, deeplink: str | None = None) -> None:
        text = format_event(event)
        for user_id in event.user_ids:
            await self._store_alert(user_id, event)
            event_key = f"{event.collection_id}:{event.type.value}"
            if not await self.anti_spam.allow_push(user_id, event_key, event.ts):
                continue
            if event.notify_instantly:
                await self._send_message(user_id, text, deeplink)

    async def _send_message(self, user_id: int, text: str, deeplink: str | None) -> None:
        markup = None
        if deeplink:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Открыть", url=deeplink)]]
            )
        try:
            await self.bot.send_message(user_id, text, reply_markup=markup, disable_notification=False)
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("Failed to send message to %s: %s", user_id, exc)

    async def send_digest(self, user_id: int, text: str, key: str) -> None:
        event_key = f"digest:{key}"
        if not await self.anti_spam.allow_push(user_id, event_key, datetime.utcnow()):
            return
        await self._send_message(user_id, text, None)

    async def _store_alert(self, user_id: int, event: AlertEvent) -> None:
        async with SessionLocal() as session:
            stmt = insert(db_models.Alert).values(
                user_id=user_id,
                collection_id=event.collection_id,
                ts=event.ts,
                type=event.type.value,
                payload=dict(event.payload),
            )
            await session.execute(stmt)
            await session.commit()


__all__ = ["Notifier"]
