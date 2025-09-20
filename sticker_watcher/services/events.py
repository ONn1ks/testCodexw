from __future__ import annotations

from enum import Enum


class EventType(str, Enum):
    FLOOR_BELOW = "FLOOR_BELOW"
    UNDER_FLOOR_RARE = "UNDER_FLOOR_RARE"
    THIN_FLOOR = "THIN_FLOOR"
    DROP_SPIKE = "DROP_SPIKE"
    VOLUME_SPIKE = "VOLUME_SPIKE"


__all__ = ["EventType"]
