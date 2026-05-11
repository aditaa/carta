from django.http import JsonResponse
from django.shortcuts import render

from buildings.services import visible_owned_buildings
from production.services import (
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
    return render(request, "dashboard/home.html", context)


def health(request):
    return JsonResponse({"status": "ok", "app": "Carta Arcanum"})
