"""create auth tables

Revision ID: 20260505_0001
Revises:
Create Date: 2026-05-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260505_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

house_role = sa.Enum("member", "manager", "admin", "read_only", name="houserole")


def upgrade() -> None:
    op.create_table(
        "houses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_houses")),
        sa.UniqueConstraint("name", name=op.f("uq_houses_name")),
    )
    op.create_index(op.f("ix_houses_name"), "houses", ["name"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "house_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("house_id", sa.Integer(), nullable=False),
        sa.Column("role", house_role, nullable=False),
        sa.Column("can_view_house", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["house_id"], ["houses.id"], name=op.f("fk_house_memberships_house_id_houses")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_house_memberships_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_house_memberships")),
    )
    op.create_index(
        op.f("ix_house_memberships_house_id"), "house_memberships", ["house_id"], unique=False
    )
    op.create_index(
        op.f("ix_house_memberships_user_id"), "house_memberships", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_house_memberships_user_id"), table_name="house_memberships")
    op.drop_index(op.f("ix_house_memberships_house_id"), table_name="house_memberships")
    op.drop_table("house_memberships")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_houses_name"), table_name="houses")
    op.drop_table("houses")
    house_role.drop(op.get_bind(), checkfirst=True)
