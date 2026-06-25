"""add security fields (backup_codes, security_setup, passkey)

Revision ID: 20260626_0007
Revises: 20260625_0006
Create Date: 2026-06-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlmodel import SQLModel


# revision identifiers, used by Alembic.
revision = '20260626_0007'
down_revision = '20260625_0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add security fields to user table
    op.add_column('user', sa.Column('backup_codes', sa.String(), nullable=True))
    op.add_column('user', sa.Column('security_setup_completed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('user', sa.Column('passkey_enabled', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    # Remove security fields from user table
    op.drop_column('user', 'passkey_enabled')
    op.drop_column('user', 'security_setup_completed')
    op.drop_column('user', 'backup_codes')