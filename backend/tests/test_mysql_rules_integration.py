import os

import pytest
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.domains.auth.models import House, HouseMembership, User
from app.domains.buildings.models import OwnedBuilding
from app.domains.buildings.schemas import BuildingRegistryCreate
from app.domains.buildings.service import BuildingRegistryPermissionError, BuildingRegistryService
from app.domains.rules.models import (
    RuleBuildingDefinition,
    RuleCurrency,
    RuleProductionRecipe,
    RuleResource,
    Ruleset,
    RuleTransport,
    RuleUnit,
)
from app.domains.rules.service import get_rules_service

pytestmark = pytest.mark.integration


def mysql_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        pytest.skip("DATABASE_URL is required for MySQL integration tests")

    url = make_url(database_url)
    if url.get_backend_name() != "mysql":
        pytest.skip("MySQL integration tests require a mysql DATABASE_URL")
    return database_url


def cleanup_registry_rows(db: Session) -> None:
    db.execute(delete(OwnedBuilding).where(OwnedBuilding.owner_user_id.in_([9001, 9002, 9003])))
    db.execute(delete(HouseMembership).where(HouseMembership.user_id.in_([9001, 9002, 9003])))
    db.execute(delete(User).where(User.id.in_([9001, 9002, 9003])))
    db.execute(delete(House).where(House.id.in_([9010, 9020])))
    db.commit()


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
            select(RuleProductionRecipe).where(
                RuleProductionRecipe.key == "farm_victual_from_livestock"
            )
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
    assert farm_recipe.outputs_json == [{"item_type": "unit", "item_key": "victual", "amount": 1.0}]
    assert carriage is not None
    assert carriage.payload_json["transport_type"] == "caravan"


def test_mysql_building_registry_visibility_and_create_permissions() -> None:
    engine = create_engine(mysql_database_url(), pool_pre_ping=True)
    service = BuildingRegistryService()

    with Session(engine) as db:
        cleanup_registry_rows(db)
        rules = get_rules_service().load_current_rules()
        db.add_all(
            [
                User(id=9001, email="mysql-one@example.test", display_name="MySQL One"),
                User(id=9002, email="mysql-two@example.test", display_name="MySQL Two"),
                User(id=9003, email="mysql-three@example.test", display_name="MySQL Three"),
                House(id=9010, name="MySQL House Ten"),
                House(id=9020, name="MySQL House Twenty"),
                HouseMembership(user_id=9001, house_id=9010, can_view_house=True),
                HouseMembership(user_id=9002, house_id=9010, can_view_house=False),
                OwnedBuilding(
                    owner_user_id=9001,
                    building_definition_id="farm",
                    count=1,
                ),
                OwnedBuilding(
                    owner_user_id=9002,
                    house_id=9010,
                    building_definition_id="market",
                    count=1,
                ),
                OwnedBuilding(
                    owner_user_id=9002,
                    building_definition_id="shop",
                    count=1,
                ),
                OwnedBuilding(
                    owner_user_id=9003,
                    house_id=9020,
                    building_definition_id="tower",
                    count=1,
                ),
            ]
        )
        db.commit()

        scope = service.build_visibility_scope_from_db(db, user_id=9001)
        visible = service.list_visible_from_db(db, scope)

        assert scope.visible_user_ids == [9001, 9002]
        assert scope.visible_house_ids == [9010]
        assert {building.building_definition_id for building in visible} == {"farm", "market"}

        created = service.create_in_db(
            db,
            BuildingRegistryCreate(
                owner_user_id=9002,
                house_id=9010,
                building_definition_id="shop",
                count=1,
            ),
            scope,
            rules=rules,
        )
        assert created.owner_user_id == 9002
        assert created.house_id == 9010

        with pytest.raises(BuildingRegistryPermissionError):
            service.create_in_db(
                db,
                BuildingRegistryCreate(
                    owner_user_id=9002,
                    building_definition_id="shop",
                    count=1,
                ),
                scope,
                rules=rules,
            )

        cleanup_registry_rows(db)
