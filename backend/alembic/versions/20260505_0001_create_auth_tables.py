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

denizen_role = sa.Enum("read_only", "member", "manager", "admin", name="denizenrole")


def upgrade() -> None:
    denizen_role.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "kingdoms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kingdoms")),
        sa.UniqueConstraint("name", name=op.f("uq_kingdoms_name")),
    )
    op.create_index(op.f("ix_kingdoms_name"), "kingdoms", ["name"], unique=False)

    op.create_table(
        "houses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kingdom_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["kingdom_id"], ["kingdoms.id"], name=op.f("fk_houses_kingdom_id_kingdoms")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_houses")),
        sa.UniqueConstraint("name", name=op.f("uq_houses_name")),
    )
    op.create_index(op.f("ix_houses_kingdom_id"), "houses", ["kingdom_id"], unique=False)
    op.create_index(op.f("ix_houses_name"), "houses", ["name"], unique=False)

    op.create_table(
        "denizens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("character_name", sa.String(length=120), nullable=True),
        sa.Column("pronouns", sa.String(length=80), nullable=True),
        sa.Column("contact", sa.String(length=255), nullable=True),
        sa.Column("profile_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=True),
        sa.Column("role", denizen_role, nullable=False),
        sa.Column("religion", sa.String(length=120), nullable=True),
        sa.Column("primary_house_id", sa.Integer(), nullable=True),
        sa.Column("primary_kingdom_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_system_account", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["primary_house_id"], ["houses.id"], name=op.f("fk_denizens_primary_house_id_houses")
        ),
        sa.ForeignKeyConstraint(
            ["primary_kingdom_id"],
            ["kingdoms.id"],
            name=op.f("fk_denizens_primary_kingdom_id_kingdoms"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_denizens")),
        sa.UniqueConstraint("email", name=op.f("uq_denizens_email")),
    )
    op.create_index(op.f("ix_denizens_email"), "denizens", ["email"], unique=False)

    op.create_table(
        "audit_ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_denizen_id", sa.Integer(), nullable=True),
        sa.Column("is_system_action", sa.Boolean(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("scope_type", sa.String(length=40), nullable=True),
        sa.Column("scope_id", sa.Integer(), nullable=True),
        sa.Column("item_type", sa.String(length=40), nullable=True),
        sa.Column("item_key", sa.String(length=120), nullable=True),
        sa.Column("amount_delta", sa.Numeric(12, 2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["actor_denizen_id"],
            ["denizens.id"],
            name=op.f("fk_audit_ledger_entries_actor_denizen_id_denizens"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_ledger_entries")),
    )
    op.create_index(
        op.f("ix_audit_ledger_entries_action"),
        "audit_ledger_entries",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_ledger_entries_actor_denizen_id"),
        "audit_ledger_entries",
        ["actor_denizen_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_ledger_entries_item_key"),
        "audit_ledger_entries",
        ["item_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_ledger_entries_item_type"),
        "audit_ledger_entries",
        ["item_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_ledger_entries_scope_id"),
        "audit_ledger_entries",
        ["scope_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_ledger_entries_scope_type"),
        "audit_ledger_entries",
        ["scope_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_ledger_entries_target_id"),
        "audit_ledger_entries",
        ["target_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_ledger_entries_target_type"),
        "audit_ledger_entries",
        ["target_type"],
        unique=False,
    )

    op.create_table(
        "house_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("denizen_id", sa.Integer(), nullable=False),
        sa.Column("house_id", sa.Integer(), nullable=False),
        sa.Column("role", denizen_role, nullable=False),
        sa.Column("can_view_house", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["house_id"], ["houses.id"], name=op.f("fk_house_memberships_house_id_houses")
        ),
        sa.ForeignKeyConstraint(
            ["denizen_id"],
            ["denizens.id"],
            name=op.f("fk_house_memberships_denizen_id_denizens"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_house_memberships")),
    )
    op.create_index(
        op.f("ix_house_memberships_house_id"), "house_memberships", ["house_id"], unique=False
    )
    op.create_index(
        op.f("ix_house_memberships_denizen_id"),
        "house_memberships",
        ["denizen_id"],
        unique=False,
    )

    op.create_table(
        "kingdom_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("denizen_id", sa.Integer(), nullable=False),
        sa.Column("kingdom_id", sa.Integer(), nullable=False),
        sa.Column("role", denizen_role, nullable=False),
        sa.Column("can_view_kingdom", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["denizen_id"],
            ["denizens.id"],
            name=op.f("fk_kingdom_memberships_denizen_id_denizens"),
        ),
        sa.ForeignKeyConstraint(
            ["kingdom_id"],
            ["kingdoms.id"],
            name=op.f("fk_kingdom_memberships_kingdom_id_kingdoms"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kingdom_memberships")),
    )
    op.create_index(
        op.f("ix_kingdom_memberships_denizen_id"),
        "kingdom_memberships",
        ["denizen_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_kingdom_memberships_kingdom_id"),
        "kingdom_memberships",
        ["kingdom_id"],
        unique=False,
    )

    op.create_table(
        "denizen_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("denizen_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=40), nullable=False),
        sa.Column("item_key", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["denizen_id"], ["denizens.id"], name=op.f("fk_denizen_holdings_denizen_id_denizens")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_denizen_holdings")),
    )
    op.create_index(
        op.f("ix_denizen_holdings_denizen_id"), "denizen_holdings", ["denizen_id"], unique=False
    )
    op.create_index(
        op.f("ix_denizen_holdings_item_key"), "denizen_holdings", ["item_key"], unique=False
    )
    op.create_index(
        op.f("ix_denizen_holdings_item_type"), "denizen_holdings", ["item_type"], unique=False
    )

    op.create_table(
        "house_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("house_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=40), nullable=False),
        sa.Column("item_key", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["house_id"], ["houses.id"], name=op.f("fk_house_holdings_house_id_houses")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_house_holdings")),
    )
    op.create_index(
        op.f("ix_house_holdings_house_id"), "house_holdings", ["house_id"], unique=False
    )
    op.create_index(
        op.f("ix_house_holdings_item_key"), "house_holdings", ["item_key"], unique=False
    )
    op.create_index(
        op.f("ix_house_holdings_item_type"), "house_holdings", ["item_type"], unique=False
    )

    op.create_table(
        "house_denizen_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("house_id", sa.Integer(), nullable=False),
        sa.Column("denizen_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=40), nullable=False),
        sa.Column("item_key", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["denizen_id"],
            ["denizens.id"],
            name=op.f("fk_house_denizen_holdings_denizen_id_denizens"),
        ),
        sa.ForeignKeyConstraint(
            ["house_id"], ["houses.id"], name=op.f("fk_house_denizen_holdings_house_id_houses")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_house_denizen_holdings")),
    )
    op.create_index(
        op.f("ix_house_denizen_holdings_denizen_id"),
        "house_denizen_holdings",
        ["denizen_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_house_denizen_holdings_house_id"),
        "house_denizen_holdings",
        ["house_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_house_denizen_holdings_item_key"),
        "house_denizen_holdings",
        ["item_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_house_denizen_holdings_item_type"),
        "house_denizen_holdings",
        ["item_type"],
        unique=False,
    )

    op.create_table(
        "kingdom_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kingdom_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=40), nullable=False),
        sa.Column("item_key", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["kingdom_id"],
            ["kingdoms.id"],
            name=op.f("fk_kingdom_holdings_kingdom_id_kingdoms"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kingdom_holdings")),
    )
    op.create_index(
        op.f("ix_kingdom_holdings_kingdom_id"),
        "kingdom_holdings",
        ["kingdom_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_kingdom_holdings_item_key"), "kingdom_holdings", ["item_key"], unique=False
    )
    op.create_index(
        op.f("ix_kingdom_holdings_item_type"), "kingdom_holdings", ["item_type"], unique=False
    )

    op.create_table(
        "three_crowns_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_type", sa.String(length=40), nullable=False),
        sa.Column("denizen_id", sa.Integer(), nullable=True),
        sa.Column("house_id", sa.Integer(), nullable=True),
        sa.Column("kingdom_id", sa.Integer(), nullable=True),
        sa.Column("item_type", sa.String(length=40), nullable=False),
        sa.Column("item_key", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["denizen_id"],
            ["denizens.id"],
            name=op.f("fk_three_crowns_holdings_denizen_id_denizens"),
        ),
        sa.ForeignKeyConstraint(
            ["house_id"], ["houses.id"], name=op.f("fk_three_crowns_holdings_house_id_houses")
        ),
        sa.ForeignKeyConstraint(
            ["kingdom_id"],
            ["kingdoms.id"],
            name=op.f("fk_three_crowns_holdings_kingdom_id_kingdoms"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_three_crowns_holdings")),
    )
    op.create_index(
        op.f("ix_three_crowns_holdings_account_type"),
        "three_crowns_holdings",
        ["account_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_three_crowns_holdings_denizen_id"),
        "three_crowns_holdings",
        ["denizen_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_three_crowns_holdings_house_id"),
        "three_crowns_holdings",
        ["house_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_three_crowns_holdings_kingdom_id"),
        "three_crowns_holdings",
        ["kingdom_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_three_crowns_holdings_item_key"),
        "three_crowns_holdings",
        ["item_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_three_crowns_holdings_item_type"),
        "three_crowns_holdings",
        ["item_type"],
        unique=False,
    )

    op.create_table(
        "permission_grants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grantor_denizen_id", sa.Integer(), nullable=False),
        sa.Column("grantee_denizen_id", sa.Integer(), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=120), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["grantee_denizen_id"],
            ["denizens.id"],
            name=op.f("fk_permission_grants_grantee_denizen_id_denizens"),
        ),
        sa.ForeignKeyConstraint(
            ["grantor_denizen_id"],
            ["denizens.id"],
            name=op.f("fk_permission_grants_grantor_denizen_id_denizens"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permission_grants")),
    )
    op.create_index(
        op.f("ix_permission_grants_grantee_denizen_id"),
        "permission_grants",
        ["grantee_denizen_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permission_grants_grantor_denizen_id"),
        "permission_grants",
        ["grantor_denizen_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permission_grants_permission"),
        "permission_grants",
        ["permission"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permission_grants_scope_id"),
        "permission_grants",
        ["scope_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_permission_grants_scope_type"),
        "permission_grants",
        ["scope_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_permission_grants_scope_type"), table_name="permission_grants")
    op.drop_index(op.f("ix_permission_grants_scope_id"), table_name="permission_grants")
    op.drop_index(op.f("ix_permission_grants_permission"), table_name="permission_grants")
    op.drop_index(op.f("ix_permission_grants_grantor_denizen_id"), table_name="permission_grants")
    op.drop_index(op.f("ix_permission_grants_grantee_denizen_id"), table_name="permission_grants")
    op.drop_table("permission_grants")
    op.drop_index(op.f("ix_three_crowns_holdings_item_type"), table_name="three_crowns_holdings")
    op.drop_index(op.f("ix_three_crowns_holdings_item_key"), table_name="three_crowns_holdings")
    op.drop_index(op.f("ix_three_crowns_holdings_kingdom_id"), table_name="three_crowns_holdings")
    op.drop_index(op.f("ix_three_crowns_holdings_house_id"), table_name="three_crowns_holdings")
    op.drop_index(op.f("ix_three_crowns_holdings_denizen_id"), table_name="three_crowns_holdings")
    op.drop_index(op.f("ix_three_crowns_holdings_account_type"), table_name="three_crowns_holdings")
    op.drop_table("three_crowns_holdings")
    op.drop_index(op.f("ix_kingdom_holdings_item_type"), table_name="kingdom_holdings")
    op.drop_index(op.f("ix_kingdom_holdings_item_key"), table_name="kingdom_holdings")
    op.drop_index(op.f("ix_kingdom_holdings_kingdom_id"), table_name="kingdom_holdings")
    op.drop_table("kingdom_holdings")
    op.drop_index(op.f("ix_house_holdings_item_type"), table_name="house_holdings")
    op.drop_index(op.f("ix_house_denizen_holdings_item_type"), table_name="house_denizen_holdings")
    op.drop_index(op.f("ix_house_denizen_holdings_item_key"), table_name="house_denizen_holdings")
    op.drop_index(op.f("ix_house_denizen_holdings_house_id"), table_name="house_denizen_holdings")
    op.drop_index(op.f("ix_house_denizen_holdings_denizen_id"), table_name="house_denizen_holdings")
    op.drop_table("house_denizen_holdings")
    op.drop_index(op.f("ix_house_holdings_item_key"), table_name="house_holdings")
    op.drop_index(op.f("ix_house_holdings_house_id"), table_name="house_holdings")
    op.drop_table("house_holdings")
    op.drop_index(op.f("ix_denizen_holdings_item_type"), table_name="denizen_holdings")
    op.drop_index(op.f("ix_denizen_holdings_item_key"), table_name="denizen_holdings")
    op.drop_index(op.f("ix_denizen_holdings_denizen_id"), table_name="denizen_holdings")
    op.drop_table("denizen_holdings")
    op.drop_index(op.f("ix_kingdom_memberships_kingdom_id"), table_name="kingdom_memberships")
    op.drop_index(op.f("ix_kingdom_memberships_denizen_id"), table_name="kingdom_memberships")
    op.drop_table("kingdom_memberships")
    op.drop_index(op.f("ix_house_memberships_denizen_id"), table_name="house_memberships")
    op.drop_index(op.f("ix_house_memberships_house_id"), table_name="house_memberships")
    op.drop_table("house_memberships")
    op.drop_index(op.f("ix_audit_ledger_entries_target_type"), table_name="audit_ledger_entries")
    op.drop_index(op.f("ix_audit_ledger_entries_target_id"), table_name="audit_ledger_entries")
    op.drop_index(op.f("ix_audit_ledger_entries_scope_type"), table_name="audit_ledger_entries")
    op.drop_index(op.f("ix_audit_ledger_entries_scope_id"), table_name="audit_ledger_entries")
    op.drop_index(op.f("ix_audit_ledger_entries_item_type"), table_name="audit_ledger_entries")
    op.drop_index(op.f("ix_audit_ledger_entries_item_key"), table_name="audit_ledger_entries")
    op.drop_index(
        op.f("ix_audit_ledger_entries_actor_denizen_id"), table_name="audit_ledger_entries"
    )
    op.drop_index(op.f("ix_audit_ledger_entries_action"), table_name="audit_ledger_entries")
    op.drop_table("audit_ledger_entries")
    op.drop_index(op.f("ix_denizens_email"), table_name="denizens")
    op.drop_table("denizens")
    op.drop_index(op.f("ix_houses_name"), table_name="houses")
    op.drop_index(op.f("ix_houses_kingdom_id"), table_name="houses")
    op.drop_table("houses")
    op.drop_index(op.f("ix_kingdoms_name"), table_name="kingdoms")
    op.drop_table("kingdoms")
    denizen_role.drop(op.get_bind(), checkfirst=True)
