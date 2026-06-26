"""add scan progress columns (current_step, progress)

Revision ID: 20260626_0009
Revises: 613546f1f0c5
Create Date: 2026-06-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260626_0009'
down_revision = '613546f1f0c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('scanrun', sa.Column('current_step', sa.String(), nullable=True))
    op.add_column('scanrun', sa.Column('progress', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('scanrun', 'progress')
    op.drop_column('scanrun', 'current_step')
