"""create rules import tables

Revision ID: 20260505_0003
Revises: 20260505_0002
Create Date: 2026-05-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260505_0003"
down_revision: str | Sequence[str] | None = "20260505_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rulesets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rulesets")),
        sa.UniqueConstraint("game", "version", name="uq_rulesets_game_version"),
    )

    op.create_table(
        "rule_currencies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("copper_value", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ruleset_id"], ["rulesets.id"], name=op.f("fk_rule_currencies_ruleset_id_rulesets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_currencies")),
        sa.UniqueConstraint("ruleset_id", "key", name="uq_rule_currencies_ruleset_id_key"),
    )
    op.create_index(op.f("ix_rule_currencies_key"), "rule_currencies", ["key"], unique=False)
    op.create_index(
        op.f("ix_rule_currencies_ruleset_id"), "rule_currencies", ["ruleset_id"], unique=False
    )

    op.create_table(
        "rule_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(
            ["ruleset_id"], ["rulesets.id"], name=op.f("fk_rule_resources_ruleset_id_rulesets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_resources")),
        sa.UniqueConstraint("ruleset_id", "key", name="uq_rule_resources_ruleset_id_key"),
    )
    op.create_index(op.f("ix_rule_resources_key"), "rule_resources", ["key"], unique=False)
    op.create_index(
        op.f("ix_rule_resources_ruleset_id"), "rule_resources", ["ruleset_id"], unique=False
    )

    op.create_table(
        "rule_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("attack", sa.Integer(), nullable=True),
        sa.Column("defense", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ruleset_id"], ["rulesets.id"], name=op.f("fk_rule_units_ruleset_id_rulesets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_units")),
        sa.UniqueConstraint("ruleset_id", "key", name="uq_rule_units_ruleset_id_key"),
    )
    op.create_index(op.f("ix_rule_units_key"), "rule_units", ["key"], unique=False)
    op.create_index(op.f("ix_rule_units_ruleset_id"), "rule_units", ["ruleset_id"], unique=False)

    op.create_table(
        "rule_settlement_tiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("min_buildings", sa.Integer(), nullable=False),
        sa.Column("max_buildings", sa.Integer(), nullable=False),
        sa.Column("upgrade_cost_json", sa.JSON(), nullable=False),
        sa.Column("upkeep_json", sa.JSON(), nullable=False),
        sa.Column("prerequisites_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ruleset_id"],
            ["rulesets.id"],
            name=op.f("fk_rule_settlement_tiers_ruleset_id_rulesets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_settlement_tiers")),
        sa.UniqueConstraint("ruleset_id", "key", name="uq_rule_settlement_tiers_ruleset_id_key"),
    )
    op.create_index(
        op.f("ix_rule_settlement_tiers_key"), "rule_settlement_tiers", ["key"], unique=False
    )
    op.create_index(
        op.f("ix_rule_settlement_tiers_ruleset_id"),
        "rule_settlement_tiers",
        ["ruleset_id"],
        unique=False,
    )

    op.create_table(
        "rule_building_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("map_visible", sa.Boolean(), nullable=False),
        sa.Column("settlement_requirement", sa.String(length=80), nullable=True),
        sa.Column("requirements_json", sa.JSON(), nullable=False),
        sa.Column("effects_json", sa.JSON(), nullable=False),
        sa.Column("build_cost_json", sa.JSON(), nullable=False),
        sa.Column("upkeep_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ruleset_id"],
            ["rulesets.id"],
            name=op.f("fk_rule_building_definitions_ruleset_id_rulesets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_building_definitions")),
        sa.UniqueConstraint(
            "ruleset_id", "key", name="uq_rule_building_definitions_ruleset_id_key"
        ),
    )
    op.create_index(
        op.f("ix_rule_building_definitions_category"),
        "rule_building_definitions",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rule_building_definitions_key"), "rule_building_definitions", ["key"], unique=False
    )
    op.create_index(
        op.f("ix_rule_building_definitions_ruleset_id"),
        "rule_building_definitions",
        ["ruleset_id"],
        unique=False,
    )

    op.create_table(
        "rule_production_recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("building_key", sa.String(length=80), nullable=False),
        sa.Column("recipe_type", sa.String(length=80), nullable=False),
        sa.Column("inputs_json", sa.JSON(), nullable=False),
        sa.Column("outputs_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ruleset_id"],
            ["rulesets.id"],
            name=op.f("fk_rule_production_recipes_ruleset_id_rulesets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_production_recipes")),
        sa.UniqueConstraint("ruleset_id", "key", name="uq_rule_production_recipes_ruleset_id_key"),
    )
    op.create_index(
        op.f("ix_rule_production_recipes_building_key"),
        "rule_production_recipes",
        ["building_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rule_production_recipes_key"), "rule_production_recipes", ["key"], unique=False
    )
    op.create_index(
        op.f("ix_rule_production_recipes_ruleset_id"),
        "rule_production_recipes",
        ["ruleset_id"],
        unique=False,
    )

    op.create_table(
        "rule_ownership_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("allowed_json", sa.JSON(), nullable=False),
        sa.Column("not_allowed_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ruleset_id"],
            ["rulesets.id"],
            name=op.f("fk_rule_ownership_rules_ruleset_id_rulesets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_ownership_rules")),
        sa.UniqueConstraint(
            "ruleset_id", "entity_type", name="uq_rule_ownership_rules_ruleset_id_entity_type"
        ),
    )
    op.create_index(
        op.f("ix_rule_ownership_rules_entity_type"),
        "rule_ownership_rules",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rule_ownership_rules_ruleset_id"),
        "rule_ownership_rules",
        ["ruleset_id"],
        unique=False,
    )

    op.create_table(
        "rule_transports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ruleset_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("transport_type", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ruleset_id"], ["rulesets.id"], name=op.f("fk_rule_transports_ruleset_id_rulesets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_transports")),
        sa.UniqueConstraint("ruleset_id", "key", name="uq_rule_transports_ruleset_id_key"),
    )
    op.create_index(op.f("ix_rule_transports_key"), "rule_transports", ["key"], unique=False)
    op.create_index(
        op.f("ix_rule_transports_ruleset_id"), "rule_transports", ["ruleset_id"], unique=False
    )
    op.create_index(
        op.f("ix_rule_transports_transport_type"),
        "rule_transports",
        ["transport_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rule_transports_transport_type"), table_name="rule_transports")
    op.drop_index(op.f("ix_rule_transports_ruleset_id"), table_name="rule_transports")
    op.drop_index(op.f("ix_rule_transports_key"), table_name="rule_transports")
    op.drop_table("rule_transports")
    op.drop_index(op.f("ix_rule_ownership_rules_ruleset_id"), table_name="rule_ownership_rules")
    op.drop_index(op.f("ix_rule_ownership_rules_entity_type"), table_name="rule_ownership_rules")
    op.drop_table("rule_ownership_rules")
    op.drop_index(
        op.f("ix_rule_production_recipes_ruleset_id"), table_name="rule_production_recipes"
    )
    op.drop_index(op.f("ix_rule_production_recipes_key"), table_name="rule_production_recipes")
    op.drop_index(
        op.f("ix_rule_production_recipes_building_key"), table_name="rule_production_recipes"
    )
    op.drop_table("rule_production_recipes")
    op.drop_index(
        op.f("ix_rule_building_definitions_ruleset_id"), table_name="rule_building_definitions"
    )
    op.drop_index(op.f("ix_rule_building_definitions_key"), table_name="rule_building_definitions")
    op.drop_index(
        op.f("ix_rule_building_definitions_category"), table_name="rule_building_definitions"
    )
    op.drop_table("rule_building_definitions")
    op.drop_index(op.f("ix_rule_settlement_tiers_ruleset_id"), table_name="rule_settlement_tiers")
    op.drop_index(op.f("ix_rule_settlement_tiers_key"), table_name="rule_settlement_tiers")
    op.drop_table("rule_settlement_tiers")
    op.drop_index(op.f("ix_rule_units_ruleset_id"), table_name="rule_units")
    op.drop_index(op.f("ix_rule_units_key"), table_name="rule_units")
    op.drop_table("rule_units")
    op.drop_index(op.f("ix_rule_resources_ruleset_id"), table_name="rule_resources")
    op.drop_index(op.f("ix_rule_resources_key"), table_name="rule_resources")
    op.drop_table("rule_resources")
    op.drop_index(op.f("ix_rule_currencies_ruleset_id"), table_name="rule_currencies")
    op.drop_index(op.f("ix_rule_currencies_key"), table_name="rule_currencies")
    op.drop_table("rule_currencies")
    op.drop_table("rulesets")
