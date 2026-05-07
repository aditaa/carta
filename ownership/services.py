from __future__ import annotations

from django.contrib.auth import get_user_model

from ownership.models import House, HouseMembership, Kingdom, KingdomMembership, Role

ROLE_RANK = {
    Role.READ_ONLY: 10,
    Role.MEMBER: 20,
    Role.MANAGER: 30,
    Role.ADMIN: 40,
}


def can_view_user(viewer, target_user) -> bool:
    if not _is_active_user(viewer) or not _is_active_user(target_user):
        return False
    if viewer.pk == target_user.pk or viewer.is_superuser:
        return True

    target_house_ids = HouseMembership.objects.filter(
        user=target_user,
        active=True,
    ).values("house_id")
    if HouseMembership.objects.filter(
        user=viewer,
        active=True,
        house_id__in=target_house_ids,
    ).exists():
        return True

    target_kingdom_ids = KingdomMembership.objects.filter(
        user=target_user,
        active=True,
    ).values("kingdom_id")
    return KingdomMembership.objects.filter(
        user=viewer,
        active=True,
        kingdom_id__in=target_kingdom_ids,
    ).exists()


def can_view_house(viewer, house: House) -> bool:
    if not _is_active_user(viewer):
        return False
    if viewer.is_superuser:
        return True
    if has_house_role(viewer, house):
        return True
    if house.kingdom_id is None:
        return False
    return has_kingdom_role(viewer, house.kingdom)


def can_view_kingdom(viewer, kingdom: Kingdom) -> bool:
    if not _is_active_user(viewer):
        return False
    if viewer.is_superuser:
        return True
    return has_kingdom_role(viewer, kingdom)


def has_house_role(viewer, house: House, minimum_role: Role = Role.READ_ONLY) -> bool:
    return _membership_meets_role(
        HouseMembership.objects.filter(user=viewer, house=house, active=True).first(),
        minimum_role,
    )


def has_kingdom_role(viewer, kingdom: Kingdom, minimum_role: Role = Role.READ_ONLY) -> bool:
    return _membership_meets_role(
        KingdomMembership.objects.filter(user=viewer, kingdom=kingdom, active=True).first(),
        minimum_role,
    )


def visible_house_ids(viewer) -> set[int]:
    if not _is_active_user(viewer):
        return set()
    if viewer.is_superuser:
        return set(House.objects.values_list("id", flat=True))

    house_ids = set(
        HouseMembership.objects.filter(user=viewer, active=True).values_list("house_id", flat=True)
    )
    kingdom_ids = KingdomMembership.objects.filter(user=viewer, active=True).values("kingdom_id")
    house_ids.update(House.objects.filter(kingdom_id__in=kingdom_ids).values_list("id", flat=True))
    return house_ids


def _membership_meets_role(membership, minimum_role: Role) -> bool:
    if membership is None:
        return False
    return ROLE_RANK[membership.role] >= ROLE_RANK[minimum_role]


def _is_active_user(user) -> bool:
    user_model = get_user_model()
    return isinstance(user, user_model) and user.is_active
