from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from buildings.models import BuildingDefinition, SettlementTier
from ownership.models import OwnershipRule
from production.models import ProductionRecipe
from progression.models import PhaseDefinition, PhaseUnlock, TitleDefinition
from resources.models import Currency, Resource, ResourceCategory, Unit
from rulesets.models import ItemReference, Ruleset, RulesetImportLog
from transports.models import TransportDefinition


class RulesetValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RulesetImportResult:
    ruleset: Ruleset
    currencies: int
    resources: int
    units: int
    settlement_tiers: int
    buildings: int
    production_recipes: int
    ownership_rules: int
    transports: int
    titles: int
    phases: int
    phase_unlocks: int


def load_rules_data(rules_path: Path) -> dict[str, Any]:
    with rules_path.open(encoding="utf-8") as rules_file:
        data = json.load(rules_file)
    if not isinstance(data, dict):
        raise RulesetValidationError("Rules file must contain a JSON object.")
    return data


def validate_rules_data(
    data: dict[str, Any],
    schema_path: Path | None = None,
) -> None:
    schema_path = schema_path or settings.BASE_DIR / "rules" / "rules.schema.json"
    with schema_path.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if errors:
        raise RulesetValidationError(_format_validation_error(errors[0]))


def import_rules_file(rules_path: Path, schema_path: Path | None = None) -> RulesetImportResult:
    rules_path = rules_path.resolve()
    data = load_rules_data(rules_path)

    try:
        validate_rules_data(data, schema_path=schema_path)
        with transaction.atomic():
            ruleset, _created = Ruleset.objects.update_or_create(
                game=data["game"],
                rules_version=data["rules_version"],
                defaults={
                    "schema_version": data["schema_version"],
                    "source_path": str(rules_path),
                    "metadata": data.get("metadata", {}),
                    "raw_data": data,
                },
            )
            _sync_currencies(ruleset, data.get("currencies", []))
            categories = _sync_resource_categories(ruleset, data.get("resources", []))
            _sync_resources(ruleset, data.get("resources", []), categories)
            ResourceCategory.objects.filter(ruleset=ruleset).exclude(
                key__in=categories.keys()
            ).delete()
            _sync_units(ruleset, data.get("units", []))
            tiers = _sync_settlement_tiers(ruleset, data.get("settlement_tiers", []))
            buildings = _sync_buildings(ruleset, data.get("building_definitions", []), tiers)
            _sync_production_recipes(ruleset, data.get("production_recipes", []), buildings)
            _sync_ownership_rules(ruleset, data.get("ownership_rules", []))
            _sync_transports(ruleset, data.get("transports", []))
            _sync_titles(ruleset, data.get("titles", []))
            _sync_phases(ruleset, data.get("phases", []))
            RulesetImportLog.objects.create(
                ruleset=ruleset,
                source_path=str(rules_path),
                status=RulesetImportLog.Status.SUCCESS,
                message="Rules import completed.",
            )
    except Exception as exc:
        RulesetImportLog.objects.create(
            source_path=str(rules_path),
            status=RulesetImportLog.Status.FAILED,
            message=str(exc),
        )
        raise

    return RulesetImportResult(
        ruleset=ruleset,
        currencies=ruleset.currencies.count(),
        resources=ruleset.resources.count(),
        units=ruleset.units.count(),
        settlement_tiers=ruleset.settlement_tiers.count(),
        buildings=ruleset.buildings.count(),
        production_recipes=ruleset.recipes.count(),
        ownership_rules=ruleset.ownership_rules.count(),
        transports=ruleset.transports.count(),
        titles=ruleset.titles.count(),
        phases=ruleset.phases.count(),
        phase_unlocks=PhaseUnlock.objects.filter(phase__ruleset=ruleset).count(),
    )


def _sync_currencies(ruleset: Ruleset, currencies: list[dict[str, Any]]) -> None:
    keys = []
    for currency in currencies:
        keys.append(currency["key"])
        Currency.objects.update_or_create(
            ruleset=ruleset,
            key=currency["key"],
            defaults={
                "name": currency["name"],
                "copper_value": currency.get("copper_value"),
            },
        )
    Currency.objects.filter(ruleset=ruleset).exclude(key__in=keys).delete()


