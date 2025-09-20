from __future__ import annotations

from dataclasses import dataclass

from .tma import TmaAdapter


@dataclass(slots=True)
class PalaceAdapter(TmaAdapter):
    code: str = "palace"


__all__ = ["PalaceAdapter"]
