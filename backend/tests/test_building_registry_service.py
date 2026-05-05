from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domains.auth.models import House, HouseMembership, User
from app.domains.auth.schemas import VisibilityScope
from app.domains.buildings.models import OwnedBuilding
from app.domains.buildings.schemas import BuildingRegistryCreate, BuildingRegistryUpdate
from app.domains.buildings.service import (
    BuildingRegistryError,
    BuildingRegistryPermissionError,
    BuildingRegistryService,
    OwnedBuildingRecord,
)
from app.domains.rules.importer import load_rules_dataset

RULES_FILE = Path(__file__).resolve().parents[2] / "rules" / "carta-arcanum-2.1.4.rules.json"

pytestmark = pytest.mark.unit


def build_test_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal(), engine


def seed_registry_db(db) -> None:
    db.add_all(
        [
            User(id=1, email="one@example.test", display_name="User One"),
            User(id=2, email="two@example.test", display_name="User Two"),
            User(id=3, email="three@example.test", display_name="User Three"),
            House(id=10, name="House Ten"),
            House(id=20, name="House Twenty"),
            HouseMembership(user_id=1, house_id=10, can_view_house=True),
            HouseMembership(user_id=2, house_id=10, can_view_house=False),
            OwnedBuilding(
                id=1,
                owner_user_id=1,
                building_definition_id="farm",
                count=2,
            ),
            OwnedBuilding(
                id=2,
                owner_user_id=2,
                house_id=10,
                building_definition_id="market",
                count=1,
            ),
            OwnedBuilding(
                id=3,
                owner_user_id=3,
                house_id=20,
                building_definition_id="watchtower",
                count=1,
            ),
            OwnedBuilding(
                id=4,
                owner_user_id=2,
                building_definition_id="shop",
                count=1,
            ),
            OwnedBuilding(
                id=5,
                owner_user_id=2,
                house_id=20,
                building_definition_id="tower",
                count=1,
            ),
        ]
    )
    db.commit()


def test_user_sees_own_buildings() -> None:
    service = BuildingRegistryService()
    scope = VisibilityScope(user_id=1, visible_user_ids=[1], visible_house_ids=[])

    buildings = service.list_visible(
        [
            OwnedBuildingRecord(
                id=1,
                owner_user_id=1,
                building_definition_id="farm",
                count=1,
            ),
            OwnedBuildingRecord(
                id=2,
                owner_user_id=2,
                building_definition_id="market",
                count=1,
            ),
        ],
        scope,
    )

    assert [building.id for building in buildings] == [1]


def test_house_permission_includes_house_buildings() -> None:
    service = BuildingRegistryService()
    scope = VisibilityScope(
        user_id=1,
        visible_user_ids=[1, 2],
        visible_house_ids=[10],
    )

    buildings = service.list_visible(
        [
            OwnedBuildingRecord(
                id=1,
                owner_user_id=1,
                building_definition_id="farm",
                count=1,
            ),
            OwnedBuildingRecord(
                id=2,
                owner_user_id=2,
                house_id=10,
                building_definition_id="market",
                count=1,
            ),
        ],
        scope,
    )

    assert [building.id for building in buildings] == [1, 2]


def test_house_permission_excludes_house_members_personal_buildings() -> None:
    service = BuildingRegistryService()
    scope = VisibilityScope(
        user_id=1,
        visible_user_ids=[1, 2],
        visible_house_ids=[10],
    )

    buildings = service.list_visible(
        [
            OwnedBuildingRecord(
                id=1,
                owner_user_id=1,
                building_definition_id="farm",
                count=1,
            ),
            OwnedBuildingRecord(
                id=2,
                owner_user_id=2,
                building_definition_id="shop",
                count=1,
            ),
            OwnedBuildingRecord(
                id=3,
                owner_user_id=2,
                house_id=20,
                building_definition_id="tower",
                count=1,
            ),
        ],
        scope,
    )

    assert [building.id for building in buildings] == [1]


