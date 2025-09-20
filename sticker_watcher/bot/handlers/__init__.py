from __future__ import annotations

from aiogram import Router

from . import commands

router = Router()
router.include_router(commands.router)

__all__ = ["router"]
