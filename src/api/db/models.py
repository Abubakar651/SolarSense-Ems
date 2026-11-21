"""
ORM models for accounts, sites, preferences and alerts.

Types are kept portable (Uuid, Numeric, timezone-aware DateTime) so the same models run on
Supabase Postgres in production and on in-memory SQLite in the test suite. Every child row
cascades from `users`, so deleting an account removes all of its data in one statement.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    TypeDecorator,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores aware datetimes as UTC and always returns them aware (SQLite drops the offset)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed; pass a timezone-aware value.")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    email_verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now)

    site: Mapped[Site | None] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True)


class ActionToken(Base):
    __tablename__ = "action_tokens"
    __table_args__ = (CheckConstraint("purpose IN ('verify_email', 'reset_password')", name="ck_action_tokens_purpose"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)


class Site(Base):
    __tablename__ = "sites"
    __table_args__ = (
        CheckConstraint("reserve_pct BETWEEN 15 AND 100", name="ck_sites_reserve_pct"),
        CheckConstraint("pv_kwp > 0", name="ck_sites_pv_kwp"),
        CheckConstraint("battery_kwh > 0", name="ck_sites_battery_kwh"),
        CheckConstraint("sanctioned_load_kw > 0", name="ck_sites_sanctioned_load_kw"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Karachi")
    pv_kwp: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    battery_kwh: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    inverter_make: Mapped[str] = mapped_column(String(32), nullable=False)
    inverter_serial: Mapped[str] = mapped_column(String(64), nullable=False)
    # The inverter's private LAN address, polled for telemetry (src/api/telemetry_logger.py). None until set.
    inverter_host: Mapped[str | None] = mapped_column(String(45), nullable=True)
    # The recorded station dataset this site owns, if any (see src/api/user_site.py). At most one site per
    # station; every other site only ever sees its own logged telemetry.
    station_code: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    reserve_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    tariff_category: Mapped[str] = mapped_column(String(32), nullable=False)
    prosumer_regime: Mapped[str] = mapped_column(String(48), nullable=False)
    sanctioned_load_kw: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    is_atl_filer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_electricity_duty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_protected_consumer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user: Mapped[User] = relationship(back_populates="site")
    blackouts: Mapped[list[BlackoutWindow]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="BlackoutWindow.position"
    )


class BlackoutWindow(Base):
    __tablename__ = "blackout_windows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sites.id", ondelete="CASCADE"), index=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)


class NotificationPref(Base):
    __tablename__ = "notification_prefs"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    alert_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    in_app: Mapped[bool] = mapped_column(Boolean, nullable=False)
    email: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ReportPref(Base):
    __tablename__ = "report_prefs"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    monthly: Mapped[bool] = mapped_column(Boolean, nullable=False)
    weekly: Mapped[bool] = mapped_column(Boolean, nullable=False)
    send_to: Mapped[str] = mapped_column(String(254), nullable=False)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (CheckConstraint("severity IN ('crit', 'warn', 'info', 'ok')", name="ck_alerts_severity"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(8), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now, index=True)
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class InverterSample(Base):
    """
    One poll of a site's inverter (src/api/telemetry_logger.py). These rows are the site's own history:
    the live forecast's lag features, its energy and outage history, and its alerts. Deleted with the site.
    Signs follow the live reader: grid power + is export, battery power + is charging.
    """

    __tablename__ = "inverter_samples"

    site_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    pv_power_w: Mapped[float] = mapped_column(Float, nullable=False)
    load_power_w: Mapped[float] = mapped_column(Float, nullable=False)
    grid_power_w: Mapped[float] = mapped_column(Float, nullable=False)
    battery_power_w: Mapped[float] = mapped_column(Float, nullable=False)
    battery_soc_pct: Mapped[float] = mapped_column(Float, nullable=False)
    is_blackout: Mapped[bool] = mapped_column(Boolean, nullable=False)


class PanelWash(Base):
    """
    A day the user washed the site's panels (local Asia/Karachi date): the clean event the live dust model
    (src/soiling/live_model.py) measures soiling from. One row per site and day. Deleted with the site.
    """

    __tablename__ = "panel_washes"

    site_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    washed_on: Mapped[date] = mapped_column(Date, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
