from __future__ import annotations

from typing import Any

from ..adapters import HarborAdapter, MarketAdapter, MrktAdapter, PalaceAdapter, PixelAdapter
from ..config import get_settings


class AdapterFactory:
    def __init__(self) -> None:
        self.settings = get_settings()

    def create(self, market_code: str, meta: dict[str, Any]) -> MarketAdapter:
        if market_code == "harbor":
            base_url = meta.get("base_url") or self.settings.harbor_api_url
            return HarborAdapter(base_url=base_url)
        if market_code == "mrkt":
            return MrktAdapter(
                base_url=meta["base_url"],
                init_data=meta["init_data"],
                session_headers=meta.get("headers", {}),
            )
        if market_code == "palace":
            return PalaceAdapter(
                base_url=meta["base_url"],
                init_data=meta["init_data"],
                session_headers=meta.get("headers", {}),
            )
        if market_code == "pixel":
            return PixelAdapter(
                base_url=meta["base_url"],
                init_data=meta["init_data"],
                session_headers=meta.get("headers", {}),
            )
        raise ValueError(f"Unsupported market: {market_code}")


__all__ = ["AdapterFactory"]
