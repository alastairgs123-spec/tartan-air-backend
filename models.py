from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, Text
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    callsign: Mapped[str | None] = mapped_column(String(16), nullable=True)

    flights: Mapped[list["Flight"]] = relationship(back_populates="user")

class Route(Base):
    __tablename__ = "routes"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dep: Mapped[str] = mapped_column(String(8), index=True)
    arr: Mapped[str] = mapped_column(String(8), index=True)
    distance_nm: Mapped[int] = mapped_column(Integer)
    aircraft: Mapped[str] = mapped_column(String(128))  # comma-separated types

class Flight(Base):
    __tablename__ = "flights"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id"), nullable=True)

    dep: Mapped[str] = mapped_column(String(8))
    arr: Mapped[str] = mapped_column(String(8))

    status: Mapped[str] = mapped_column(String(32), default="active")  # active|finished
    start_ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    block_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    landing_rate_fpm: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="flights")
    positions: Mapped[list["Position"]] = relationship(back_populates="flight", cascade="all, delete-orphan")

class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    alt_ft: Mapped[float] = mapped_column(Float)
    ias_kt: Mapped[float] = mapped_column(Float)
    vs_fpm: Mapped[float] = mapped_column(Float)
    onground: Mapped[bool] = mapped_column(Boolean, default=False)

    flight: Mapped["Flight"] = relationship(back_populates="positions")
