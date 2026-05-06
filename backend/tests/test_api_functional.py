import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.domains.auth.models import Denizen, House, HouseMembership
from app.domains.auth.service import hash_password
from app.domains.buildings.models import OwnedBuilding
from app.main import app

pytestmark = pytest.mark.functional

client = TestClient(app)


@pytest.fixture
def db_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    db.add_all(
        [
            Denizen(
                id=1,
                email="one@example.test",
                display_name="Denizen One",
                password_hash=hash_password("swordfish"),
            ),
            Denizen(
                id=2,
                email="two@example.test",
                display_name="Denizen Two",
                password_hash=hash_password("swordfish"),
            ),
            House(id=10, name="House Ten"),
            HouseMembership(denizen_id=1, house_id=10, can_view_house=True),
            HouseMembership(denizen_id=2, house_id=10, can_view_house=False),
            OwnedBuilding(
                id=1,
                owner_denizen_id=1,
                house_id=None,
                building_definition_id="farm",
                count=1,
            ),
        ]
    )
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)


def auth_headers(test_client: TestClient, email: str) -> dict[str, str]:
    response = test_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "swordfish"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "Carta Arcanum API",
        "environment": "local",
    }


def test_current_rules_endpoint_returns_dataset_metadata() -> None:
    response = client.get("/api/v1/rules/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["game"] == "Carta Arcanum"
    assert payload["rules_version"] == "2.1.4"
    assert len(payload["building_definitions"]) >= 40


def test_building_upkeep_preview_uses_visible_demo_buildings() -> None:
    response = client.get("/api/v1/buildings/upkeep-preview")

    assert response.status_code == 200
    payload = response.json()
    assert [line["building_definition_id"] for line in payload["lines"]] == [
        "farm",
        "market",
    ]
    assert payload["totals"] == [
        {"item_type": "currency", "item_key": "tower", "amount": 3.0},
        {"item_type": "resource", "item_key": "crops", "amount": 2.0},
        {"item_type": "resource", "item_key": "rarities", "amount": 1.0},
    ]


@pytest.mark.parametrize(
    ("method", "url", "json"),
    [
        ("get", "/api/v1/buildings/db", None),
        (
            "post",
            "/api/v1/buildings/db",
            {"owner_denizen_id": 1, "building_definition_id": "shop", "count": 1},
        ),
        ("get", "/api/v1/buildings/db/1", None),
        ("patch", "/api/v1/buildings/db/1", {"count": 2}),
        ("delete", "/api/v1/buildings/db/1", None),
    ],
)
def test_db_building_endpoints_require_bearer_token(
    db_client,
    method: str,
    url: str,
    json: dict[str, object] | None,
) -> None:
    response = db_client.request(method, url, json=json)

    assert response.status_code == 401


def test_create_db_building_rejects_other_user_personal_asset(db_client) -> None:
    response = db_client.post(
        "/api/v1/buildings/db",
        headers=auth_headers(db_client, "one@example.test"),
        json={
            "owner_denizen_id": 2,
            "building_definition_id": "shop",
            "count": 1,
        },
    )

    assert response.status_code == 403


def test_create_db_building_allows_visible_house_asset(db_client) -> None:
    response = db_client.post(
        "/api/v1/buildings/db",
        headers=auth_headers(db_client, "one@example.test"),
        json={
            "owner_denizen_id": 2,
            "house_id": 10,
            "building_definition_id": "shop",
            "count": 1,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["owner_denizen_id"] == 2
    assert payload["house_id"] == 10


def test_db_building_endpoints_ignore_spoofed_denizen_id_query_param(db_client) -> None:
    response = db_client.post(
        "/api/v1/buildings/db?denizen_id=1",
        headers=auth_headers(db_client, "two@example.test"),
        json={
            "owner_denizen_id": 1,
            "house_id": 10,
            "building_definition_id": "shop",
            "count": 1,
        },
    )

    assert response.status_code == 403


def test_login_returns_token_and_current_user(db_client) -> None:
    response = db_client.post(
        "/api/v1/auth/login",
        json={"email": "two@example.test", "password": "swordfish"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["denizen"]["email"] == "two@example.test"

    me_response = db_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["display_name"] == "Denizen Two"


def test_login_rejects_bad_password(db_client) -> None:
    response = db_client.post(
        "/api/v1/auth/login",
        json={"email": "two@example.test", "password": "wrong"},
    )

    assert response.status_code == 401
