"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("platform_user_id", sa.String(length=128), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("account_status", sa.String(length=32), nullable=False),
        sa.Column("authentication_type", sa.String(length=32), nullable=False),
        sa.Column("browser_profile_path", sa.Text(), nullable=True),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("is_mock", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("feature_flags_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "platform_user_id", name="uq_platform_user"),
    )
    op.create_index("ix_platform_accounts_platform", "platform_accounts", ["platform"])
    op.create_index("ix_platform_accounts_account_status", "platform_accounts", ["account_status"])

    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enable_scheduled_sync", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("sync_max_posts", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("data_retention_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("dev_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enable_mock_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("data_dir_display", sa.Text(), nullable=True),
        sa.Column("browser_profiles_dir_display", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("platform_post_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("post_url", sa.Text(), nullable=True),
        sa.Column("post_type", sa.String(length=64), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("impression_count", sa.Integer(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("favorite_count", sa.Integer(), nullable=True),
        sa.Column("share_count", sa.Integer(), nullable=True),
        sa.Column("repost_count", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.Column("raw_metrics_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["platform_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "platform_post_id", name="uq_account_post"),
    )
    op.create_index("ix_posts_account_id", "posts", ["account_id"])
    op.create_index("ix_posts_platform_post_id", "posts", ["platform_post_id"])

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("sync_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posts_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("diagnostic_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["platform_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_runs_account_id", "sync_runs", ["account_id"])
    op.create_index("ix_sync_runs_platform", "sync_runs", ["platform"])
    op.create_index("ix_sync_runs_status", "sync_runs", ["status"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("platform_comment_id", sa.String(length=128), nullable=False),
        sa.Column("parent_comment_id", sa.String(length=128), nullable=True),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("author_platform_id", sa.String(length=128), nullable=True),
        sa.Column("author_avatar_url", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("comment_url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("platform_reply_count", sa.Integer(), nullable=True),
        sa.Column("local_status", sa.String(length=32), nullable=False),
        sa.Column("replied_by_owner", sa.Boolean(), nullable=True),
        sa.Column("owner_reply_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("raw_data_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["platform_accounts.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "platform_comment_id", name="uq_account_comment"),
    )
    op.create_index("ix_comments_post_id", "comments", ["post_id"])
    op.create_index("ix_comments_account_id", "comments", ["account_id"])
    op.create_index("ix_comments_local_status", "comments", ["local_status"])

    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("impression_count", sa.Integer(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("favorite_count", sa.Integer(), nullable=True),
        sa.Column("share_count", sa.Integer(), nullable=True),
        sa.Column("repost_count", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metric_snapshots_post_id", "metric_snapshots", ["post_id"])
    op.create_index("ix_metric_snapshots_captured_at", "metric_snapshots", ["captured_at"])


def downgrade() -> None:
    op.drop_table("metric_snapshots")
    op.drop_table("comments")
    op.drop_table("sync_runs")
    op.drop_table("posts")
    op.drop_table("app_settings")
    op.drop_table("platform_accounts")
