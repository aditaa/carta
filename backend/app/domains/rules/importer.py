from pathlib import Path
from typing import Any

import jsonschema
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domains.rules.models import (
    RuleBuildingDefinition,
    RuleCurrency,
    RuleOwnershipRule,
    RuleProductionRecipe,
    RuleResource,
    Ruleset,
    RuleSettlementTier,
    RuleTransport,
    RuleUnit,
)
from app.domains.rules.schemas import RulesDataset, RulesRef


class RuleImportError(ValueError):
    pass


def load_rules_dataset(path: Path) -> RulesDataset:
    payload = _load_json(path)
    schema_path = path.parent / "rules.schema.json"
    if schema_path.exists():
        jsonschema.validate(instance=payload, schema=_load_json(schema_path))
    dataset = RulesDataset.model_validate(payload)
    validate_references(dataset)
    return dataset


def import_rules_dataset(db: Session, dataset: RulesDataset) -> Ruleset:
    ruleset = db.scalar(
        select(Ruleset).where(
            Ruleset.game == dataset.game,
            Ruleset.version == dataset.rules_version,
        )
    )
    if ruleset is None:
        ruleset = Ruleset(
            game=dataset.game,
            version=dataset.rules_version,
            schema_version=dataset.schema_version,
            metadata_json=dataset.metadata,
        )
        db.add(ruleset)
        db.flush()
    else:
        ruleset.schema_version = dataset.schema_version
        ruleset.metadata_json = dataset.metadata
        _clear_ruleset_children(db, ruleset.id)

    db.add_all(
        [
            RuleCurrency(
                ruleset_id=ruleset.id,
                key=currency.key,
                name=currency.name,
                copper_value=currency.copper_value,
            )
            for currency in dataset.currencies
        ]
    )
    db.add_all(
        [
            RuleResource(
                ruleset_id=ruleset.id,
                key=resource.key,
                name=resource.name,
                category=resource.category,
            )
            for resource in dataset.resources
        ]
    )
    db.add_all(
        [
            RuleUnit(
                ruleset_id=ruleset.id,
                key=unit.key,
                name=unit.name,
                category=unit.category,
                attack=unit.attack,
                defense=unit.defense,
            )
            for unit in dataset.units
        ]
    )
    db.add_all(
        [
            RuleSettlementTier(
                ruleset_id=ruleset.id,
                key=tier.key,
                name=tier.name,
                min_buildings=tier.min_buildings,
                max_buildings=tier.max_buildings,
                upgrade_cost_json=_dump_refs(tier.upgrade_cost),
                upkeep_json=_dump_refs(tier.upkeep),
                prerequisites_json=tier.prerequisites,
            )
            for tier in dataset.settlement_tiers
        ]
    )
    db.add_all(
        [
            RuleBuildingDefinition(
                ruleset_id=ruleset.id,
                key=building.key,
                name=building.name,
                category=building.category,
                map_visible=building.map_visible,
                settlement_requirement=building.settlement_requirement,
                requirements_json=building.requirements,
                effects_json=building.effects,
                build_cost_json=_dump_refs(building.build_cost),
                upkeep_json=_dump_refs(building.upkeep),
            )
            for building in dataset.building_definitions
        ]
    )
    db.add_all(
        [
            RuleProductionRecipe(
                ruleset_id=ruleset.id,
                key=recipe.key,
                building_key=recipe.building_key,
                recipe_type=recipe.recipe_type,
                inputs_json=_dump_refs(recipe.inputs),
                outputs_json=_dump_refs(recipe.outputs),
            )
            for recipe in dataset.production_recipes
        ]
    )
    db.add_all(
        [
            RuleOwnershipRule(
                ruleset_id=ruleset.id,
                entity_type=rule.entity_type,
                allowed_json=rule.allowed,
                not_allowed_json=rule.not_allowed,
                notes="\n".join(rule.notes) if rule.notes else None,
            )
            for rule in dataset.ownership_rules
        ]
    )
    db.add_all(
        [
            RuleTransport(
                ruleset_id=ruleset.id,
                key=transport["key"],
                name=transport["name"],
                transport_type=transport["transport_type"],
                payload_json=transport,
            )
            for transport in dataset.transports
        ]
    )
    db.commit()
    db.refresh(ruleset)
    return ruleset


def validate_references(dataset: RulesDataset) -> None:
    item_keys = {
        "currency": {item.key for item in dataset.currencies},
        "resource": {item.key for item in dataset.resources},
        "unit": {item.key for item in dataset.units},
        "special": set(),
    }
    building_keys = {building.key for building in dataset.building_definitions}
    tier_keys = {tier.key for tier in dataset.settlement_tiers}

    for tier in dataset.settlement_tiers:
        _validate_refs(f"settlement_tiers.{tier.key}.upgrade_cost", tier.upgrade_cost, item_keys)
        _validate_refs(f"settlement_tiers.{tier.key}.upkeep", tier.upkeep, item_keys)

    for building in dataset.building_definitions:
        if building.settlement_requirement and building.settlement_requirement not in tier_keys:
            raise RuleImportError(
                f"building_definitions.{building.key}.settlement_requirement "
                f"references unknown tier {building.settlement_requirement!r}"
            )
        _validate_refs(
            f"building_definitions.{building.key}.build_cost", building.build_cost, item_keys
        )
        _validate_refs(f"building_definitions.{building.key}.upkeep", building.upkeep, item_keys)

    for recipe in dataset.production_recipes:
        if recipe.building_key not in building_keys:
            raise RuleImportError(
                f"production_recipes.{recipe.key}.building_key references "
                f"unknown building {recipe.building_key!r}"
            )
        _validate_refs(f"production_recipes.{recipe.key}.inputs", recipe.inputs, item_keys)
        _validate_refs(f"production_recipes.{recipe.key}.outputs", recipe.outputs, item_keys)

    for transport in dataset.transports:
        transport_key = transport.get("key", "<missing>")
        for field in ("build_cost", "upkeep", "repair_cost"):
            refs = [RulesRef.model_validate(ref) for ref in transport.get(field, [])]
            _validate_refs(f"transports.{transport_key}.{field}", refs, item_keys)


def _clear_ruleset_children(db: Session, ruleset_id: int) -> None:
    for model in (
        RuleOwnershipRule,
        RuleProductionRecipe,
        RuleBuildingDefinition,
        RuleSettlementTier,
        RuleUnit,
        RuleResource,
        RuleCurrency,
        RuleTransport,
    ):
        db.execute(delete(model).where(model.ruleset_id == ruleset_id))


def _validate_refs(
    location: str,
    refs: list[RulesRef],
    item_keys: dict[str, set[str]],
) -> None:
    for ref in refs:
        if ref.item_key not in item_keys[ref.item_type]:
            raise RuleImportError(f"{location} references unknown {ref.item_type} {ref.item_key!r}")


def _dump_refs(refs: list[RulesRef]) -> list[dict[str, Any]]:
    return [ref.model_dump() for ref in refs]


def _load_json(path: Path) -> dict[str, Any]:
    import json

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
