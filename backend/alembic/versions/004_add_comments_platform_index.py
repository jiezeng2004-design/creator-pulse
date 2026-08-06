"""add comments platform_comment_id index

Revision ID: 004
Revises: 003
Create Date: 2026-08-05
"""

from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The ORM model declares platform_comment_id as indexed; migration 001
    # never created it, so alembic-created databases diverge from
    # create_all-created ones. Add the missing index.
    op.create_index(
        "ix_comments_platform_comment_id",
        "comments",
        ["platform_comment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_comments_platform_comment_id", table_name="comments")
