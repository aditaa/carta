import json
from pathlib import Path

import pytest
from django.core.management import call_command

from buildings.models import BuildingDefinition, SettlementTier
from ownership.models import OwnershipRule
from production.models import ProductionRecipe
from progression.models import PhaseDefinition, PhaseUnlock, TitleDefinition
from resources.models import Currency, Resource, ResourceCategory, Unit
from rulesets.models import ItemReference, Ruleset, RulesetImportLog
from rulesets.services import (
    RulesetValidationError,
    import_rules_file,
    load_rules_data,
    validate_rules_data,
)
from transports.models import TransportDefinition

RULES_FILE = Path("rules/carta-arcanum-2.1.4.rules.json")


def test_valid_rules_file_validates():
    data = load_rules_data(RULES_FILE)

    validate_rules_data(data)


def test_invalid_rules_file_reports_missing_required_section():
    data = load_rules_data(RULES_FILE)
    data.pop("currencies")

    with pytest.raises(RulesetValidationError, match="'currencies' is a required property"):
        validate_rules_data(data)


@pytest.mark.django_db
def test_import_rules_file_creates_ruleset_and_resource_records():
    result = import_rules_file(RULES_FILE)

    assert result.ruleset.game == "Carta Arcanum"
    assert result.ruleset.rules_version == "2.1.4"
    assert result.currencies == 6
    assert result.resources == 11
    assert result.units == 45
    assert result.settlement_tiers == 5
    assert result.buildings == 46
    assert result.production_recipes == 47
    assert result.ownership_rules == 3
    assert result.transports == 4
    assert result.titles == 0
    assert result.phases == 0
    assert result.phase_unlocks == 0
    assert Currency.objects.get(ruleset=result.ruleset, key="crown").copper_value == 324
    assert Resource.objects.get(ruleset=result.ruleset, key="wood").category.key == "basic"
    assert Unit.objects.get(ruleset=result.ruleset, key="knight").attack == 5
    homestead = SettlementTier.objects.get(ruleset=result.ruleset, key="homestead")
    orchard = BuildingDefinition.objects.get(ruleset=result.ruleset, key="orchard")
    recipe = ProductionRecipe.objects.get(ruleset=result.ruleset, key="orchard_train_lumberjack")
    house_rule = OwnershipRule.objects.get(ruleset=result.ruleset, entity_type="house")
    carriage = TransportDefinition.objects.get(ruleset=result.ruleset, key="carriage")
    assert homestead.min_buildings == 1
    assert orchard.settlement_requirement == homestead
    assert recipe.building == orchard
    assert "advanced_buildings" in house_rule.allowed
    assert carriage.storage == 6
    assert "merchant_trading" in carriage.actions
    assert (
        ItemReference.objects.filter(
            ruleset=result.ruleset,
            owner_type="building_definition",
            owner_key="orchard",
            purpose=ItemReference.Purpose.BUILD_COST,
        ).count()
        == 4
    )
    assert (
        ItemReference.objects.get(
            ruleset=result.ruleset,
            owner_type="production_recipe",
            owner_key="orchard_train_lumberjack",
            purpose=ItemReference.Purpose.RECIPE_OUTPUT,
        ).item_key
        == "lumberjack"
    )
    assert (
        ItemReference.objects.filter(
            ruleset=result.ruleset,
            owner_type="transport_definition",
            owner_key="carriage",
            purpose=ItemReference.Purpose.TRANSPORT_BUILD_COST,
        ).count()
        == 6
    )
    assert (
        ItemReference.objects.filter(
            ruleset=result.ruleset,
            owner_type="transport_definition",
            owner_key="carriage",
            purpose=ItemReference.Purpose.TRANSPORT_REPAIR_COST,
        ).count()
        == 2
    )
    assert RulesetImportLog.objects.filter(
        ruleset=result.ruleset,
        status=RulesetImportLog.Status.SUCCESS,
    ).exists()


@pytest.mark.django_db
def test_import_rules_file_is_idempotent_by_game_and_version():
    first = import_rules_file(RULES_FILE)
    second = import_rules_file(RULES_FILE)

    assert first.ruleset.pk == second.ruleset.pk
    assert Ruleset.objects.count() == 1
    assert Currency.objects.count() == 6
    assert ResourceCategory.objects.count() == 2
    assert Resource.objects.count() == 11
    assert Unit.objects.count() == 45
    assert SettlementTier.objects.count() == 5
    assert BuildingDefinition.objects.count() == 46
    assert ProductionRecipe.objects.count() == 47
    assert OwnershipRule.objects.count() == 3
    assert TransportDefinition.objects.count() == 4
    assert TitleDefinition.objects.count() == 0
    assert PhaseDefinition.objects.count() == 0
    assert PhaseUnlock.objects.count() == 0
    assert RulesetImportLog.objects.filter(status=RulesetImportLog.Status.SUCCESS).count() == 2


