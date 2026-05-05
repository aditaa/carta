from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Ruleset(Base):
    __tablename__ = "rulesets"
    __table_args__ = (UniqueConstraint("game", "version", name="uq_rulesets_game_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    game: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(40))
    schema_version: Mapped[str] = mapped_column(String(40))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    currencies: Mapped[list["RuleCurrency"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )
    resources: Mapped[list["RuleResource"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )
    units: Mapped[list["RuleUnit"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )
    settlement_tiers: Mapped[list["RuleSettlementTier"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )
    building_definitions: Mapped[list["RuleBuildingDefinition"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )
    production_recipes: Mapped[list["RuleProductionRecipe"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )
    ownership_rules: Mapped[list["RuleOwnershipRule"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )
    transports: Mapped[list["RuleTransport"]] = relationship(
        back_populates="ruleset", cascade="all, delete-orphan"
    )


class RuleCurrency(Base):
    __tablename__ = "rule_currencies"
    __table_args__ = (
        UniqueConstraint("ruleset_id", "key", name="uq_rule_currencies_ruleset_id_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), index=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120))
    copper_value: Mapped[int | None] = mapped_column(Integer)

    ruleset: Mapped[Ruleset] = relationship(back_populates="currencies")


class RuleResource(Base):
    __tablename__ = "rule_resources"
    __table_args__ = (
        UniqueConstraint("ruleset_id", "key", name="uq_rule_resources_ruleset_id_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), index=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80), default="basic")

    ruleset: Mapped[Ruleset] = relationship(back_populates="resources")


class RuleUnit(Base):
    __tablename__ = "rule_units"
    __table_args__ = (UniqueConstraint("ruleset_id", "key", name="uq_rule_units_ruleset_id_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), index=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80))
    attack: Mapped[int | None] = mapped_column(Integer)
    defense: Mapped[int | None] = mapped_column(Integer)

    ruleset: Mapped[Ruleset] = relationship(back_populates="units")


class RuleSettlementTier(Base):
    __tablename__ = "rule_settlement_tiers"
    __table_args__ = (
        UniqueConstraint("ruleset_id", "key", name="uq_rule_settlement_tiers_ruleset_id_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), index=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120))
    min_buildings: Mapped[int] = mapped_column(Integer)
    max_buildings: Mapped[int] = mapped_column(Integer)
    upgrade_cost_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    upkeep_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    prerequisites_json: Mapped[list[str]] = mapped_column(JSON, default=list)

    ruleset: Mapped[Ruleset] = relationship(back_populates="settlement_tiers")


class RuleBuildingDefinition(Base):
    __tablename__ = "rule_building_definitions"
    __table_args__ = (
        UniqueConstraint("ruleset_id", "key", name="uq_rule_building_definitions_ruleset_id_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), index=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80), index=True)
    map_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    settlement_requirement: Mapped[str | None] = mapped_column(String(80))
    requirements_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    effects_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    build_cost_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    upkeep_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    ruleset: Mapped[Ruleset] = relationship(back_populates="building_definitions")


class RuleProductionRecipe(Base):
    __tablename__ = "rule_production_recipes"
    __table_args__ = (
        UniqueConstraint("ruleset_id", "key", name="uq_rule_production_recipes_ruleset_id_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), index=True)
    key: Mapped[str] = mapped_column(String(100), index=True)
    building_key: Mapped[str] = mapped_column(String(80), index=True)
    recipe_type: Mapped[str] = mapped_column(String(80))
    inputs_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    outputs_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    ruleset: Mapped[Ruleset] = relationship(back_populates="production_recipes")


class RuleOwnershipRule(Base):
    __tablename__ = "rule_ownership_rules"
    __table_args__ = (
        UniqueConstraint(
            "ruleset_id", "entity_type", name="uq_rule_ownership_rules_ruleset_id_entity_type"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    allowed_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    not_allowed_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)

    ruleset: Mapped[Ruleset] = relationship(back_populates="ownership_rules")


class RuleTransport(Base):
    __tablename__ = "rule_transports"
    __table_args__ = (
        UniqueConstraint("ruleset_id", "key", name="uq_rule_transports_ruleset_id_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ruleset_id: Mapped[int] = mapped_column(ForeignKey("rulesets.id"), index=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120))
    transport_type: Mapped[str] = mapped_column(String(80), index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    ruleset: Mapped[Ruleset] = relationship(back_populates="transports")
