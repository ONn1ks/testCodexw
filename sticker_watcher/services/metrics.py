from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from statistics import median, pstdev

from ..adapters import Listing


@dataclass(slots=True)
class MarketSnapshot:
    ts: datetime
    floor: Decimal
    depth_5: int
    listings: Sequence[Listing]


def calculate_floor(listings: Sequence[Listing]) -> Decimal | None:
    return listings[0].price if listings else None


def calculate_depth(listings: Sequence[Listing], floor: Decimal, delta_pct: float) -> int:
    upper = floor * (Decimal(1) + Decimal(delta_pct) / Decimal(100))
    return sum(1 for item in listings if floor <= item.price <= upper)


def calculate_volatility(history: Sequence[Decimal]) -> Decimal:
    if len(history) < 2:
        return Decimal(0)
    floats = [float(value) for value in history]
    return Decimal(str(pstdev(floats)))


def calculate_median_floor(history: Sequence[Decimal]) -> Decimal | None:
    if not history:
        return None
    try:
        return Decimal(str(median(history)))
    except InvalidOperation:
        return None


class RollingSeries:
    def __init__(self, maxlen: int, ttl: timedelta | None = None) -> None:
        self._values: deque[tuple[datetime, Decimal]] = deque(maxlen=maxlen)
        self._ttl = ttl

    def add(self, ts: datetime, value: Decimal) -> None:
        self._values.append((ts, value))
        self._trim()

    def values(self) -> Sequence[Decimal]:
        self._trim()
        return [value for _, value in self._values]

    def items(self) -> Sequence[tuple[datetime, Decimal]]:
        self._trim()
        return list(self._values)

    def value_ago(self, delta: timedelta) -> Decimal | None:
        if not self._values:
            return None
        cutoff = datetime.now(UTC) - delta
        for ts, value in reversed(self._values):
            if ts <= cutoff:
                return value
        return self._values[0][1]

    def _trim(self) -> None:
        if self._ttl is None:
            return
        cutoff = datetime.now(UTC) - self._ttl
        while self._values and self._values[0][0] < cutoff:
            self._values.popleft()


__all__ = [
    "MarketSnapshot",
    "RollingSeries",
    "calculate_depth",
    "calculate_floor",
    "calculate_median_floor",
    "calculate_volatility",
]
