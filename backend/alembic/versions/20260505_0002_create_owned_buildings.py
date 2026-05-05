"""create owned buildings

Revision ID: 20260505_0002
Revises: 20260505_0001
Create Date: 2026-05-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260505_0002"
down_revision: str | Sequence[str] | None = "20260505_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "owned_buildings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("house_id", sa.Integer(), nullable=True),
        sa.Column("building_definition_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["house_id"], ["houses.id"], name=op.f("fk_owned_buildings_house_id_houses")
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], name=op.f("fk_owned_buildings_owner_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_owned_buildings")),
    )
    op.create_index(
        op.f("ix_owned_buildings_building_definition_id"),
        "owned_buildings",
        ["building_definition_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_owned_buildings_house_id"), "owned_buildings", ["house_id"], unique=False
    )
    op.create_index(
        op.f("ix_owned_buildings_owner_user_id"), "owned_buildings", ["owner_user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_owned_buildings_owner_user_id"), table_name="owned_buildings")
    op.drop_index(op.f("ix_owned_buildings_house_id"), table_name="owned_buildings")
    op.drop_index(op.f("ix_owned_buildings_building_definition_id"), table_name="owned_buildings")
    op.drop_table("owned_buildings")
