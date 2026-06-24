"""add stripe events table

Revision ID: 20260618_0002
Revises: 20260617_0001
Create Date: 2026-06-18 00:00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260618_0002"
down_revision = "20260617_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stripeevent",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("payload_json", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_stripeevent_event_id", "stripeevent", ["event_id"], unique=True)
    op.create_index("ix_stripeevent_event_type", "stripeevent", ["event_type"], unique=False)
    op.create_index("ix_stripeevent_processed", "stripeevent", ["processed"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stripeevent_processed", table_name="stripeevent")
    op.drop_index("ix_stripeevent_event_type", table_name="stripeevent")
    op.drop_index("ix_stripeevent_event_id", table_name="stripeevent")
    op.drop_table("stripeevent")
