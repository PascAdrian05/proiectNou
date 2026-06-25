"""add credentials table for WebAuthn passkeys

Revision ID: 20260626_0008
Revises: 20260626_0007
Create Date: 2026-06-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlmodel import SQLModel
from uuid import uuid4


# revision identifiers, used by Alembic.
revision = '20260626_0008'
down_revision = '20260626_0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'credential',
        sa.Column('id', sa.Uuid(), nullable=False, primary_key=True, default=uuid4),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('user.id'), nullable=False, index=True),
        sa.Column('credential_id', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('public_key', sa.String(), nullable=False),
        sa.Column('sign_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('transports', sa.String(), nullable=True),
        sa.Column('device_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('credential')