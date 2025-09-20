from __future__ import annotations

import abc
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Listing:
    asset_id: str
    price: Decimal
    quantity: int = 1
    seller: str | None = None
    ts: datetime | None = None


@dataclass(frozen=True)
class Sale:
    asset_id: str
    price: Decimal
    ts: datetime
    tx_hash: str | None = None


class MarketAdapter(abc.ABC):
    code: str

    @abc.abstractmethod
    async def fetch_active_listings(self, collection_code: str) -> Sequence[Listing]:
        """Return active listings sorted by price ascending."""

    async def fetch_recent_sales(self, collection_code: str, limit: int = 50) -> Sequence[Sale]:
        """Fetch recent sales for the collection."""
        return []

    async def close(self) -> None:
        return None


__all__ = ["Listing", "Sale", "MarketAdapter"]
