from decimal import Decimal

import pytest

from buildings.models import BuildingDefinition
from production.models import ProductionRecipe
from resources.models import Resource
from rulesets.models import ItemReference, Ruleset
from solver.services import SolverTarget, solve_required_chain

pytestmark = pytest.mark.django_db


def create_ruleset():
    ruleset = Ruleset.objects.create(
        game="Carta Arcanum",
        rules_version="test",
        schema_version="1",
        source_path="test.rules.json",
        raw_data={},
    )
    for key in ["wood", "food", "lumberjack", "plank"]:
        Resource.objects.create(ruleset=ruleset, key=key, name=key.title())
    return ruleset


def create_building(ruleset, key):
    return BuildingDefinition.objects.create(
        ruleset=ruleset,
        key=key,
        name=key.replace("_", " ").title(),
        category="basic",
    )


def create_recipe(ruleset, *, key, building, inputs, outputs):
    recipe = ProductionRecipe.objects.create(
        ruleset=ruleset,
        key=key,
        building=building,
        recipe_type="production",
    )
    for index, (item_key, amount) in enumerate(inputs):
        ItemReference.objects.create(
            ruleset=ruleset,
            owner_type="production_recipe",
            owner_key=recipe.key,
            purpose=ItemReference.Purpose.RECIPE_INPUT,
            item_type=ItemReference.ItemType.RESOURCE,
            item_key=item_key,
            amount=Decimal(amount),
            sort_order=index,
        )
    for index, (item_key, amount) in enumerate(outputs):
        ItemReference.objects.create(
            ruleset=ruleset,
            owner_type="production_recipe",
            owner_key=recipe.key,
            purpose=ItemReference.Purpose.RECIPE_OUTPUT,
            item_type=ItemReference.ItemType.RESOURCE,
            item_key=item_key,
            amount=Decimal(amount),
            sort_order=index,
        )
    return recipe


def test_solver_calculates_required_buildings_and_missing_inputs():
    ruleset = create_ruleset()
    orchard = create_building(ruleset, "orchard")
    create_recipe(
        ruleset,
        key="orchard_food",
        building=orchard,
        inputs=[("wood", "2")],
        outputs=[("food", "4")],
    )

    result = solve_required_chain(
        ruleset=ruleset,
        target=SolverTarget(
            item_type=ItemReference.ItemType.RESOURCE,
            item_key="food",
            quantity=Decimal("6"),
        ),
    )

    assert result.has_blockers is True
    assert result.required_buildings[0].building_key == "orchard"
    assert result.required_buildings[0].quantity == Decimal("2")
    assert result.required_inputs[0].item_key == "wood"
    assert result.required_inputs[0].quantity == Decimal("4")
    assert result.missing_inputs[0].item_key == "wood"
    assert result.missing_inputs[0].quantity == Decimal("4")
    assert result.dependency_chain[0].recipe_key == "orchard_food"
    assert result.dependency_chain[0].output_quantity == Decimal("8.00")


def test_solver_resolves_transitive_recipe_dependencies():
    ruleset = create_ruleset()
    orchard = create_building(ruleset, "orchard")
    lumber_mill = create_building(ruleset, "lumber_mill")
    create_recipe(
        ruleset,
        key="orchard_food",
        building=orchard,
        inputs=[("plank", "2")],
        outputs=[("food", "4")],
    )
    create_recipe(
        ruleset,
        key="mill_planks",
        building=lumber_mill,
        inputs=[("wood", "3")],
        outputs=[("plank", "2")],
    )

    result = solve_required_chain(
        ruleset=ruleset,
        target=SolverTarget(
            item_type=ItemReference.ItemType.RESOURCE,
            item_key="food",
            quantity=Decimal("4"),
        ),
    )

    building_counts = {
        building.building_key: building.quantity for building in result.required_buildings
    }
    missing_inputs = {line.item_key: line.quantity for line in result.missing_inputs}

    assert building_counts == {"lumber_mill": Decimal("1"), "orchard": Decimal("1")}
    assert missing_inputs == {"wood": Decimal("3")}
    assert [step.recipe_key for step in result.dependency_chain] == [
        "orchard_food",
        "mill_planks",
    ]


def test_solver_reports_unknown_target_as_missing_input():
    ruleset = create_ruleset()

    result = solve_required_chain(
        ruleset=ruleset,
        target=SolverTarget(
            item_type=ItemReference.ItemType.RESOURCE,
            item_key="food",
            quantity=Decimal("3"),
        ),
    )

    assert result.required_buildings == []
    assert result.missing_inputs[0].item_key == "food"
    assert result.missing_inputs[0].quantity == Decimal("3")


def test_solver_detects_circular_dependencies():
    ruleset = create_ruleset()
    orchard = create_building(ruleset, "orchard")
    lumber_mill = create_building(ruleset, "lumber_mill")
    create_recipe(
        ruleset,
        key="orchard_food",
        building=orchard,
        inputs=[("plank", "1")],
        outputs=[("food", "1")],
    )
    create_recipe(
        ruleset,
        key="mill_planks",
        building=lumber_mill,
        inputs=[("food", "1")],
        outputs=[("plank", "1")],
    )

    result = solve_required_chain(
        ruleset=ruleset,
        target=SolverTarget(
            item_type=ItemReference.ItemType.RESOURCE,
            item_key="food",
            quantity=Decimal("1"),
        ),
    )

    assert result.has_blockers is True
    assert result.circular_dependencies == [["resource:food", "resource:plank", "resource:food"]]
    assert result.missing_inputs == []
