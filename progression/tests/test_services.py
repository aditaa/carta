import pytest

from progression.models import PhaseDefinition, PhaseUnlock, TitleDefinition
from progression.services import (
    ProgressionFact,
    next_phase,
    phase_catalog,
    phase_requirement_statuses,
    title_catalog,
)
from rulesets.models import Ruleset


@pytest.fixture
def ruleset(db):
    return Ruleset.objects.create(
        game="Carta Arcanum",
        rules_version="test",
        schema_version="1",
        source_path="test.rules.json",
    )


@pytest.mark.django_db
def test_title_catalog_returns_titles_in_model_order(ruleset):
    TitleDefinition.objects.create(
        ruleset=ruleset,
        key="baron",
        name="Baron",
        category="noble",
        requirements=[{"kind": "renown", "amount": 5}],
        effects=[{"kind": "visibility", "scope": "house"}],
    )

    titles = title_catalog(ruleset)

    assert len(titles) == 1
    assert titles[0].key == "baron"
    assert titles[0].requirements == [{"kind": "renown", "amount": 5}]
    assert titles[0].effects == [{"kind": "visibility", "scope": "house"}]


@pytest.mark.django_db
def test_phase_catalog_includes_ordered_unlocks(ruleset):
    phase = PhaseDefinition.objects.create(
        ruleset=ruleset,
        key="settlement",
        name="Settlement",
        description="Found and stabilize a settlement.",
        sort_order=20,
        requirements=[{"kind": "building_count", "amount": 3}],
    )
    PhaseUnlock.objects.create(
        phase=phase,
        key="advanced_buildings",
        name="Advanced Buildings",
        unlock_type="building_category",
        data={"building_category": "advanced"},
        sort_order=10,
    )
    PhaseUnlock.objects.create(
        phase=phase,
        key="trade_routes",
        name="Trade Routes",
        unlock_type="system",
        sort_order=20,
    )

    phases = phase_catalog(ruleset)

    assert len(phases) == 1
    assert phases[0].requirements == [{"kind": "building_count", "amount": 3}]
    assert [unlock.key for unlock in phases[0].unlocks] == [
        "advanced_buildings",
        "trade_routes",
    ]
    assert phases[0].unlocks[0].data == {"building_category": "advanced"}


@pytest.mark.django_db
def test_next_phase_returns_first_phase_when_current_phase_is_empty_or_unknown(ruleset):
    PhaseDefinition.objects.create(ruleset=ruleset, key="founding", name="Founding")
    PhaseDefinition.objects.create(
        ruleset=ruleset,
        key="settlement",
        name="Settlement",
        sort_order=10,
    )

    assert next_phase(ruleset).key == "founding"
    assert next_phase(ruleset, "missing").key == "founding"


@pytest.mark.django_db
def test_next_phase_returns_following_phase_or_none_at_end(ruleset):
    PhaseDefinition.objects.create(ruleset=ruleset, key="founding", name="Founding")
    PhaseDefinition.objects.create(
        ruleset=ruleset,
        key="settlement",
        name="Settlement",
        sort_order=10,
    )

    assert next_phase(ruleset, "founding").key == "settlement"
    assert next_phase(ruleset, "settlement") is None


@pytest.mark.django_db
def test_phase_requirement_statuses_reports_met_and_missing_amounts(ruleset):
    phase = PhaseDefinition.objects.create(
        ruleset=ruleset,
        key="settlement",
        name="Settlement",
        requirements=[
            {"kind": "building_count", "key": "any", "amount": 3},
            {"kind": "resource", "key": "wood", "amount": 10},
        ],
    )

    statuses = phase_requirement_statuses(
        phase,
        [
            ProgressionFact(kind="building_count", key="any", amount=4),
            ProgressionFact(kind="resource", key="wood", amount=6),
        ],
    )

    assert [status.status for status in statuses] == ["met", "missing"]
    assert statuses[0].is_met is True
    assert statuses[0].missing == 0
    assert statuses[1].current == 6
    assert statuses[1].target == 10
    assert statuses[1].missing == 4


@pytest.mark.django_db
def test_phase_requirement_statuses_handles_boolean_and_unknown_requirements(ruleset):
    phase = PhaseDefinition.objects.create(
        ruleset=ruleset,
        key="settlement",
        name="Settlement",
        requirements=[
            {"kind": "approval", "key": "game_maker"},
            {"label": "Unstructured requirement"},
        ],
    )

    statuses = phase_requirement_statuses(
        phase,
        [ProgressionFact(kind="approval", key="game_maker", completed=True)],
    )

    assert statuses[0].status == "met"
    assert statuses[0].current is True
    assert statuses[0].target is True
    assert statuses[1].status == "unknown"
