"""Panel washes: the days a user washed their panels, the clean events of the live dust model.

Revision ID: 0003_panel_washes
Revises: 0002_inverter_samples
Create Date: 2026-11-21

One new table, so it is safe on live data. One row per site and local day (the primary key makes a
second wash on the same day a no-op); rows are deleted with their site. Like the other per-site tables it
gets row level security with no policies on Postgres. Downgrade drops the table and the recorded washes.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_panel_washes"
down_revision = "0002_inverter_samples"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "panel_washes",
        sa.Column("site_id", sa.Uuid(), sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("washed_on", sa.Date(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE "panel_washes" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_table("panel_washes")
