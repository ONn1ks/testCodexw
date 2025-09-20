from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:  # type: ignore[override]
        return mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = ["Base", "TimestampMixin"]
