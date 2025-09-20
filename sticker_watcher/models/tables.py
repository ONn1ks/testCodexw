from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    tz: Mapped[str] = mapped_column(Text, default="Europe/Amsterdam", nullable=False)
    mute_until: Mapped[datetime | None] = mapped_column(default=None)

    watches: Mapped[list[Watch]] = relationship(back_populates="user")


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    collections: Mapped[list[Collection]] = relationship(back_populates="market")


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    market: Mapped[Market] = relationship(back_populates="collections")
    watches: Mapped[list[Watch]] = relationship(back_populates="collection")
    prices: Mapped[list[Price]] = relationship(back_populates="collection")
    sales: Mapped[list[Sale]] = relationship(back_populates="collection")


class Watch(Base):
    __tablename__ = "watches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False)
    threshold_ton: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="watches")
    collection: Mapped[Collection] = relationship(back_populates="watches")

    __table_args__ = (UniqueConstraint("user_id", "collection_id", name="uq_user_collection"),)


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(nullable=False)
    floor: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    depth_5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spread: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    src: Mapped[str] = mapped_column(Text, nullable=False)

    collection: Mapped[Collection] = relationship(back_populates="prices")


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    tx_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    src: Mapped[str] = mapped_column(Text, nullable=False)

    collection: Mapped[Collection] = relationship(back_populates="sales")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


__all__ = [
    "Alert",
    "Collection",
    "Market",
    "Price",
    "Sale",
    "User",
    "Watch",
]
