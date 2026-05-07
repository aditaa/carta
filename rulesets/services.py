from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from resources.models import Currency, Resource, ResourceCategory, Unit
from rulesets.models import Ruleset, RulesetImportLog


class RulesetValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RulesetImportResult:
    ruleset: Ruleset
    currencies: int
    resources: int
    units: int


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


def _format_validation_error(error: ValidationError) -> str:
    path = ".".join(str(part) for part in error.path)
    if path:
        return f"{path}: {error.message}"
    return error.message


def _humanize_key(key: str) -> str:
    return key.replace("_", " ").title()
