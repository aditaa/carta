from typing import Any, Literal

from pydantic import BaseModel, Field

ItemType = Literal["resource", "currency", "unit", "special"]


class RulesRef(BaseModel):
    item_type: ItemType
    item_key: str
    amount: float


class Currency(BaseModel):
    key: str
    name: str
    copper_value: int | None = None


class Resource(BaseModel):
    key: str
    name: str
    category: str = "basic"


class Unit(BaseModel):
    key: str
    name: str
    category: str
    attack: int | None = None
    defense: int | None = None


class SettlementTier(BaseModel):
    key: str
    name: str
    min_buildings: int
    max_buildings: int
    upgrade_cost: list[RulesRef] = Field(default_factory=list)
    upkeep: list[RulesRef] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class BuildingDefinition(BaseModel):
    key: str
    name: str
    category: str
    map_visible: bool = False
    settlement_requirement: str | None = None
    requirements: list[str] = Field(default_factory=list)
    effects: list[str] = Field(default_factory=list)
    build_cost: list[RulesRef] = Field(default_factory=list)
    upkeep: list[RulesRef] = Field(default_factory=list)


class ProductionRecipe(BaseModel):
    key: str
    building_key: str
    recipe_type: str
    inputs: list[RulesRef] = Field(default_factory=list)
    outputs: list[RulesRef] = Field(default_factory=list)


class OwnershipRule(BaseModel):
    entity_type: str
    allowed: list[str] = Field(default_factory=list)
    not_allowed: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Phase(BaseModel):
    key: str
    name: str
    requirements: list[dict[str, Any]] = Field(default_factory=list)


class RulesDataset(BaseModel):
    schema_version: str
    game: str
    rules_version: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    currencies: list[Currency] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)
    units: list[Unit] = Field(default_factory=list)
    settlement_tiers: list[SettlementTier] = Field(default_factory=list)
    building_definitions: list[BuildingDefinition] = Field(default_factory=list)
    production_recipes: list[ProductionRecipe] = Field(default_factory=list)
    ownership_rules: list[OwnershipRule] = Field(default_factory=list)
    transports: list[dict[str, Any]] = Field(default_factory=list)
    titles: list[dict[str, Any]] = Field(default_factory=list)
    phases: list[Phase] = Field(default_factory=list)
    solver_defaults: dict[str, Any] = Field(default_factory=dict)
    maintenance_status: dict[str, Any] = Field(default_factory=dict)
