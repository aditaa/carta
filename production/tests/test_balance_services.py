from decimal import Decimal

import pytest

from buildings.models import BuildingDefinition, OwnedBuilding
from production.models import ProductionRecipe
from production.services import (
    balance_by_owner,
    deficit_totals,
    net_resource_balance,
    production_alerts,
    production_totals,
    surplus_totals,
    upkeep_totals,
)
from resources.models import Resource
from rulesets.models import ItemReference, Ruleset

pytestmark = pytest.mark.django_db


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
    Resource.objects.create(ruleset=ruleset, key="stone", name="Stone")
    return ruleset


def create_building_definition(ruleset, key="orchard"):
    return BuildingDefinition.objects.create(
        ruleset=ruleset,
        key=key,
        name=key.title(),
        category="basic",
    )


def create_user(email="producer@example.test", display_name="Producer"):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name=display_name,
    )


def add_item_ref(*, ruleset, owner_type, owner_key, purpose, item_key, amount):
    return ItemReference.objects.create(
        ruleset=ruleset,
        owner_type=owner_type,
        owner_key=owner_key,
        purpose=purpose,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key=item_key,
        amount=Decimal(amount),
    )


def test_upkeep_totals_sum_active_owned_buildings():
    ruleset = create_ruleset()
    orchard = create_building_definition(ruleset)
    user = create_user()
    active_orchard = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    second_active_orchard = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    inactive_orchard = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.INACTIVE,
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="building_definition",
        owner_key="orchard",
        purpose=ItemReference.Purpose.BUILDING_UPKEEP,
        item_key="food",
        amount="2",
    )

    totals = upkeep_totals([active_orchard, second_active_orchard, inactive_orchard])

    assert totals[0].item_key == "food"
    assert totals[0].quantity == Decimal("4")


def test_production_totals_sum_recipe_inputs_and_outputs_for_active_buildings():
    ruleset = create_ruleset()
    orchard = create_building_definition(ruleset)
    user = create_user()
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    recipe = ProductionRecipe.objects.create(
        ruleset=ruleset,
        key="orchard_food",
        building=orchard,
        recipe_type="production",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=ItemReference.Purpose.RECIPE_INPUT,
        item_key="wood",
        amount="1",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=ItemReference.Purpose.RECIPE_OUTPUT,
        item_key="food",
        amount="4",
    )

    totals = production_totals([building])

    assert totals["inputs"][0].item_key == "wood"
    assert totals["inputs"][0].quantity == Decimal("1")
    assert totals["outputs"][0].item_key == "food"
    assert totals["outputs"][0].quantity == Decimal("4")


def test_net_resource_balance_subtracts_inputs_and_upkeep_from_outputs():
    ruleset = create_ruleset()
    orchard = create_building_definition(ruleset)
    user = create_user()
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    recipe = ProductionRecipe.objects.create(
        ruleset=ruleset,
        key="orchard_food",
        building=orchard,
        recipe_type="production",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="building_definition",
        owner_key="orchard",
        purpose=ItemReference.Purpose.BUILDING_UPKEEP,
        item_key="food",
        amount="2",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=ItemReference.Purpose.RECIPE_INPUT,
        item_key="wood",
        amount="1",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=ItemReference.Purpose.RECIPE_OUTPUT,
        item_key="food",
        amount="4",
    )

    totals = {
        (line.item_type, line.item_key): line.quantity for line in net_resource_balance([building])
    }

    assert totals[(ItemReference.ItemType.RESOURCE, "food")] == Decimal("2")
    assert totals[(ItemReference.ItemType.RESOURCE, "wood")] == Decimal("-1")


def test_deficit_and_surplus_totals_split_net_balance():
    ruleset = create_ruleset()
    orchard = create_building_definition(ruleset)
    user = create_user()
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    recipe = ProductionRecipe.objects.create(
        ruleset=ruleset,
        key="orchard_food",
        building=orchard,
        recipe_type="production",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=ItemReference.Purpose.RECIPE_INPUT,
        item_key="wood",
        amount="3",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=ItemReference.Purpose.RECIPE_OUTPUT,
        item_key="food",
        amount="5",
    )

    deficits = deficit_totals([building])
    surpluses = surplus_totals([building])

    assert deficits[0].item_key == "wood"
    assert deficits[0].quantity == Decimal("3")
    assert surpluses[0].item_key == "food"
    assert surpluses[0].quantity == Decimal("5")


def test_production_alerts_reports_missing_and_surplus_messages():
    ruleset = create_ruleset()
    orchard = create_building_definition(ruleset)
    user = create_user()
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    recipe = ProductionRecipe.objects.create(
        ruleset=ruleset,
        key="orchard_food",
        building=orchard,
        recipe_type="production",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="building_definition",
        owner_key="orchard",
        purpose=ItemReference.Purpose.BUILDING_UPKEEP,
        item_key="food",
        amount="2",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=ItemReference.Purpose.RECIPE_INPUT,
        item_key="wood",
        amount="3",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=ItemReference.Purpose.RECIPE_OUTPUT,
        item_key="food",
        amount="8",
    )

    alerts = production_alerts([building])

    assert "Missing 3 resource:wood to balance upkeep and inputs." in alerts
    assert "Surplus 6 resource:food." in alerts


def test_balance_by_owner_returns_panels_for_each_owner():
    ruleset = create_ruleset()
    orchard = create_building_definition(ruleset)
    keep = create_building_definition(ruleset, key="keep")
    user = create_user()
    other_user = create_user(
        "other@example.test",
        display_name="Other Producer",
    )
    first_building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    second_building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=keep,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=other_user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="building_definition",
        owner_key=orchard.key,
        purpose=ItemReference.Purpose.BUILDING_UPKEEP,
        item_key="food",
        amount="1",
    )
    add_item_ref(
        ruleset=ruleset,
        owner_type="building_definition",
        owner_key=keep.key,
        purpose=ItemReference.Purpose.BUILDING_UPKEEP,
        item_key="wood",
        amount="2",
    )

    panels = balance_by_owner([first_building, second_building])

    assert any(panel["owner"] == f"Denizen: {user.display_name}" for panel in panels)
    assert any(panel["owner"] == f"Denizen: {other_user.display_name}" for panel in panels)
    assert {panel["building_count"] for panel in panels} == {1}
