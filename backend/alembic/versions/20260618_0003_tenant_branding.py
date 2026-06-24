"""tenant branding settings

Revision ID: 20260618_0003
Revises: 20260618_0002
Create Date: 2026-06-18 00:30:00

"""

from alembic import op
import sqlalchemy as sa


revision = "20260618_0003"
down_revision = "20260618_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenant", sa.Column("brand_name", sa.String(), nullable=True))
    op.add_column("tenant", sa.Column("brand_logo_url", sa.String(), nullable=True))
    op.add_column("tenant", sa.Column("report_primary_color", sa.String(), nullable=True))
    op.add_column("tenant", sa.Column("report_base_url", sa.String(), nullable=True))
    op.add_column("tenant", sa.Column("report_cta_text", sa.String(), nullable=True))
    op.add_column("tenant", sa.Column("report_cta_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant", "report_cta_url")
    op.drop_column("tenant", "report_cta_text")
    op.drop_column("tenant", "report_base_url")
    op.drop_column("tenant", "report_primary_color")
    op.drop_column("tenant", "brand_logo_url")
    op.drop_column("tenant", "brand_name")
