from decimal import Decimal

import pytest
from django.urls import reverse

from buildings.models import BuildingDefinition, OwnedBuilding
from ownership.models import House, HouseMembership
from production.models import ProductionRecipe
from resources.models import Resource
from rulesets.models import ItemReference, Ruleset


@pytest.fixture(autouse=True)
def installed_app(settings, tmp_path):
    settings.INSTALLER_LOCK_FILE = tmp_path / "installer.lock"
    settings.INSTALLER_LOCK_FILE.write_text("installed\n", encoding="utf-8")


def create_ruleset():
    ruleset = Ruleset.objects.create(
        game="Carta Arcanum",
        rules_version="test",
        schema_version="1",
        source_path="test.rules.json",
        raw_data={},
    )
    Resource.objects.create(ruleset=ruleset, key="wood", name="Wood")
    Resource.objects.create(ruleset=ruleset, key="food", name="Food")
    return ruleset


def create_user(email="dashboard@example.test"):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name="Dashboard User",
    )


def test_home_page_returns_success(client):
    response = client.get(reverse("dashboard:home"))

    assert response.status_code == 200
    assert b"Carta Arcanum" in response.content
    assert b"Sign in" in response.content


@pytest.mark.django_db
def test_home_page_shows_owner_balance_overview(client):
    ruleset = create_ruleset()
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=user, house=house)
    orchard = BuildingDefinition.objects.create(
        ruleset=ruleset,
        key="orchard",
        name="Orchard",
        category="basic",
    )
    house_keep = BuildingDefinition.objects.create(
        ruleset=ruleset,
        key="keep",
        name="Keep",
        category="defensive",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=house_keep,
        owner_scope=OwnedBuilding.OwnerScope.HOUSE,
        house=house,
        status=OwnedBuilding.Status.ACTIVE,
    )
    client.force_login(user)

    response = client.get(reverse("dashboard:home"))

    assert response.status_code == 200
    assert b"Owner Balance Overview" in response.content
    assert b"Denizen: Dashboard User" in response.content
    assert b"House: House Bramble" in response.content


@pytest.mark.django_db
def test_home_page_links_to_owner_detail(client):
    ruleset = create_ruleset()
    user = create_user()
    orchard = BuildingDefinition.objects.create(
        ruleset=ruleset,
        key="orchard",
        name="Orchard",
        category="basic",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    client.force_login(user)

    response = client.get(reverse("dashboard:home"))

    assert response.status_code == 200
    assert b"/owners/user/" in response.content


@pytest.mark.django_db
def test_owner_detail_page_shows_owner_balance(client):
    ruleset = create_ruleset()
    user = create_user()
    orchard = BuildingDefinition.objects.create(
        ruleset=ruleset,
        key="orchard",
        name="Orchard",
        category="basic",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    client.force_login(user)

    response = client.get(reverse("dashboard:owner_detail", args=["user", user.id]))

    assert response.status_code == 200
    assert b"Orchard" in response.content
    assert b"Owner Production Balance" in response.content
    assert b"Visible Buildings" in response.content


@pytest.mark.django_db
def test_owner_detail_404_for_nonexistent_owner(client):
    user = create_user()
    client.force_login(user)

    response = client.get(reverse("dashboard:owner_detail", args=["user", 999]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_home_page_shows_balance_panel_for_visible_buildings(client):
    ruleset = create_ruleset()
    user = create_user()
    hidden_user = create_user("hidden@example.test")
    orchard = BuildingDefinition.objects.create(
        ruleset=ruleset,
        key="orchard",
        name="Orchard",
        category="basic",
    )
    hidden_mine = BuildingDefinition.objects.create(
        ruleset=ruleset,
        key="mine",
        name="Mine",
        category="basic",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=hidden_mine,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=hidden_user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    recipe = ProductionRecipe.objects.create(
        ruleset=ruleset,
        key="orchard_food",
        building=orchard,
        recipe_type="production",
    )
    ItemReference.objects.create(
        ruleset=ruleset,
        owner_type="building_definition",
        owner_key=orchard.key,
        purpose=ItemReference.Purpose.BUILDING_UPKEEP,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="food",
        amount=Decimal("1"),
    )
    ItemReference.objects.create(
        ruleset=ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=ItemReference.Purpose.RECIPE_INPUT,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        amount=Decimal("2"),
    )
    ItemReference.objects.create(
        ruleset=ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=ItemReference.Purpose.RECIPE_OUTPUT,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="food",
        amount=Decimal("4"),
    )
    ItemReference.objects.create(
        ruleset=ruleset,
        owner_type="building_definition",
        owner_key=hidden_mine.key,
        purpose=ItemReference.Purpose.BUILDING_UPKEEP,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        amount=Decimal("9"),
    )
    client.force_login(user)

    response = client.get(reverse("dashboard:home"))

    assert response.status_code == 200
    assert b"Production Balance" in response.content
    assert b"1 visible buildings included" in response.content
    assert b"Alerts" in response.content
    assert b"Surplus 3 resource:food." in response.content
    assert b"1.00 resource:food" in response.content
    assert b"2.00 resource:wood" in response.content
    assert b"4.00 resource:food" in response.content
    assert b"3.00 resource:food" in response.content
    assert b"9.00 resource:wood" not in response.content


def test_health_page_returns_json(client):
    response = client.get(reverse("dashboard:health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "Carta Arcanum"}
