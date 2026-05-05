import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.functional

client = TestClient(app)


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
