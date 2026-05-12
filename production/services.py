from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from buildings.models import OwnedBuilding
from production.models import ProductionRecipe
from rulesets.models import ItemReference


@dataclass(frozen=True)
class ItemTotal:
    item_type: str
    item_key: str
    quantity: Decimal


def upkeep_totals(buildings) -> list[ItemTotal]:
    active_buildings = _active_buildings(buildings)
    totals = _empty_totals()
    for building in active_buildings:
        _add_item_refs(
            totals,
            ruleset=building.ruleset,
            owner_type="building_definition",
            owner_key=building.definition.key,
            purpose=ItemReference.Purpose.BUILDING_UPKEEP,
            multiplier=Decimal("1"),
        )
    return _total_lines(totals)


def production_totals(buildings) -> dict[str, list[ItemTotal]]:
    active_buildings = _active_buildings(buildings)
    totals = {
        "inputs": _empty_totals(),
        "outputs": _empty_totals(),
    }
    for building in active_buildings:
        recipes = ProductionRecipe.objects.filter(
            ruleset=building.ruleset,
            building=building.definition,
        )
        for recipe in recipes:
            _add_item_refs(
                totals["inputs"],
                ruleset=recipe.ruleset,
                owner_type="production_recipe",
                owner_key=recipe.key,
                purpose=ItemReference.Purpose.RECIPE_INPUT,
                multiplier=Decimal("1"),
            )
            _add_item_refs(
                totals["outputs"],
                ruleset=recipe.ruleset,
                owner_type="production_recipe",
                owner_key=recipe.key,
                purpose=ItemReference.Purpose.RECIPE_OUTPUT,
                multiplier=Decimal("1"),
            )
    return {
        "inputs": _total_lines(totals["inputs"]),
        "outputs": _total_lines(totals["outputs"]),
    }


def net_resource_balance(buildings) -> list[ItemTotal]:
    upkeep = _totals_by_key(upkeep_totals(buildings))
    production = production_totals(buildings)
    inputs = _totals_by_key(production["inputs"])
    outputs = _totals_by_key(production["outputs"])
    net = _empty_totals()
    for key, quantity in outputs.items():
        net[key] += quantity
    for key, quantity in inputs.items():
        net[key] -= quantity
    for key, quantity in upkeep.items():
        net[key] -= quantity
    return _total_lines(net)


def _format_quantity(quantity: Decimal) -> str:
    if quantity == quantity.to_integral_value():
        return str(quantity.quantize(Decimal(1)))
    return str(quantity.normalize())


def production_alerts(buildings) -> list[str]:
    net = net_resource_balance(buildings)
    if not net:
        return ["No active buildings with production or upkeep."]

    alerts = []
    for line in net:
        formatted_quantity = _format_quantity(abs(line.quantity))
        if line.quantity < 0:
            alerts.append(
                f"Missing {formatted_quantity} {line.item_type}:"
                f"{line.item_key} to balance upkeep and inputs."
            )
        elif line.quantity > 0:
            alerts.append(f"Surplus {formatted_quantity} {line.item_type}:{line.item_key}.")

    if not alerts:
        alerts.append("Production and upkeep are balanced.")

    return alerts


def balance_by_owner(buildings) -> list[dict]:
    owner_groups: dict[tuple[str, int], list] = {}
    for building in buildings:
        owner_key = _owner_group_key(building)
        owner_groups.setdefault(owner_key, []).append(building)

    panels = []
    for key, group in sorted(owner_groups.items()):
        production = production_totals(group)
        panels.append(
            {
                "owner": _owner_label(group[0]),
                "building_count": len(group),
                "upkeep": upkeep_totals(group),
                "production_inputs": production["inputs"],
                "production_outputs": production["outputs"],
                "deficits": deficit_totals(group),
                "surpluses": surplus_totals(group),
                "alerts": production_alerts(group),
            }
        )
    return panels


def _owner_group_key(building) -> tuple[str, int]:
    if getattr(building, "user_id", None) is not None:
        return ("user", building.user_id)
    if getattr(building, "house_id", None) is not None:
        return ("house", building.house_id)
    if getattr(building, "kingdom_id", None) is not None:
        return ("kingdom", building.kingdom_id)
    return ("unknown", getattr(building, "id", 0))


def _owner_label(building) -> str:
    return getattr(building, "owner_label", "Unknown owner")


def deficit_totals(buildings) -> list[ItemTotal]:
    return [
        ItemTotal(
            item_type=line.item_type,
            item_key=line.item_key,
            quantity=abs(line.quantity),
        )
        for line in net_resource_balance(buildings)
        if line.quantity < 0
    ]


def surplus_totals(buildings) -> list[ItemTotal]:
    return [line for line in net_resource_balance(buildings) if line.quantity > 0]


def _active_buildings(buildings) -> list[OwnedBuilding]:
    return [
        building
        for building in buildings
        if building.status == OwnedBuilding.Status.ACTIVE and building.definition_id
    ]


def _add_item_refs(
    totals,
    *,
    ruleset,
    owner_type: str,
    owner_key: str,
    purpose: ItemReference.Purpose,
    multiplier: Decimal,
) -> None:
    refs = ItemReference.objects.filter(
        ruleset=ruleset,
        owner_type=owner_type,
        owner_key=owner_key,
        purpose=purpose,
    )
    for ref in refs:
        totals[(ref.item_type, ref.item_key)] += ref.amount * multiplier


def _empty_totals():
    return defaultdict(Decimal)


def _totals_by_key(lines: list[ItemTotal]):
    return {(line.item_type, line.item_key): line.quantity for line in lines}


def _total_lines(totals) -> list[ItemTotal]:
    return [
        ItemTotal(item_type=item_type, item_key=item_key, quantity=quantity)
        for (item_type, item_key), quantity in sorted(totals.items())
        if quantity != 0
    ]
