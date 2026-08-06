"""add sync_runs.phase for live progress tracking

Revision ID: 003
Revises: 002
Create Date: 2026-07-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite batch mode is required for ALTER TABLE ADD COLUMN.
    with op.batch_alter_table("sync_runs") as batch_op:
        batch_op.add_column(sa.Column("phase", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sync_runs") as batch_op:
        batch_op.drop_column("phase")