def _sync_resource_categories(
    ruleset: Ruleset,
    resources: list[dict[str, Any]],
) -> dict[str, ResourceCategory]:
    category_keys = sorted(
        {resource["category"] for resource in resources if resource.get("category")}
    )
    categories = {}
    for category_key in category_keys:
        category, _created = ResourceCategory.objects.update_or_create(
            ruleset=ruleset,
            key=category_key,
            defaults={"name": _humanize_key(category_key)},
        )
        categories[category_key] = category
    return categories


def _sync_resources(
    ruleset: Ruleset,
    resources: list[dict[str, Any]],
    categories: dict[str, ResourceCategory],
) -> None:
    keys = []
    for resource in resources:
        keys.append(resource["key"])
        Resource.objects.update_or_create(
            ruleset=ruleset,
            key=resource["key"],
            defaults={
                "name": resource["name"],
                "category": categories.get(resource.get("category")),
            },
        )
    Resource.objects.filter(ruleset=ruleset).exclude(key__in=keys).delete()


def _sync_units(ruleset: Ruleset, units: list[dict[str, Any]]) -> None:
    keys = []
    for unit in units:
        keys.append(unit["key"])
        Unit.objects.update_or_create(
            ruleset=ruleset,
            key=unit["key"],
            defaults={
                "name": unit["name"],
                "category": unit["category"],
                "attack": unit.get("attack"),
                "defense": unit.get("defense"),
            },
        )
    Unit.objects.filter(ruleset=ruleset).exclude(key__in=keys).delete()


def _sync_settlement_tiers(
    ruleset: Ruleset,
    settlement_tiers: list[dict[str, Any]],
) -> dict[str, SettlementTier]:
    keys = []
    tiers = {}
    for tier_data in settlement_tiers:
        keys.append(tier_data["key"])
        tier, _created = SettlementTier.objects.update_or_create(
            ruleset=ruleset,
            key=tier_data["key"],
            defaults={
                "name": tier_data["name"],
                "min_buildings": tier_data["min_buildings"],
                "max_buildings": tier_data["max_buildings"],
                "prerequisites": tier_data.get("prerequisites", []),
            },
        )
        tiers[tier.key] = tier
        _sync_item_refs(
            ruleset=ruleset,
            owner_type="settlement_tier",
            owner_key=tier.key,
            purpose=ItemReference.Purpose.SETTLEMENT_UPGRADE_COST,
            refs=tier_data.get("upgrade_cost", []),
        )
        _sync_item_refs(
            ruleset=ruleset,
            owner_type="settlement_tier",
            owner_key=tier.key,
            purpose=ItemReference.Purpose.SETTLEMENT_UPKEEP,
            refs=tier_data.get("upkeep", []),
        )
    _delete_owner_item_refs_for_stale_keys(
        ruleset=ruleset,
        owner_type="settlement_tier",
        kept_keys=keys,
    )
    SettlementTier.objects.filter(ruleset=ruleset).exclude(key__in=keys).delete()
    return tiers


