from __future__ import annotations

import asyncio

from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .bot import bot, dispatcher
from .config import get_settings
from .logging import setup_logging
from .services.scheduler import WatchScheduler

app = FastAPI(title="Sticker Floor Watcher")
settings = get_settings()
setup_logging()
scheduler = WatchScheduler(settings)


@app.on_event("startup")
async def on_startup() -> None:
    if settings.webhook_url:
        await bot.set_webhook(settings.webhook_url, secret_token=settings.webhook_secret)
    if settings.run_scheduler:
        asyncio.create_task(scheduler.start())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await scheduler.shutdown()
    await bot.session.close()


@app.post(settings.webhook_path)
async def telegram_webhook(request: Request) -> JSONResponse:
    if settings.webhook_secret:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if token != settings.webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid secret token")
    data = await request.json()
    update = Update.model_validate(data)
    await dispatcher.feed_update(bot, update)
    return JSONResponse({"ok": True})


@app.get("/healthz")
async def healthcheck() -> JSONResponse:
    return JSONResponse({"status": "ok"})


__all__ = ["app"]
