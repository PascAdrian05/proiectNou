"""add 2fa fields

Revision ID: 20260625_0005
Revises: 20260623_0004
Create Date: 2025-06-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlmodel import SQLModel


# revision identifiers, used by Alembic.
revision = '20260625_0005'
down_revision = '20260623_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 2FA fields to user table
    op.add_column('user', sa.Column('totp_secret', sa.String(), nullable=True))
    op.add_column('user', sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    # Remove 2FA fields from user table
    op.drop_column('user', 'totp_enabled')
    op.drop_column('user', 'totp_secret')