@pytest.mark.django_db
def test_import_rules_file_updates_existing_records(tmp_path):
    import_rules_file(RULES_FILE)
    data = load_rules_data(RULES_FILE)
    data["currencies"][0]["name"] = "Updated Gold Bar"
    changed_rules = tmp_path / "changed.rules.json"
    changed_rules.write_text(json.dumps(data), encoding="utf-8")

    import_rules_file(changed_rules)

    assert Ruleset.objects.count() == 1
    assert Currency.objects.get(key="gold_bar").name == "Updated Gold Bar"


@pytest.mark.django_db
def test_import_rules_file_removes_stale_resource_records(tmp_path):
    import_rules_file(RULES_FILE)
    data = load_rules_data(RULES_FILE)
    data["currencies"] = [
        currency for currency in data["currencies"] if currency["key"] != "copper"
    ]
    data["resources"] = [resource for resource in data["resources"] if resource["key"] != "gold"]
    data["units"] = [unit for unit in data["units"] if unit["key"] != "knight"]
    changed_rules = tmp_path / "changed.rules.json"
    changed_rules.write_text(json.dumps(data), encoding="utf-8")

    result = import_rules_file(changed_rules)

    assert result.currencies == 5
    assert result.resources == 10
    assert result.units == 44
    assert not Currency.objects.filter(key="copper").exists()
    assert not Resource.objects.filter(key="gold").exists()
    assert not ResourceCategory.objects.filter(key="wildcard").exists()
    assert not Unit.objects.filter(key="knight").exists()


@pytest.mark.django_db
def test_import_rules_file_removes_stale_building_records(tmp_path):
    import_rules_file(RULES_FILE)
    data = load_rules_data(RULES_FILE)
    data["production_recipes"] = [
        recipe
        for recipe in data["production_recipes"]
        if recipe["key"] != "orchard_train_lumberjack"
    ]
    data["building_definitions"] = [
        building for building in data["building_definitions"] if building["key"] != "orchard"
    ]
    changed_rules = tmp_path / "changed.rules.json"
    changed_rules.write_text(json.dumps(data), encoding="utf-8")

    result = import_rules_file(changed_rules)

    assert result.buildings == 45
    assert result.production_recipes == 46
    assert not BuildingDefinition.objects.filter(key="orchard").exists()
    assert not ProductionRecipe.objects.filter(key="orchard_train_lumberjack").exists()
    assert not ItemReference.objects.filter(owner_key="orchard").exists()


@pytest.mark.django_db
def test_import_rules_file_removes_stale_ownership_and_transport_records(tmp_path):
    import_rules_file(RULES_FILE)
    data = load_rules_data(RULES_FILE)
    data["ownership_rules"] = [
        rule for rule in data["ownership_rules"] if rule["entity_type"] != "house"
    ]
    data["transports"] = [
        transport for transport in data["transports"] if transport["key"] != "carriage"
    ]
    changed_rules = tmp_path / "changed.rules.json"
    changed_rules.write_text(json.dumps(data), encoding="utf-8")

    result = import_rules_file(changed_rules)

    assert result.ownership_rules == 2
    assert result.transports == 3
    assert not OwnershipRule.objects.filter(entity_type="house").exists()
    assert not TransportDefinition.objects.filter(key="carriage").exists()
    assert not ItemReference.objects.filter(owner_key="carriage").exists()


@pytest.mark.django_db
def test_import_rules_file_creates_progression_records(tmp_path):
    data = load_rules_data(RULES_FILE)
    data["titles"] = [
        {
            "key": "baron",
            "name": "Baron",
            "category": "noble",
            "requirements": [{"kind": "renown", "amount": 5}],
            "effects": [{"kind": "visibility", "scope": "house"}],
            "notes": ["Manually reviewed title seed."],
        }
    ]
    data["phases"] = [
        {
            "key": "settlement",
            "name": "Settlement",
            "description": "Found and stabilize a settlement.",
            "sort_order": 10,
            "requirements": [{"kind": "building_count", "amount": 3}],
            "unlocks": [
                {
                    "key": "advanced_buildings",
                    "name": "Advanced Buildings",
                    "unlock_type": "building_category",
                    "description": "Advanced buildings may be constructed.",
                    "building_category": "advanced",
                }
            ],
        }
    ]
    changed_rules = tmp_path / "changed.rules.json"
    changed_rules.write_text(json.dumps(data), encoding="utf-8")

    result = import_rules_file(changed_rules)

    assert result.titles == 1
    assert result.phases == 1
    assert result.phase_unlocks == 1
    title = TitleDefinition.objects.get(ruleset=result.ruleset, key="baron")
    phase = PhaseDefinition.objects.get(ruleset=result.ruleset, key="settlement")
    unlock = PhaseUnlock.objects.get(phase=phase, key="advanced_buildings")
    assert title.category == "noble"
    assert title.requirements == [{"kind": "renown", "amount": 5}]
    assert title.raw_data["notes"] == ["Manually reviewed title seed."]
    assert phase.sort_order == 10
    assert phase.requirements == [{"kind": "building_count", "amount": 3}]
    assert unlock.unlock_type == "building_category"
    assert unlock.data["building_category"] == "advanced"


