from decimal import Decimal

import pytest
from django.urls import reverse

from buildings.models import BuildingDefinition
from production.models import ProductionRecipe
from resources.models import Resource
from rulesets.models import ItemReference, Ruleset

pytestmark = pytest.mark.django_db


def create_user(email="solver@example.test"):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name="Solver User",
    )


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


def create_recipe(ruleset):
    orchard = BuildingDefinition.objects.create(
        ruleset=ruleset,
        key="orchard",
        name="Orchard",
        category="basic",
    )
    recipe = ProductionRecipe.objects.create(
        ruleset=ruleset,
        key="orchard_food",
        building=orchard,
        recipe_type="production",
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


def test_solver_page_requires_login(client):
    response = client.get(reverse("solver:index"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_solver_page_shows_empty_state_without_ruleset(client):
    user = create_user()
    client.force_login(user)

    response = client.get(reverse("solver:index"))

    assert response.status_code == 200
    assert b"No ruleset has been imported yet" in response.content


def test_solver_page_lists_recipe_outputs_as_targets(client):
    ruleset = create_ruleset()
    create_recipe(ruleset)
    user = create_user()
    client.force_login(user)

    response = client.get(reverse("solver:index"))

    assert response.status_code == 200
    assert b"resource:food" in response.content
    assert b"Solve" in response.content


def test_solver_page_shows_solution_for_selected_target(client):
    ruleset = create_ruleset()
    create_recipe(ruleset)
    user = create_user()
    client.force_login(user)

    response = client.get(
        reverse("solver:index"),
        {
            "target": "resource:food",
            "quantity": "6",
        },
    )

    assert response.status_code == 200
    assert b"Required Buildings" in response.content
    assert b"2 Orchard" in response.content
    assert b"4.00 resource:wood" in response.content
    assert b"orchard_food" in response.content
