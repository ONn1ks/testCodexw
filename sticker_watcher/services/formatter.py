from __future__ import annotations

from .events import EventType
from .types import AlertEvent


def format_event(event: AlertEvent) -> str:
    market = event.market_code.upper()
    collection = event.collection_name
    floor = event.payload.get("floor")
    depth = event.payload.get("depth_5")
    if event.type == EventType.FLOOR_BELOW:
        threshold = event.payload.get("threshold")
        return (
            f"⚡ {collection} — {market}: floor {floor} TON."
            + (f" Порог: {threshold} TON." if threshold else "")
        )
    if event.type == EventType.UNDER_FLOOR_RARE:
        listings = event.payload.get("listings", [])
        if listings:
            listing = listings[0]
            price = listing.get("price")
            return (
                f"⚡ {collection} — {market}: редкий листинг {price} TON"
                f" (floor {floor} TON)."
            )
    if event.type == EventType.THIN_FLOOR:
        return f"🧩 {market} | {collection}: floor {floor} TON, depth5 {depth}."
    if event.type == EventType.DROP_SPIKE:
        drop = event.payload.get("drop_pct")
        return (
            f"⚡ {collection} — {market}: floor {floor} TON ({drop:.2f}% за 15м)."
        )
    if event.type == EventType.VOLUME_SPIKE:
        volume = event.payload.get("volume")
        return f"⚡ {collection} — {market}: рост объёма {volume}."
    return f"ℹ️ {collection} — {market}: событие {event.type.value}."


__all__ = ["format_event"]
