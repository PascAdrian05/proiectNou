"""add scan limits columns

Revision ID: 613546f1f0c5
Revises: 20260626_0008
Create Date: 2026-06-26 09:44:21.100626

"""
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '613546f1f0c5'
down_revision = '20260626_0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scan limit columns to subscription table
    op.add_column('subscription', sa.Column('scans_used', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('subscription', sa.Column('scans_limit', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('subscription', sa.Column('scan_limit_reset_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove scan limit columns from subscription table
    op.drop_column('subscription', 'scan_limit_reset_at')
    op.drop_column('subscription', 'scans_limit')
    op.drop_column('subscription', 'scans_used')
