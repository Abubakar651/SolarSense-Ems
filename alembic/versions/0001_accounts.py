"""Create account, site, preference and alert tables.

Revision ID: 0001_accounts
Revises:
Create Date: 2026-11-18

On Postgres (Supabase) every table gets row level security switched on with no policies. FastAPI
connects as the database owner, which bypasses RLS, while Supabase's public REST API (anon and
authenticated keys) can then read nothing, including password hashes.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_accounts"
down_revision = None
branch_labels = None
depends_on = None

TABLES = (
    "users",
    "action_tokens",
    "sites",
    "blackout_windows",
    "notification_prefs",
    "report_prefs",
    "alerts",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(100), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "action_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("purpose IN ('verify_email', 'reset_password')", name="ck_action_tokens_purpose"),
    )
    op.create_index("ix_action_tokens_user_id", "action_tokens", ["user_id"])
    op.create_table(
        "sites",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("address", sa.String(200), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("pv_kwp", sa.Numeric(8, 2), nullable=False),
        sa.Column("battery_kwh", sa.Numeric(8, 2), nullable=False),
        sa.Column("inverter_make", sa.String(32), nullable=False),
        sa.Column("inverter_serial", sa.String(64), nullable=False),
        sa.Column("station_code", sa.String(32), nullable=False),
        sa.Column("reserve_pct", sa.Integer(), nullable=False),
        sa.Column("tariff_category", sa.String(32), nullable=False),
        sa.Column("prosumer_regime", sa.String(48), nullable=False),
        sa.Column("sanctioned_load_kw", sa.Numeric(8, 2), nullable=False),
        sa.Column("is_atl_filer", sa.Boolean(), nullable=False),
        sa.Column("include_electricity_duty", sa.Boolean(), nullable=False),
        sa.Column("is_protected_consumer", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("reserve_pct BETWEEN 15 AND 100", name="ck_sites_reserve_pct"),
        sa.CheckConstraint("pv_kwp > 0", name="ck_sites_pv_kwp"),
        sa.CheckConstraint("battery_kwh > 0", name="ck_sites_battery_kwh"),
        sa.CheckConstraint("sanctioned_load_kw > 0", name="ck_sites_sanctioned_load_kw"),
    )
    op.create_table(
        "blackout_windows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("site_id", sa.Uuid(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
    )
    op.create_index("ix_blackout_windows_site_id", "blackout_windows", ["site_id"])
    op.create_table(
        "notification_prefs",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("alert_key", sa.String(32), primary_key=True),
        sa.Column("in_app", sa.Boolean(), nullable=False),
        sa.Column("email", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "report_prefs",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("monthly", sa.Boolean(), nullable=False),
        sa.Column("weekly", sa.Boolean(), nullable=False),
        sa.Column("send_to", sa.String(254), nullable=False),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(8), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("severity IN ('crit', 'warn', 'info', 'ok')", name="ck_alerts_severity"),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])

    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