def test_user_without_house_permission_cannot_see_house_buildings() -> None:
    service = BuildingRegistryService()
    scope = VisibilityScope(user_id=1, visible_user_ids=[1], visible_house_ids=[])

    buildings = service.list_visible(
        [
            OwnedBuildingRecord(
                id=1,
                owner_user_id=1,
                building_definition_id="farm",
                count=1,
            ),
            OwnedBuildingRecord(
                id=2,
                owner_user_id=2,
                house_id=10,
                building_definition_id="market",
                count=1,
            ),
        ],
        scope,
    )

    assert [building.id for building in buildings] == [1]


def test_aggregate_counts_by_owner() -> None:
    service = BuildingRegistryService()

    totals = service.aggregate_counts_by_owner(
        [
            service_item
            for service_item in service.list_visible(
                [
                    OwnedBuildingRecord(
                        id=1,
                        owner_user_id=1,
                        building_definition_id="farm",
                        count=2,
                    ),
                    OwnedBuildingRecord(
                        id=2,
                        owner_user_id=1,
                        building_definition_id="farm",
                        count=1,
                    ),
                    OwnedBuildingRecord(
                        id=3,
                        owner_user_id=2,
                        house_id=10,
                        building_definition_id="market",
                        count=1,
                    ),
                ],
                VisibilityScope(
                    user_id=1,
                    visible_user_ids=[1, 2],
                    visible_house_ids=[10],
                ),
            )
        ]
    )

    assert totals == {1: {"farm": 3}, 2: {"market": 1}}


def test_validate_building_definitions_rejects_unknown_keys() -> None:
    service = BuildingRegistryService()
    rules = load_rules_dataset(RULES_FILE)

    try:
        service.validate_building_definitions(
            [
                OwnedBuildingRecord(
                    id=1,
                    owner_user_id=1,
                    building_definition_id="missing_building",
                    count=1,
                )
            ],
            rules,
        )
    except BuildingRegistryError as error:
        assert "missing_building" in str(error)
    else:
        raise AssertionError("Expected unknown building key to raise")


def test_calculate_upkeep_totals_from_rules() -> None:
    service = BuildingRegistryService()
    rules = load_rules_dataset(RULES_FILE)
    visible_buildings = service.list_visible(
        [
            OwnedBuildingRecord(
                id=1,
                owner_user_id=1,
                building_definition_id="farm",
                count=2,
            ),
            OwnedBuildingRecord(
                id=2,
                owner_user_id=1,
                building_definition_id="market",
                count=1,
            ),
            OwnedBuildingRecord(
                id=3,
                owner_user_id=2,
                building_definition_id="watchtower",
                count=1,
            ),
        ],
        VisibilityScope(
            user_id=1,
            visible_user_ids=[1],
            visible_house_ids=[],
        ),
    )

    upkeep = service.calculate_upkeep(visible_buildings, rules)

    assert [line.building_definition_id for line in upkeep.lines] == ["farm", "market"]
    assert [line.count for line in upkeep.lines] == [2, 1]
    assert [item.model_dump() for item in upkeep.totals] == [
        {"item_type": "currency", "item_key": "tower", "amount": 3.0},
        {"item_type": "resource", "item_key": "crops", "amount": 2.0},
        {"item_type": "resource", "item_key": "rarities", "amount": 1.0},
    ]


