from __future__ import annotations

from datetime import datetime, time, timedelta

import pytz


def next_occurrence(now: datetime, target: time, tz: str) -> datetime:
    zone = pytz.timezone(tz)
    localized_now = now.astimezone(zone)
    candidate = zone.localize(datetime.combine(localized_now.date(), target))
    if candidate <= localized_now:
        candidate += timedelta(days=1)
    return candidate.astimezone(pytz.UTC)


__all__ = ["next_occurrence"]
