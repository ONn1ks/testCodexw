from __future__ import annotations

from dataclasses import dataclass

from .tma import TmaAdapter


@dataclass(slots=True)
class MrktAdapter(TmaAdapter):
    code: str = "mrkt"


__all__ = ["MrktAdapter"]
