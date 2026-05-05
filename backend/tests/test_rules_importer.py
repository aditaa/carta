from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.domains.rules.importer import (
    RuleImportError,
    import_rules_dataset,
    load_rules_dataset,
    validate_references,
)
from app.domains.rules.models import RuleBuildingDefinition, RuleCurrency, Ruleset, RuleTransport
from app.domains.rules.schemas import ProductionRecipe, RulesRef

RULES_FILE = Path(__file__).resolve().parents[2] / "rules" / "carta-arcanum-2.1.4.rules.json"

pytestmark = pytest.mark.unit


def test_load_rules_dataset_validates_schema_and_references() -> None:
    dataset = load_rules_dataset(RULES_FILE)

    assert dataset.rules_version == "2.1.4"
    assert [currency.key for currency in dataset.currencies] == [
        "gold_bar",
        "crown",
        "bit",
        "piece",
        "tower",
        "copper",
    ]
    assert "farm" in {building.key for building in dataset.building_definitions}
    assert len(dataset.settlement_tiers) == 5
    assert len(dataset.units) == 45
    assert len(dataset.building_definitions) == 46
    assert len(dataset.production_recipes) == 47
    assert {transport["key"] for transport in dataset.transports} == {
        "carriage",
        "cortege",
        "knull",
        "hulk",
    }


def test_core_rules_rows_match_known_pdf_values() -> None:
    dataset = load_rules_dataset(RULES_FILE)
    settlement_tiers = {tier.key: tier for tier in dataset.settlement_tiers}
    buildings = {building.key: building for building in dataset.building_definitions}

    assert settlement_tiers["shire"].upkeep == [
        RulesRef(item_type="unit", item_key="peasant", amount=5),
        RulesRef(item_type="resource", item_key="crops", amount=5),
        RulesRef(item_type="resource", item_key="livestock", amount=2),
        RulesRef(item_type="currency", item_key="bit", amount=1),
    ]
    assert buildings["mage_tower"].upkeep == [
        RulesRef(item_type="resource", item_key="arcana", amount=5),
        RulesRef(item_type="currency", item_key="bit", amount=2),
        RulesRef(item_type="unit", item_key="peasant", amount=1),
    ]
    assert buildings["temple"].build_cost == []
    assert "needs PDF review" in " ".join(buildings["temple"].requirements)


def test_currency_records_only_store_conversion_value() -> None:
    dataset = load_rules_dataset(RULES_FILE)
    first_currency = dataset.currencies[0].model_dump()

    assert first_currency == {
        "key": "gold_bar",
        "name": "Gold Bar",
        "copper_value": 972,
    }


def test_validate_references_rejects_unknown_recipe_building() -> None:
    dataset = load_rules_dataset(RULES_FILE)
    dataset.production_recipes.append(
        ProductionRecipe(
            key="bad_recipe",
            building_key="missing_building",
            recipe_type="unit_training",
            inputs=[],
            outputs=[RulesRef(item_type="unit", item_key="peasant", amount=1)],
        )
    )

    with pytest.raises(RuleImportError, match="unknown building"):
        validate_references(dataset)


def test_import_rules_dataset_creates_linked_sql_records() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    dataset = load_rules_dataset(RULES_FILE)
    with SessionLocal() as db:
        ruleset = import_rules_dataset(db, dataset)

    with Session(engine) as db:
        stored_ruleset = db.scalar(select(Ruleset).where(Ruleset.id == ruleset.id))
        farm = db.scalar(
            select(RuleBuildingDefinition).where(
                RuleBuildingDefinition.ruleset_id == ruleset.id,
                RuleBuildingDefinition.key == "farm",
            )
        )
        currencies = db.scalars(
            select(RuleCurrency).where(RuleCurrency.ruleset_id == ruleset.id)
        ).all()
        transports = db.scalars(
            select(RuleTransport).where(RuleTransport.ruleset_id == ruleset.id)
        ).all()

    assert stored_ruleset is not None
    assert stored_ruleset.version == "2.1.4"
    assert farm is not None
    assert farm.upkeep_json == [
        {"item_type": "resource", "item_key": "crops", "amount": 1.0},
        {"item_type": "currency", "item_key": "tower", "amount": 1.0},
    ]
    assert len(currencies) == 6
    assert {transport.key for transport in transports} == {"carriage", "cortege", "knull", "hulk"}
