from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from .base import Listing, MarketAdapter, Sale


@dataclass(slots=True)
class TmaAdapter(MarketAdapter):
    code: str
    base_url: str
    init_data: str
    session_headers: Mapping[str, str] | None = None
    client: httpx.AsyncClient | None = None

    def __post_init__(self) -> None:
        if self.client is None:
            headers = {"User-Agent": "StickerFloorWatcher/1.0"}
            if self.session_headers:
                headers.update(self.session_headers)
            self.client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=10.0)

    async def fetch_active_listings(self, collection_code: str) -> Sequence[Listing]:
        assert self.client is not None
        response = await self.client.get(
            "/collections/listings",
            params={"collection": collection_code, "limit": 200},
            headers={"X-Telegram-Init-Data": self.init_data},
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items") if isinstance(payload, dict) else payload
        return self._parse_listings(items)

    async def fetch_recent_sales(self, collection_code: str, limit: int = 50) -> Sequence[Sale]:
        assert self.client is not None
        response = await self.client.get(
            "/collections/sales",
            params={"collection": collection_code, "limit": limit},
            headers={"X-Telegram-Init-Data": self.init_data},
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items") if isinstance(payload, dict) else payload
        return self._parse_sales(items)

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()

    def _parse_listings(self, items: Any) -> Sequence[Listing]:
        listings: list[Listing] = []
        if not isinstance(items, list):
            return listings
        for item in items:
            price = self._extract_price(item)
            if price is None:
                continue
            listings.append(
                Listing(
                    asset_id=str(item.get("id") or item.get("tokenId") or ""),
                    price=price,
                    quantity=int(item.get("quantity", 1)),
                    seller=item.get("seller") or item.get("owner"),
                )
            )
        listings.sort(key=lambda x: x.price)
        return listings

    def _parse_sales(self, items: Any) -> Sequence[Sale]:
        sales: list[Sale] = []
        if not isinstance(items, list):
            return sales
        for item in items:
            price = self._extract_price(item)
            ts_raw = item.get("timestamp") or item.get("createdAt")
            if price is None or ts_raw is None:
                continue
            sales.append(
                Sale(
                    asset_id=str(item.get("id") or item.get("tokenId") or ""),
                    price=price,
                    ts=self._parse_ts(ts_raw),
                    tx_hash=item.get("txHash") or item.get("transactionHash"),
                )
            )
        return sales

    @staticmethod
    def _extract_price(payload: Any) -> Decimal | None:
        value = payload.get("price") or payload.get("askPrice") or payload.get("amount")
        if value is None:
            return None
        if isinstance(value, dict):
            value = value.get("amount") or value.get("value")
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def _parse_ts(value: Any) -> datetime:
        if isinstance(value, int | float):
            return datetime.fromtimestamp(float(value), tz=UTC)
        if isinstance(value, str):
            try:
                if value.endswith("Z"):
                    value = value[:-1] + "+00:00"
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return datetime.now(tz=UTC)


__all__ = ["TmaAdapter"]