@pytest.mark.django_db
def test_import_rules_file_removes_stale_progression_records(tmp_path):
    data = load_rules_data(RULES_FILE)
    data["titles"] = [{"key": "baron", "name": "Baron"}]
    data["phases"] = [
        {
            "key": "settlement",
            "name": "Settlement",
            "unlocks": [{"key": "advanced_buildings", "name": "Advanced Buildings"}],
        }
    ]
    changed_rules = tmp_path / "changed.rules.json"
    changed_rules.write_text(json.dumps(data), encoding="utf-8")
    import_rules_file(changed_rules)

    data["titles"] = []
    data["phases"] = [
        {
            "key": "settlement",
            "name": "Settlement",
            "unlocks": [],
        }
    ]
    changed_rules.write_text(json.dumps(data), encoding="utf-8")
    result = import_rules_file(changed_rules)

    assert result.titles == 0
    assert result.phases == 1
    assert result.phase_unlocks == 0
    assert not TitleDefinition.objects.filter(key="baron").exists()
    assert not PhaseUnlock.objects.filter(key="advanced_buildings").exists()


@pytest.mark.django_db
def test_import_rules_file_logs_failed_validation(tmp_path):
    data = load_rules_data(RULES_FILE)
    data.pop("resources")
    invalid_rules = tmp_path / "invalid.rules.json"
    invalid_rules.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RulesetValidationError):
        import_rules_file(invalid_rules)

    log = RulesetImportLog.objects.get(status=RulesetImportLog.Status.FAILED)
    assert log.ruleset is None
    assert "resources" in log.message
    assert Ruleset.objects.count() == 0


@pytest.mark.django_db
def test_import_rules_file_rejects_recipe_with_missing_building(tmp_path):
    data = load_rules_data(RULES_FILE)
    data["production_recipes"][0]["building_key"] = "missing_building"
    invalid_rules = tmp_path / "invalid.rules.json"
    invalid_rules.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RulesetValidationError, match="missing building"):
        import_rules_file(invalid_rules)

    assert Ruleset.objects.count() == 0
    assert RulesetImportLog.objects.filter(status=RulesetImportLog.Status.FAILED).exists()


@pytest.mark.django_db
def test_import_rules_file_rejects_building_with_missing_settlement_tier(tmp_path):
    data = load_rules_data(RULES_FILE)
    data["building_definitions"][0]["settlement_requirement"] = "missing_tier"
    invalid_rules = tmp_path / "invalid.rules.json"
    invalid_rules.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RulesetValidationError, match="missing settlement tier"):
        import_rules_file(invalid_rules)

    assert Ruleset.objects.count() == 0
    assert RulesetImportLog.objects.filter(status=RulesetImportLog.Status.FAILED).exists()


@pytest.mark.django_db
def test_import_rules_file_rejects_transport_with_missing_required_value(tmp_path):
    data = load_rules_data(RULES_FILE)
    data["transports"][0].pop("health")
    invalid_rules = tmp_path / "invalid.rules.json"
    invalid_rules.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RulesetValidationError, match="'health' is a required property"):
        import_rules_file(invalid_rules)

    assert Ruleset.objects.count() == 0
    assert RulesetImportLog.objects.filter(status=RulesetImportLog.Status.FAILED).exists()


@pytest.mark.django_db
def test_import_rules_command_outputs_summary(capsys):
    call_command("import_rules", RULES_FILE)

    output = capsys.readouterr().out
    assert "Imported Carta Arcanum 2.1.4" in output
    assert "46 buildings" in output
    assert "47 production recipes" in output
    assert "3 ownership rules" in output
    assert "4 transports" in output
    assert "0 titles" in output
    assert "0 phases" in output
    assert "0 phase unlocks" in output
    assert Ruleset.objects.count() == 1
