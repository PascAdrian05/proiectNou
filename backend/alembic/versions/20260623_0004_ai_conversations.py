"""add ai conversations table

Revision ID: 20260623_0004
Revises: 20260618_0003
Create Date: 2026-06-23 23:38:00

"""

from alembic import op
import sqlalchemy as sa
from uuid import uuid4


revision = "20260623_0004"
down_revision = "20260618_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_conversation",
        sa.Column("id", sa.UUID(), nullable=False, default=uuid4),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("conversation_type", sa.String(), nullable=False),
        sa.Column("messages", sa.String(), nullable=False, server_default="[]"),
        sa.Column("context_data", sa.String(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_conversation_user_id", "ai_conversation", ["user_id"])
    op.create_index("ix_ai_conversation_tenant_id", "ai_conversation", ["tenant_id"])
    op.create_index("ix_ai_conversation_conversation_type", "ai_conversation", ["conversation_type"])


def downgrade() -> None:
    op.drop_index("ix_ai_conversation_conversation_type", table_name="ai_conversation")
    op.drop_index("ix_ai_conversation_tenant_id", table_name="ai_conversation")
    op.drop_index("ix_ai_conversation_user_id", table_name="ai_conversation")
    op.drop_table("ai_conversation")