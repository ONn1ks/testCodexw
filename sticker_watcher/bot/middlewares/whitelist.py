from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import Update

from ...config import get_settings


class WhitelistMiddleware(BaseMiddleware):
    def __init__(self, allowed_ids: set[int] | None = None) -> None:
        self.allowed_ids = allowed_ids or get_settings().whitelist_ids

    async def __call__(self, handler, event: Update, data):  # type: ignore[override]
        user = event.from_user if hasattr(event, "from_user") else None
        if user is None or (self.allowed_ids and user.id not in self.allowed_ids):
            if hasattr(event, "answer"):
                await event.answer("🚫 Доступ закрыт")
            return None
        return await handler(event, data)


__all__ = ["WhitelistMiddleware"]
