from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from buildings.forms import OwnedBuildingForm
from buildings.models import BuildingLedgerEntry, OwnedBuilding
from buildings.services import (
    building_owner_choices,
    editable_owned_buildings,
    log_building_event,
    registry_summary,
    visible_owned_buildings,
)


@login_required
def index(request):
    base_buildings = visible_owned_buildings(request.user)
    filters = _registry_filters(request)
    buildings = _filter_buildings(base_buildings, filters)
    editable_ids = set(
        editable_owned_buildings(request.user)
        .filter(id__in=buildings.values("id"))
        .values_list("id", flat=True)
    )
    context = {
        "buildings": buildings,
        "editable_building_ids": editable_ids,
        "filters": filters,
        "filter_options": _registry_filter_options(request.user, base_buildings),
        "summary": registry_summary(buildings),
    }
    template = (
        "buildings/_registry_results.html"
        if request.headers.get("HX-Request")
        else "buildings/index.html"
    )
    return render(request, template, context)


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
            if request.headers.get("HX-Request"):
                response = HttpResponse()
                response["HX-Redirect"] = reverse("buildings:index")
                return response
            return redirect("buildings:index")
    else:
        form = OwnedBuildingForm(request.user)

    template = (
        "buildings/_form.html" if request.headers.get("HX-Request") else "buildings/form.html"
    )
    return render(request, template, {"form": form})


@login_required
def edit(request, building_id):
    building = get_editable_building_or_404(request.user, building_id)
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
            if request.headers.get("HX-Request"):
                response = HttpResponse()
                response["HX-Redirect"] = reverse("buildings:index")
                return response
            return redirect("buildings:index")
    else:
        form = OwnedBuildingForm(request.user, instance=building)

    template = (
        "buildings/_form.html" if request.headers.get("HX-Request") else "buildings/form.html"
    )
    return render(request, template, {"form": form, "building": building})


@login_required
def delete(request, building_id):
    building = get_editable_building_or_404(request.user, building_id)
    if request.method == "POST":
        label = str(building)
        changes = _building_snapshot(building)
        building.delete()
        log_building_event(
            building=None,
            actor=request.user,
            action=BuildingLedgerEntry.Action.DELETED,
            building_label=label,
            changes=changes,
        )
        return redirect("buildings:index")
    return render(request, "buildings/confirm_delete.html", {"building": building})


def get_visible_building_or_404(user, building_id) -> OwnedBuilding:
    building = get_object_or_404(OwnedBuilding, id=building_id)
    if not visible_owned_buildings(user).filter(id=building.id).exists():
        raise Http404
    return building


def get_editable_building_or_404(user, building_id) -> OwnedBuilding:
    building = get_object_or_404(OwnedBuilding, id=building_id)
    if not editable_owned_buildings(user).filter(id=building.id).exists():
        raise Http404
    return building


def _registry_filters(request) -> dict:
    return {
        "status": request.GET.get("status", ""),
        "category": request.GET.get("category", ""),
        "owner_scope": request.GET.get("owner_scope", ""),
        "owner": request.GET.get("owner", ""),
    }


def _registry_filter_options(user, buildings) -> dict:
    return {
        "statuses": OwnedBuilding.Status.choices,
        "categories": buildings.values_list("definition__category", flat=True)
        .distinct()
        .order_by("definition__category"),
        "owner_scopes": OwnedBuilding.OwnerScope.choices,
        "owners": _owner_filter_options(user),
    }


def _filter_buildings(buildings, filters: dict):
    if filters["status"] in OwnedBuilding.Status.values:
        buildings = buildings.filter(status=filters["status"])
    if filters["category"]:
        buildings = buildings.filter(definition__category=filters["category"])
    if filters["owner_scope"] in OwnedBuilding.OwnerScope.values:
        buildings = buildings.filter(owner_scope=filters["owner_scope"])
    owner = filters["owner"]
    if owner:
        owner_type, _, raw_id = owner.partition(":")
        if raw_id.isdigit():
            if owner_type == "user":
                buildings = buildings.filter(user_id=raw_id)
            elif owner_type == "house":
                buildings = buildings.filter(house_id=raw_id)
            elif owner_type == "kingdom":
                buildings = buildings.filter(kingdom_id=raw_id)
    return buildings


def _owner_filter_options(user) -> list[tuple[str, str]]:
    return building_owner_choices(user, include_visible_users=True, editable_only=False)


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
