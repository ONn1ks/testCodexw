from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from .events import EventType


@dataclass(slots=True)
class AlertEvent:
    type: EventType
    collection_id: int
    market_code: str
    collection_code: str
    collection_name: str
    payload: Mapping[str, Any]
    ts: datetime
    user_ids: tuple[int, ...]
    notify_instantly: bool = True


@dataclass(slots=True)
class WatchConfig:
    threshold_ton: Decimal | None
    user_id: int


__all__ = ["AlertEvent", "WatchConfig"]
