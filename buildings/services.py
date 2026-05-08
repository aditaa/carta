from __future__ import annotations

from django.db.models import Count

from buildings.models import OwnedBuilding
from ownership.services import can_view_house, can_view_kingdom, can_view_user


def visible_owned_buildings(viewer):
    buildings = OwnedBuilding.objects.select_related(
        "definition",
        "ruleset",
        "user",
        "house",
        "kingdom",
    )
    if not viewer.is_authenticated or not viewer.is_active:
        return OwnedBuilding.objects.none()
    if viewer.is_superuser:
        return buildings

    visible_ids = [
        building.id
        for building in buildings
        if _can_view_owned_building(viewer=viewer, building=building)
    ]
    return buildings.filter(id__in=visible_ids)


def registry_summary(buildings):
    return {
        "total": buildings.count(),
        "by_status": list(
            buildings.values("status").annotate(count=Count("id")).order_by("status")
        ),
        "by_category": list(
            buildings.values("definition__category")
            .annotate(count=Count("id"))
            .order_by("definition__category")
        ),
    }


def _can_view_owned_building(*, viewer, building: OwnedBuilding) -> bool:
    if building.user_id is not None:
        return can_view_user(viewer, building.user)
    if building.house_id is not None:
        return can_view_house(viewer, building.house)
    if building.kingdom_id is not None:
        return can_view_kingdom(viewer, building.kingdom)
    return False
