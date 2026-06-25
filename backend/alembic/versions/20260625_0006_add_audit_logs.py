"""add audit logs

Revision ID: 20260625_0006
Revises: 20260625_0005
Create Date: 2025-06-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260625_0006'
down_revision = '20260625_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'auditlog',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(), nullable=True),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('details', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_auditlog_action'), 'auditlog', ['action'], unique=False)
    op.create_index(op.f('ix_auditlog_created_at'), 'auditlog', ['created_at'], unique=False)
    op.create_index(op.f('ix_auditlog_resource_type'), 'auditlog', ['resource_type'], unique=False)
    op.create_index(op.f('ix_auditlog_tenant_id'), 'auditlog', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_auditlog_user_id'), 'auditlog', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_auditlog_user_id'), table_name='auditlog')
    op.drop_index(op.f('ix_auditlog_tenant_id'), table_name='auditlog')
    op.drop_index(op.f('ix_auditlog_resource_type'), table_name='auditlog')
    op.drop_index(op.f('ix_auditlog_created_at'), table_name='auditlog')
    op.drop_index(op.f('ix_auditlog_action'), table_name='auditlog')
    op.drop_table('auditlog')
