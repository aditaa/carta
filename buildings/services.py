from __future__ import annotations

from django.db.models import Count, Q

from buildings.models import BuildingLedgerEntry, OwnedBuilding
from ownership.services import (
    visible_house_ids,
    visible_kingdom_ids,
    visible_user_ids,
)


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

    user_ids = visible_user_ids(viewer)
    house_ids = visible_house_ids(viewer)
    kingdom_ids = visible_kingdom_ids(viewer)
    return buildings.filter(
        Q(user_id__in=user_ids)
        | Q(house_id__in=house_ids)
        | Q(kingdom_id__in=kingdom_ids)
    )


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


def log_building_event(
    *,
    building: OwnedBuilding | None,
    actor,
    action: BuildingLedgerEntry.Action,
    building_label: str = "",
    changes: dict | None = None,
    note: str = "",
) -> BuildingLedgerEntry:
    label = building_label or str(building)
    return BuildingLedgerEntry.objects.create(
        building=building,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        building_label=label,
        changes=changes or {},
        note=note,
    )


