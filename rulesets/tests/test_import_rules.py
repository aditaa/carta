import json
from pathlib import Path

import pytest
from django.core.management import call_command

from resources.models import Currency, Resource, ResourceCategory, Unit
from rulesets.models import Ruleset, RulesetImportLog
from rulesets.services import (
    RulesetValidationError,
    import_rules_file,
    load_rules_data,
    validate_rules_data,
)

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
    assert Currency.objects.get(ruleset=result.ruleset, key="crown").copper_value == 324
    assert Resource.objects.get(ruleset=result.ruleset, key="wood").category.key == "basic"
    assert Unit.objects.get(ruleset=result.ruleset, key="knight").attack == 5
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
def test_import_rules_command_outputs_summary(capsys):
    call_command("import_rules", RULES_FILE)

    output = capsys.readouterr().out
    assert "Imported Carta Arcanum 2.1.4" in output
    assert Ruleset.objects.count() == 1