def _sync_buildings(
    ruleset: Ruleset,
    buildings: list[dict[str, Any]],
    tiers: dict[str, SettlementTier],
) -> dict[str, BuildingDefinition]:
    keys = []
    building_records = {}
    for building_data in buildings:
        keys.append(building_data["key"])
        settlement_requirement_key = building_data.get("settlement_requirement")
        settlement_requirement = None
        if settlement_requirement_key:
            settlement_requirement = tiers.get(settlement_requirement_key)
            if settlement_requirement is None:
                raise RulesetValidationError(
                    f"Building {building_data['key']} references missing settlement tier "
                    f"{settlement_requirement_key}."
                )
        building, _created = BuildingDefinition.objects.update_or_create(
            ruleset=ruleset,
            key=building_data["key"],
            defaults={
                "name": building_data["name"],
                "category": building_data["category"],
                "map_visible": building_data.get("map_visible", False),
                "settlement_requirement": settlement_requirement,
                "requirements": building_data.get("requirements", []),
                "effects": building_data.get("effects", []),
            },
        )
        building_records[building.key] = building
        _sync_item_refs(
            ruleset=ruleset,
            owner_type="building_definition",
            owner_key=building.key,
            purpose=ItemReference.Purpose.BUILD_COST,
            refs=building_data.get("build_cost", []),
        )
        _sync_item_refs(
            ruleset=ruleset,
            owner_type="building_definition",
            owner_key=building.key,
            purpose=ItemReference.Purpose.BUILDING_UPKEEP,
            refs=building_data.get("upkeep", []),
        )
    _delete_owner_item_refs_for_stale_keys(
        ruleset=ruleset,
        owner_type="building_definition",
        kept_keys=keys,
    )
    BuildingDefinition.objects.filter(ruleset=ruleset).exclude(key__in=keys).delete()
    return building_records


def _sync_production_recipes(
    ruleset: Ruleset,
    recipes: list[dict[str, Any]],
    buildings: dict[str, BuildingDefinition],
) -> None:
    keys = []
    for recipe_data in recipes:
        keys.append(recipe_data["key"])
        building = buildings.get(recipe_data["building_key"])
        if building is None:
            raise RulesetValidationError(
                f"Recipe {recipe_data['key']} references missing building "
                f"{recipe_data['building_key']}."
            )
        recipe, _created = ProductionRecipe.objects.update_or_create(
            ruleset=ruleset,
            key=recipe_data["key"],
            defaults={
                "building": building,
                "recipe_type": recipe_data["recipe_type"],
            },
        )
        _sync_item_refs(
            ruleset=ruleset,
            owner_type="production_recipe",
            owner_key=recipe.key,
            purpose=ItemReference.Purpose.RECIPE_INPUT,
            refs=recipe_data.get("inputs", []),
        )
        _sync_item_refs(
            ruleset=ruleset,
            owner_type="production_recipe",
            owner_key=recipe.key,
            purpose=ItemReference.Purpose.RECIPE_OUTPUT,
            refs=recipe_data.get("outputs", []),
        )
    _delete_owner_item_refs_for_stale_keys(
        ruleset=ruleset,
        owner_type="production_recipe",
        kept_keys=keys,
    )
    ProductionRecipe.objects.filter(ruleset=ruleset).exclude(key__in=keys).delete()


def _sync_ownership_rules(
    ruleset: Ruleset,
    ownership_rules: list[dict[str, Any]],
) -> None:
    entity_types = []
    for rule_data in ownership_rules:
        entity_types.append(rule_data["entity_type"])
        OwnershipRule.objects.update_or_create(
            ruleset=ruleset,
            entity_type=rule_data["entity_type"],
            defaults={
                "allowed": rule_data.get("allowed", []),
                "not_allowed": rule_data.get("not_allowed", []),
                "notes": rule_data.get("notes", []),
            },
        )
    OwnershipRule.objects.filter(ruleset=ruleset).exclude(entity_type__in=entity_types).delete()


def _sync_transports(
    ruleset: Ruleset,
    transports: list[dict[str, Any]],
) -> None:
    keys = []
    for transport_data in transports:
        keys.append(transport_data["key"])
        transport, _created = TransportDefinition.objects.update_or_create(
            ruleset=ruleset,
            key=transport_data["key"],
            defaults={
                "name": transport_data["name"],
                "transport_type": transport_data["transport_type"],
                "home_requirement": transport_data.get("home_requirement", ""),
                "health": transport_data["health"],
                "storage": transport_data["storage"],
                "quarters": transport_data["quarters"],
                "actions": transport_data.get("actions", []),
            },
        )
        _sync_item_refs(
            ruleset=ruleset,
            owner_type="transport_definition",
            owner_key=transport.key,
            purpose=ItemReference.Purpose.TRANSPORT_BUILD_COST,
            refs=transport_data.get("build_cost", []),
        )
        _sync_item_refs(
            ruleset=ruleset,
            owner_type="transport_definition",
            owner_key=transport.key,
            purpose=ItemReference.Purpose.TRANSPORT_REPAIR_COST,
            refs=transport_data.get("repair_cost", []),
        )
        _sync_item_refs(
            ruleset=ruleset,
            owner_type="transport_definition",
            owner_key=transport.key,
            purpose=ItemReference.Purpose.TRANSPORT_UPKEEP,
            refs=transport_data.get("upkeep", []),
        )
    _delete_owner_item_refs_for_stale_keys(
        ruleset=ruleset,
        owner_type="transport_definition",
        kept_keys=keys,
    )
    TransportDefinition.objects.filter(ruleset=ruleset).exclude(key__in=keys).delete()


