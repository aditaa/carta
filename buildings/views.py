from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from buildings.forms import OwnedBuildingForm
from buildings.models import BuildingLedgerEntry, OwnedBuilding
from buildings.services import log_building_event, registry_summary, visible_owned_buildings


@login_required
def index(request):
    buildings = visible_owned_buildings(request.user)
    return render(
        request,
        "buildings/index.html",
        {
            "buildings": buildings,
            "summary": registry_summary(buildings),
        },
    )


@login_required
def create(request):
    if request.method == "POST":
        form = OwnedBuildingForm(request.user, request.POST)
        if form.is_valid():
            building = form.save()
            log_building_event(
                building=building,
                actor=request.user,
                action=BuildingLedgerEntry.Action.CREATED,
                changes={"building": str(building)},
            )
            return redirect("buildings:index")
    else:
        form = OwnedBuildingForm(request.user)
    return render(request, "buildings/form.html", {"form": form})


@login_required
def edit(request, building_id):
    building = get_visible_building_or_404(request.user, building_id)
    before = _building_snapshot(building)
    if request.method == "POST":
        form = OwnedBuildingForm(request.user, request.POST, instance=building)
        if form.is_valid():
            building = form.save()
            changes = _building_changes(before, _building_snapshot(building))
            log_building_event(
                building=building,
                actor=request.user,
                action=BuildingLedgerEntry.Action.UPDATED,
                changes=changes,
            )
            return redirect("buildings:index")
    else:
        form = OwnedBuildingForm(request.user, instance=building)
    return render(request, "buildings/form.html", {"form": form, "building": building})


def get_visible_building_or_404(user, building_id) -> OwnedBuilding:
    building = get_object_or_404(OwnedBuilding, id=building_id)
    if not visible_owned_buildings(user).filter(id=building.id).exists():
        raise Http404
    return building


def _building_snapshot(building: OwnedBuilding) -> dict:
    return {
        "definition": building.definition_id,
        "owner_scope": building.owner_scope,
        "user": building.user_id,
        "house": building.house_id,
        "kingdom": building.kingdom_id,
        "nickname": building.nickname,
        "location": building.location,
        "status": building.status,
        "notes": building.notes,
    }


def _building_changes(before: dict, after: dict) -> dict:
    return {
        key: {"from": before[key], "to": after[key]} for key in before if before[key] != after[key]
    }
