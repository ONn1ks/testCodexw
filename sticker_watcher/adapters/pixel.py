from __future__ import annotations

from dataclasses import dataclass

from .tma import TmaAdapter


@dataclass(slots=True)
class PixelAdapter(TmaAdapter):
    code: str = "pixel"


__all__ = ["PixelAdapter"]
