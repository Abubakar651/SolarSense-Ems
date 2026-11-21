"""Per-site inverter telemetry: inverter address on sites, one station owner, and inverter_samples.

Revision ID: 0002_inverter_samples
Revises: 0001_accounts
Create Date: 2026-11-21

Multi-tenancy for telemetry. Each site gets its own inverter address and its own samples (deleted with the
site). The recorded station dataset LHR-RES-01 used to be every site's default; it now belongs to at most
one site: the site of the account named by STATION_OWNER_EMAIL (read from the environment or .env, like
the API), and only if that account's email is verified. Unset or unmatched, no site gets it. Every other
site's station_code becomes NULL, so it only sees its own data.

Safe on live data: one new nullable column, a new table, and station_code values cleared before the unique
index is added. Downgrade restores the old default (every site back on LHR-RES-01) and drops the rest.
Like the account tables, inverter_samples gets row level security with no policies on Postgres.
"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa

revision = "0002_inverter_samples"
down_revision = "0001_accounts"
branch_labels = None
depends_on = None

STATION_CODE = "LHR-RES-01"


def upgrade() -> None:
    with op.batch_alter_table("sites") as batch:
        batch.add_column(sa.Column("inverter_host", sa.String(45), nullable=True))
        batch.alter_column("station_code", existing_type=sa.String(32), nullable=True)

    sites = sa.table(
        "sites",
        sa.column("id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("station_code", sa.String()),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("email", sa.String()),
        sa.column("email_verified_at", sa.DateTime(timezone=True)),
    )
    bind = op.get_bind()
    owner_email = os.environ.get("STATION_OWNER_EMAIL", "").strip().lower()
    owner = None
    if owner_email:
        owner = bind.execute(
            sa.select(sites.c.id)
            .join(users, users.c.id == sites.c.user_id)
            .where(sa.func.lower(users.c.email) == owner_email, users.c.email_verified_at.is_not(None))
        ).scalar()
    bind.execute(sa.update(sites).values(station_code=None))
    if owner is not None:
        bind.execute(sa.update(sites).where(sites.c.id == owner).values(station_code=STATION_CODE))

    with op.batch_alter_table("sites") as batch:
        batch.create_unique_constraint("uq_sites_station_code", ["station_code"])

    op.create_table(
        "inverter_samples",
        sa.Column("site_id", sa.Uuid(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("pv_power_w", sa.Float(), nullable=False),
        sa.Column("load_power_w", sa.Float(), nullable=False),
        sa.Column("grid_power_w", sa.Float(), nullable=False),
        sa.Column("battery_power_w", sa.Float(), nullable=False),
        sa.Column("battery_soc_pct", sa.Float(), nullable=False),
        sa.Column("is_blackout", sa.Boolean(), nullable=False),
    )
    if bind.dialect.name == "postgresql":
        op.execute('ALTER TABLE "inverter_samples" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_table("inverter_samples")
    with op.batch_alter_table("sites") as batch:
        batch.drop_constraint("uq_sites_station_code", type_="unique")
    sites = sa.table("sites", sa.column("station_code", sa.String()))
    op.get_bind().execute(sa.update(sites).where(sites.c.station_code.is_(None)).values(station_code=STATION_CODE))
    with op.batch_alter_table("sites") as batch:
        batch.alter_column("station_code", existing_type=sa.String(32), nullable=False)
        batch.drop_column("inverter_host")