def test_db_scope_includes_user_and_house_members() -> None:
    db, engine = build_test_session()
    try:
        seed_registry_db(db)
        service = BuildingRegistryService()

        scope = service.build_visibility_scope_from_db(db, user_id=1)
        buildings = service.list_visible_from_db(db, scope)

        assert scope.visible_user_ids == [1, 2]
        assert scope.visible_house_ids == [10]
        assert [building.id for building in buildings] == [1, 2]
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_db_user_without_house_permission_only_sees_own_buildings() -> None:
    db, engine = build_test_session()
    try:
        seed_registry_db(db)
        service = BuildingRegistryService()

        scope = service.build_visibility_scope_from_db(db, user_id=2)
        buildings = service.list_visible_from_db(db, scope)

        assert scope.visible_user_ids == [2]
        assert scope.visible_house_ids == []
        assert [building.id for building in buildings] == [2, 4, 5]
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_db_create_rejects_unknown_rule_key() -> None:
    db, engine = build_test_session()
    try:
        rules = load_rules_dataset(RULES_FILE)
        service = BuildingRegistryService()

        try:
            service.create_in_db(
                db,
                BuildingRegistryCreate(
                    owner_user_id=1,
                    building_definition_id="missing_building",
                    count=1,
                ),
                VisibilityScope(user_id=1, visible_user_ids=[1], visible_house_ids=[]),
                rules,
            )
        except BuildingRegistryError as error:
            assert "missing_building" in str(error)
        else:
            raise AssertionError("Expected unknown building key to raise")

        assert db.scalars(select(OwnedBuilding)).all() == []
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_db_create_update_and_delete_visible_building() -> None:
    db, engine = build_test_session()
    try:
        seed_registry_db(db)
        rules = load_rules_dataset(RULES_FILE)
        service = BuildingRegistryService()
        scope = service.build_visibility_scope_from_db(db, user_id=1)

        created = service.create_in_db(
            db,
            BuildingRegistryCreate(
                owner_user_id=1,
                building_definition_id="shop",
                display_name="Main Shop",
                count=1,
            ),
            scope,
            rules,
        )
        assert created.id == 6

        updated = service.update_visible_in_db(
            db,
            created.id,
            BuildingRegistryUpdate(count=3, display_name="Main Shoppe"),
            scope,
            rules,
        )
        assert updated is not None
        assert updated.count == 3
        assert updated.display_name == "Main Shoppe"

        assert service.delete_visible_from_db(db, created.id, scope) is True
        assert service.get_visible_from_db(db, created.id, scope) is None
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_db_create_allows_visible_house_member_asset() -> None:
    db, engine = build_test_session()
    try:
        seed_registry_db(db)
        rules = load_rules_dataset(RULES_FILE)
        service = BuildingRegistryService()
        scope = service.build_visibility_scope_from_db(db, user_id=1)

        created = service.create_in_db(
            db,
            BuildingRegistryCreate(
                owner_user_id=2,
                house_id=10,
                building_definition_id="shop",
                display_name="House Member Shop",
                count=1,
            ),
            scope,
            rules,
        )

        assert created.owner_user_id == 2
        assert created.house_id == 10
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_db_create_rejects_other_users_personal_building() -> None:
    db, engine = build_test_session()
    try:
        seed_registry_db(db)
        rules = load_rules_dataset(RULES_FILE)
        service = BuildingRegistryService()
        scope = service.build_visibility_scope_from_db(db, user_id=1)

        with pytest.raises(BuildingRegistryPermissionError):
            service.create_in_db(
                db,
                BuildingRegistryCreate(
                    owner_user_id=2,
                    building_definition_id="shop",
                    display_name="Private Shop",
                    count=1,
                ),
                scope,
                rules,
            )
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_db_update_refuses_invisible_building() -> None:
    db, engine = build_test_session()
    try:
        seed_registry_db(db)
        rules = load_rules_dataset(RULES_FILE)
        service = BuildingRegistryService()
        scope = service.build_visibility_scope_from_db(db, user_id=1)

        updated = service.update_visible_in_db(
            db,
            3,
            BuildingRegistryUpdate(count=9),
            scope,
            rules,
        )

        hidden = db.get(OwnedBuilding, 3)
        assert updated is None
        assert hidden is not None
        assert hidden.count == 1
    finally:
        db.close()
        Base.metadata.drop_all(engine)
