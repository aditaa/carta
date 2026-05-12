from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from buildings.models import BuildingLedgerEntry, OwnedBuilding
from ownership.models import House, Kingdom
from ownership.services import (
    visible_house_ids,
    visible_kingdom_ids,
    visible_user_ids,
)


def building_owner_choices(viewer, *, include_visible_users: bool = False) -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = []
    user_ids = visible_user_ids(viewer) if include_visible_users else {viewer.id}
    users = (
        get_user_model()
        .objects.filter(id__in=user_ids)
        .order_by(
            "display_name",
            "email",
        )
    )
    choices.extend((f"user:{user.id}", user.display_name) for user in users)

    houses = House.objects.filter(id__in=visible_house_ids(viewer)).order_by("name")
    choices.extend((f"house:{house.id}", f"House: {house.name}") for house in houses)

    kingdoms = Kingdom.objects.filter(id__in=visible_kingdom_ids(viewer)).order_by("name")
    choices.extend((f"kingdom:{kingdom.id}", f"Kingdom: {kingdom.name}") for kingdom in kingdoms)
    return choices


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
        Q(user_id__in=user_ids) | Q(house_id__in=house_ids) | Q(kingdom_id__in=kingdom_ids)
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