def _sync_titles(ruleset: Ruleset, titles: list[dict[str, Any]]) -> None:
    keys = []
    for title_data in titles:
        keys.append(title_data["key"])
        TitleDefinition.objects.update_or_create(
            ruleset=ruleset,
            key=title_data["key"],
            defaults={
                "name": title_data["name"],
                "category": title_data.get("category", ""),
                "requirements": title_data.get("requirements", []),
                "effects": title_data.get("effects", []),
                "raw_data": title_data,
            },
        )
    TitleDefinition.objects.filter(ruleset=ruleset).exclude(key__in=keys).delete()


def _sync_phases(ruleset: Ruleset, phases: list[dict[str, Any]]) -> None:
    keys = []
    for index, phase_data in enumerate(phases):
        keys.append(phase_data["key"])
        phase, _created = PhaseDefinition.objects.update_or_create(
            ruleset=ruleset,
            key=phase_data["key"],
            defaults={
                "name": phase_data["name"],
                "description": phase_data.get("description", ""),
                "sort_order": phase_data.get("sort_order", index),
                "requirements": phase_data.get("requirements", []),
                "raw_data": phase_data,
            },
        )
        _sync_phase_unlocks(phase, phase_data.get("unlocks", []))
    PhaseDefinition.objects.filter(ruleset=ruleset).exclude(key__in=keys).delete()


def _sync_phase_unlocks(phase: PhaseDefinition, unlocks: list[dict[str, Any]]) -> None:
    keys = []
    for index, unlock_data in enumerate(unlocks):
        keys.append(unlock_data["key"])
        PhaseUnlock.objects.update_or_create(
            phase=phase,
            key=unlock_data["key"],
            defaults={
                "name": unlock_data["name"],
                "unlock_type": unlock_data.get("unlock_type", ""),
                "description": unlock_data.get("description", ""),
                "data": unlock_data,
                "sort_order": unlock_data.get("sort_order", index),
            },
        )
    phase.unlocks.exclude(key__in=keys).delete()


def _sync_item_refs(
    ruleset: Ruleset,
    owner_type: str,
    owner_key: str,
    purpose: ItemReference.Purpose,
    refs: list[dict[str, Any]],
) -> None:
    ItemReference.objects.filter(
        ruleset=ruleset,
        owner_type=owner_type,
        owner_key=owner_key,
        purpose=purpose,
    ).delete()
    ItemReference.objects.bulk_create(
        [
            ItemReference(
                ruleset=ruleset,
                owner_type=owner_type,
                owner_key=owner_key,
                purpose=purpose,
                item_type=ref["item_type"],
                item_key=ref["item_key"],
                amount=ref["amount"],
                sort_order=index,
            )
            for index, ref in enumerate(refs)
        ]
    )


def _delete_owner_item_refs_for_stale_keys(
    ruleset: Ruleset,
    owner_type: str,
    kept_keys: list[str],
) -> None:
    ItemReference.objects.filter(ruleset=ruleset, owner_type=owner_type).exclude(
        owner_key__in=kept_keys
    ).delete()


def _format_validation_error(error: ValidationError) -> str:
    path = ".".join(str(part) for part in error.path)
    if path:
        return f"{path}: {error.message}"
    return error.message


def _humanize_key(key: str) -> str:
    return key.replace("_", " ").title()
