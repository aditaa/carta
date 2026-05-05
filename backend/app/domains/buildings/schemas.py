from pydantic import BaseModel, Field

from app.domains.rules.schemas import RulesRef


class BuildingRegistryItem(BaseModel):
    id: int
    owner_user_id: int
    building_definition_id: str
    count: int
    house_id: int | None = None
    display_name: str | None = None


class BuildingRegistrySummary(BaseModel):
    items: list[BuildingRegistryItem] = Field(default_factory=list)
    note: str | None = None


class BuildingRegistryCreate(BaseModel):
    owner_user_id: int
    building_definition_id: str = Field(min_length=1, max_length=120)
    count: int = Field(default=1, ge=1)
    house_id: int | None = None
    display_name: str | None = Field(default=None, max_length=120)


class BuildingRegistryUpdate(BaseModel):
    owner_user_id: int | None = None
    building_definition_id: str | None = Field(default=None, min_length=1, max_length=120)
    count: int | None = Field(default=None, ge=1)
    house_id: int | None = None
    display_name: str | None = Field(default=None, max_length=120)


class BuildingUpkeepLine(BaseModel):
    building_registry_id: int
    building_definition_id: str
    count: int
    upkeep: list[RulesRef] = Field(default_factory=list)


class BuildingUpkeepSummary(BaseModel):
    lines: list[BuildingUpkeepLine] = Field(default_factory=list)
    totals: list[RulesRef] = Field(default_factory=list)
