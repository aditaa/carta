from django.http import Http404, JsonResponse
from django.shortcuts import render

from buildings.services import visible_owned_buildings
from production.services import (
    balance_by_owner,
    deficit_totals,
    production_alerts,
    production_totals,
    surplus_totals,
    upkeep_totals,
)


def home(request):
    context = {}
    if request.user.is_authenticated:
        buildings = visible_owned_buildings(request.user)
        production = production_totals(buildings)
        context["balance_panel"] = {
            "building_count": buildings.count(),
            "upkeep": upkeep_totals(buildings),
            "production_inputs": production["inputs"],
            "production_outputs": production["outputs"],
            "deficits": deficit_totals(buildings),
            "surpluses": surplus_totals(buildings),
            "alerts": production_alerts(buildings),
        }
        context["owner_panels"] = balance_by_owner(buildings)
    return render(request, "dashboard/home.html", context)


def health(request):
    return JsonResponse({"status": "ok", "app": "Carta Arcanum"})


def owner_detail(request, owner_type: str, owner_id: int):
    if not request.user.is_authenticated:
        raise Http404

    buildings = visible_owned_buildings(request.user)
    if owner_type not in {"user", "house", "kingdom"}:
        raise Http404

    if owner_type == "user":
        owner_buildings = buildings.filter(user_id=owner_id)
    elif owner_type == "house":
        owner_buildings = buildings.filter(house_id=owner_id)
    else:
        owner_buildings = buildings.filter(kingdom_id=owner_id)

    if not owner_buildings.exists():
        raise Http404

    production = production_totals(owner_buildings)
    context = {
        "owner_label": owner_buildings.first().owner_label,
        "owner_type": owner_type,
        "owner_id": owner_id,
        "balance_panel": {
            "building_count": owner_buildings.count(),
            "upkeep": upkeep_totals(owner_buildings),
            "production_inputs": production["inputs"],
            "production_outputs": production["outputs"],
            "deficits": deficit_totals(owner_buildings),
            "surpluses": surplus_totals(owner_buildings),
            "alerts": production_alerts(owner_buildings),
        },
        "buildings": owner_buildings,
    }
    return render(request, "dashboard/owner_detail.html", context)
