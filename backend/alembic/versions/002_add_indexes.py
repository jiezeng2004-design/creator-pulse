"""add composite and missing indexes

Revision ID: 002
Revises: 001
Create Date: 2026-07-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # posts.published_at -- supports chronological feed queries
    op.create_index("ix_posts_published_at", "posts", ["published_at"])

    # posts: composite (account_id, published_at) -- supports
    # "recent posts for account X" range scans in a single index
    op.create_index(
        "ix_posts_account_id_published_at",
        "posts",
        ["account_id", "published_at"],
    )

    # comments.published_at -- supports chronological comment listing
    op.create_index("ix_comments_published_at", "comments", ["published_at"])

    # metric_snapshots: composite (post_id, captured_at) -- supports
    # trend queries that filter by post and sort by capture time
    op.create_index(
        "ix_metric_snapshots_post_id_captured_at",
        "metric_snapshots",
        ["post_id", "captured_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_metric_snapshots_post_id_captured_at", table_name="metric_snapshots")
    op.drop_index("ix_comments_published_at", table_name="comments")
    op.drop_index("ix_posts_account_id_published_at", table_name="posts")
    op.drop_index("ix_posts_published_at", table_name="posts")
