from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from ..config import get_settings
from .handlers import router as handlers_router
from .middlewares.whitelist import WhitelistMiddleware

settings = get_settings()

bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher = Dispatcher()
dispatcher.include_router(handlers_router)
dispatcher.message.middleware(WhitelistMiddleware(settings.whitelist_ids))

dispatcher.callback_query.middleware(WhitelistMiddleware(settings.whitelist_ids))

__all__ = ["bot", "dispatcher"]
