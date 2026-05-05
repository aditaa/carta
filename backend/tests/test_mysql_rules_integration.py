import os

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.domains.rules.models import (
    RuleBuildingDefinition,
    RuleCurrency,
    RuleProductionRecipe,
    RuleResource,
    Ruleset,
    RuleTransport,
    RuleUnit,
)

pytestmark = pytest.mark.integration


def mysql_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        pytest.skip("DATABASE_URL is required for MySQL integration tests")

    url = make_url(database_url)
    if url.get_backend_name() != "mysql":
        pytest.skip("MySQL integration tests require a mysql DATABASE_URL")
    return database_url


def test_mysql_rules_import_counts_match_dataset() -> None:
    engine = create_engine(mysql_database_url(), pool_pre_ping=True)

    with Session(engine) as db:
        ruleset = db.scalar(
            select(Ruleset).where(
                Ruleset.game == "Carta Arcanum",
                Ruleset.version == "2.1.4",
            )
        )
        assert ruleset is not None

        assert db.scalar(select(func.count()).select_from(RuleCurrency)) == 6
        assert db.scalar(select(func.count()).select_from(RuleResource)) == 11
        assert db.scalar(select(func.count()).select_from(RuleUnit)) == 45
        assert db.scalar(select(func.count()).select_from(RuleBuildingDefinition)) == 46
        assert db.scalar(select(func.count()).select_from(RuleProductionRecipe)) == 47
        assert db.scalar(select(func.count()).select_from(RuleTransport)) == 4


def test_mysql_can_read_core_imported_rule_data() -> None:
    engine = create_engine(mysql_database_url(), pool_pre_ping=True)

    with Session(engine) as db:
        farm = db.scalar(select(RuleBuildingDefinition).where(RuleBuildingDefinition.key == "farm"))
        temple = db.scalar(
            select(RuleBuildingDefinition).where(RuleBuildingDefinition.key == "temple")
        )
        farm_recipe = db.scalar(
            select(RuleProductionRecipe).where(RuleProductionRecipe.key == "farm_produce_crops")
        )
        carriage = db.scalar(select(RuleTransport).where(RuleTransport.key == "carriage"))

    assert farm is not None
    assert farm.upkeep_json == [
        {"item_type": "resource", "item_key": "crops", "amount": 1.0},
        {"item_type": "currency", "item_key": "tower", "amount": 1.0},
    ]
    assert temple is not None
    assert temple.build_cost_json == []
    assert farm_recipe is not None
    assert farm_recipe.outputs_json == [
        {"item_type": "resource", "item_key": "crops", "amount": 3.0}
    ]
    assert carriage is not None
    assert carriage.payload_json["transport_type"] == "caravan"
