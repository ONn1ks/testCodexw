from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from .base import Listing, MarketAdapter, Sale


@dataclass(slots=True)
class HarborAdapter(MarketAdapter):
    base_url: str
    client: httpx.AsyncClient | None = None

    code: str = "harbor"

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def fetch_active_listings(self, collection_code: str) -> Sequence[Listing]:
        assert self.client is not None
        response = await self.client.get(
            f"/marketplace/collections/{collection_code}/listings",
            params={"limit": 200},
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("items") if isinstance(data, dict) else data
        listings: list[Listing] = []
        if not isinstance(items, list):
            return listings
        for item in items:
            price = self._extract_price(item)
            if price is None:
                continue
            listings.append(
                Listing(
                    asset_id=str(item.get("tokenId") or item.get("id") or ""),
                    price=price,
                    quantity=int(item.get("quantity", 1)),
                    seller=item.get("sellerAddress") or item.get("seller"),
                )
            )
        listings.sort(key=lambda x: x.price)
        return listings

    async def fetch_recent_sales(self, collection_code: str, limit: int = 50) -> Sequence[Sale]:
        assert self.client is not None
        response = await self.client.get(
            f"/marketplace/collections/{collection_code}/sales",
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("items") if isinstance(data, dict) else data
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
                    asset_id=str(item.get("tokenId") or item.get("id") or ""),
                    price=price,
                    ts=self._parse_ts(ts_raw),
                    tx_hash=item.get("txHash") or item.get("transactionHash"),
                )
            )
        return sales

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()

    @staticmethod
    def _extract_price(payload: Any) -> Decimal | None:
        value = payload.get("price") or payload.get("askPrice") or payload.get("floorPrice")
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


__all__ = ["HarborAdapter"]
