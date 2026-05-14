from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from production.models import ProductionRecipe
from rulesets.models import ItemReference, Ruleset


@dataclass(frozen=True)
class SolverTarget:
    item_type: str
    item_key: str
    quantity: Decimal


@dataclass(frozen=True)
class RequiredBuilding:
    building_key: str
    building_name: str
    quantity: Decimal


@dataclass(frozen=True)
class RequiredInput:
    item_type: str
    item_key: str
    quantity: Decimal


@dataclass(frozen=True)
class DependencyStep:
    recipe_key: str
    building_key: str
    output_item_type: str
    output_item_key: str
    output_quantity: Decimal
    runs: Decimal


@dataclass(frozen=True)
class SolverResult:
    target: SolverTarget
    required_buildings: list[RequiredBuilding]
    required_inputs: list[RequiredInput]
    missing_inputs: list[RequiredInput]
    surplus_outputs: list[RequiredInput]
    dependency_chain: list[DependencyStep]
    circular_dependencies: list[list[str]]

    @property
    def has_blockers(self) -> bool:
        return bool(self.missing_inputs or self.circular_dependencies)


def solve_required_chain(*, ruleset: Ruleset, target: SolverTarget) -> SolverResult:
    context = _SolverContext(ruleset=ruleset, target=target)
    context.resolve(target)
    return context.result()


class _SolverContext:
    def __init__(self, *, ruleset: Ruleset, target: SolverTarget):
        self.ruleset = ruleset
        self.target = target
        self.required_buildings = defaultdict(Decimal)
        self.building_names = {}
        self.required_inputs = defaultdict(Decimal)
        self.missing_inputs = defaultdict(Decimal)
        self.surplus_outputs = defaultdict(Decimal)
        self.dependency_chain = []
        self.circular_dependencies = []
        self.stack = []

    def resolve(self, demand: SolverTarget) -> None:
        item_key = _item_key(demand.item_type, demand.item_key)
        demand_key = (demand.item_type, demand.item_key)
        available_surplus = self.surplus_outputs[demand_key]
        if available_surplus:
            consumed_quantity = min(available_surplus, demand.quantity)
            self.surplus_outputs[demand_key] -= consumed_quantity
            demand = SolverTarget(
                item_type=demand.item_type,
                item_key=demand.item_key,
                quantity=demand.quantity - consumed_quantity,
            )
            if demand.quantity <= 0:
                return

        if item_key in self.stack:
            cycle = self.stack[self.stack.index(item_key) :] + [item_key]
            self.circular_dependencies.append(cycle)
            return

        recipe, output_ref = _producer_for(self.ruleset, demand)
        if recipe is None or output_ref is None:
            self.missing_inputs[demand_key] += demand.quantity
            return

        runs = _required_runs(demand.quantity, output_ref.amount)
        output_quantity = output_ref.amount * runs
        surplus_quantity = output_quantity - demand.quantity
        if surplus_quantity > 0:
            self.surplus_outputs[demand_key] += surplus_quantity
        building_key = recipe.building.key
        self.required_buildings[building_key] += runs
        self.building_names[building_key] = recipe.building.name
        self.dependency_chain.append(
            DependencyStep(
                recipe_key=recipe.key,
                building_key=building_key,
                output_item_type=demand.item_type,
                output_item_key=demand.item_key,
                output_quantity=output_quantity,
                runs=runs,
            )
        )

        self.stack.append(item_key)
        for ref in _recipe_refs(recipe, ItemReference.Purpose.RECIPE_INPUT):
            required_quantity = ref.amount * runs
            self.required_inputs[(ref.item_type, ref.item_key)] += required_quantity
            self.resolve(
                SolverTarget(
                    item_type=ref.item_type,
                    item_key=ref.item_key,
                    quantity=required_quantity,
                )
            )
        self.stack.pop()

    def result(self) -> SolverResult:
        return SolverResult(
            target=self.target,
            required_buildings=[
                RequiredBuilding(
                    building_key=building_key,
                    building_name=self.building_names[building_key],
                    quantity=quantity,
                )
                for building_key, quantity in sorted(self.required_buildings.items())
            ],
            required_inputs=_input_lines(self.required_inputs),
            missing_inputs=_input_lines(self.missing_inputs),
            surplus_outputs=_input_lines(self.surplus_outputs),
            dependency_chain=self.dependency_chain,
            circular_dependencies=self.circular_dependencies,
        )


def _producer_for(
    ruleset: Ruleset,
    target: SolverTarget,
) -> tuple[ProductionRecipe | None, ItemReference | None]:
    output_ref = (
        ItemReference.objects.filter(
            ruleset=ruleset,
            purpose=ItemReference.Purpose.RECIPE_OUTPUT,
            item_type=target.item_type,
            item_key=target.item_key,
        )
        .order_by("owner_key", "sort_order", "id")
        .first()
    )
    if output_ref is None:
        return None, None
    recipe = (
        ProductionRecipe.objects.select_related("building")
        .filter(ruleset=ruleset, key=output_ref.owner_key)
        .first()
    )
    return recipe, output_ref


def _recipe_refs(recipe: ProductionRecipe, purpose: ItemReference.Purpose):
    return ItemReference.objects.filter(
        ruleset=recipe.ruleset,
        owner_type="production_recipe",
        owner_key=recipe.key,
        purpose=purpose,
    )


def _required_runs(quantity: Decimal, output_quantity: Decimal) -> Decimal:
    if output_quantity <= 0:
        return Decimal("0")
    return (quantity / output_quantity).to_integral_value(rounding=ROUND_CEILING)


def _input_lines(totals) -> list[RequiredInput]:
    return [
        RequiredInput(item_type=item_type, item_key=item_key, quantity=quantity)
        for (item_type, item_key), quantity in sorted(totals.items())
        if quantity != 0
    ]


def _item_key(item_type: str, item_key: str) -> str:
    return f"{item_type}:{item_key}"
