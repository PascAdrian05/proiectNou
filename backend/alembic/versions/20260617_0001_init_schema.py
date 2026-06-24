"""initial schema

Revision ID: 20260617_0001
Revises: None
Create Date: 2026-06-17 00:00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260617_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("alert_email", sa.String(), nullable=True),
        sa.Column("alert_webhook_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_name", "tenant", ["name"], unique=False)

    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=False)
    op.create_index("ix_user_role", "user", ["role"], unique=False)
    op.create_index("ix_user_tenant_id", "user", ["tenant_id"], unique=False)

    op.create_table(
        "subscription",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id"),
    )
    op.create_index("ix_subscription_stripe_customer_id", "subscription", ["stripe_customer_id"], unique=False)
    op.create_index("ix_subscription_stripe_subscription_id", "subscription", ["stripe_subscription_id"], unique=False)
    op.create_index("ix_subscription_tenant_id", "subscription", ["tenant_id"], unique=True)

    op.create_table(
        "website",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("ownership_verified", sa.Boolean(), nullable=False),
        sa.Column("scan_frequency_minutes", sa.Integer(), nullable=False),
        sa.Column("last_scan_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_website_domain", "website", ["domain"], unique=False)
    op.create_index("ix_website_tenant_id", "website", ["tenant_id"], unique=False)

    op.create_table(
        "scanrun",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("celery_task_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("result_json", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["website_id"], ["website.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scanrun_celery_task_id", "scanrun", ["celery_task_id"], unique=False)
    op.create_index("ix_scanrun_status", "scanrun", ["status"], unique=False)
    op.create_index("ix_scanrun_tenant_id", "scanrun", ["tenant_id"], unique=False)
    op.create_index("ix_scanrun_website_id", "scanrun", ["website_id"], unique=False)

    op.create_table(
        "finding",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("details_json", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["scan_run_id"], ["scanrun.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["website_id"], ["website.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finding_kind", "finding", ["kind"], unique=False)
    op.create_index("ix_finding_scan_run_id", "finding", ["scan_run_id"], unique=False)
    op.create_index("ix_finding_severity", "finding", ["severity"], unique=False)
    op.create_index("ix_finding_status", "finding", ["status"], unique=False)
    op.create_index("ix_finding_tenant_id", "finding", ["tenant_id"], unique=False)
    op.create_index("ix_finding_website_id", "finding", ["website_id"], unique=False)

    op.create_table(
        "alert",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["finding.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_channel", "alert", ["channel"], unique=False)
    op.create_index("ix_alert_finding_id", "alert", ["finding_id"], unique=False)
    op.create_index("ix_alert_status", "alert", ["status"], unique=False)
    op.create_index("ix_alert_tenant_id", "alert", ["tenant_id"], unique=False)

    op.create_table(
        "oauthaccount",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_user_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )
    op.create_index("ix_oauthaccount_provider", "oauthaccount", ["provider"], unique=False)
    op.create_index("ix_oauthaccount_provider_user_id", "oauthaccount", ["provider_user_id"], unique=False)
    op.create_index("ix_oauthaccount_user_id", "oauthaccount", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_oauthaccount_user_id", table_name="oauthaccount")
    op.drop_index("ix_oauthaccount_provider_user_id", table_name="oauthaccount")
    op.drop_index("ix_oauthaccount_provider", table_name="oauthaccount")
    op.drop_table("oauthaccount")

    op.drop_index("ix_alert_tenant_id", table_name="alert")
    op.drop_index("ix_alert_status", table_name="alert")
    op.drop_index("ix_alert_finding_id", table_name="alert")
    op.drop_index("ix_alert_channel", table_name="alert")
    op.drop_table("alert")

    op.drop_index("ix_finding_website_id", table_name="finding")
    op.drop_index("ix_finding_tenant_id", table_name="finding")
    op.drop_index("ix_finding_status", table_name="finding")
    op.drop_index("ix_finding_severity", table_name="finding")
    op.drop_index("ix_finding_scan_run_id", table_name="finding")
    op.drop_index("ix_finding_kind", table_name="finding")
    op.drop_table("finding")

    op.drop_index("ix_scanrun_website_id", table_name="scanrun")
    op.drop_index("ix_scanrun_tenant_id", table_name="scanrun")
    op.drop_index("ix_scanrun_status", table_name="scanrun")
    op.drop_index("ix_scanrun_celery_task_id", table_name="scanrun")
    op.drop_table("scanrun")

    op.drop_index("ix_website_tenant_id", table_name="website")
    op.drop_index("ix_website_domain", table_name="website")
    op.drop_table("website")

    op.drop_index("ix_subscription_tenant_id", table_name="subscription")
    op.drop_index("ix_subscription_stripe_subscription_id", table_name="subscription")
    op.drop_index("ix_subscription_stripe_customer_id", table_name="subscription")
    op.drop_table("subscription")

    op.drop_index("ix_user_tenant_id", table_name="user")
    op.drop_index("ix_user_role", table_name="user")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")

    op.drop_index("ix_tenant_name", table_name="tenant")
    op.drop_table("tenant")
