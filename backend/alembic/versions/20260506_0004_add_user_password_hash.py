"""add denizen password hash

Revision ID: 20260506_0004
Revises: 20260505_0003
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260506_0004"
down_revision: str | Sequence[str] | None = "20260505_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("denizens", sa.Column("password_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("denizens", "password_hash")
