import pytest
from django.contrib.auth import get_user_model

from ownership.models import House, HouseMembership, Kingdom, KingdomMembership, Role
from ownership.services import (
    can_view_house,
    can_view_kingdom,
    can_view_user,
    has_house_role,
    visible_house_ids,
)


def create_user(email: str, display_name: str = "Test Denizen"):
    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name=display_name,
    )


@pytest.mark.django_db
def test_user_can_view_self_but_not_unrelated_user():
    viewer = create_user("viewer@example.test", "Viewer")
    stranger = create_user("stranger@example.test", "Stranger")

    assert can_view_user(viewer, viewer)
    assert not can_view_user(viewer, stranger)


@pytest.mark.django_db
def test_shared_active_house_membership_allows_user_and_house_visibility():
    viewer = create_user("viewer@example.test", "Viewer")
    housemate = create_user("housemate@example.test", "Housemate")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=viewer, house=house, role=Role.READ_ONLY)
    HouseMembership.objects.create(user=housemate, house=house, role=Role.MEMBER)

    assert can_view_user(viewer, housemate)
    assert can_view_house(viewer, house)
    assert visible_house_ids(viewer) == {house.id}


@pytest.mark.django_db
def test_inactive_house_membership_does_not_allow_visibility():
    viewer = create_user("viewer@example.test", "Viewer")
    housemate = create_user("housemate@example.test", "Housemate")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=viewer, house=house, role=Role.ADMIN, active=False)
    HouseMembership.objects.create(user=housemate, house=house, role=Role.MEMBER)

    assert not can_view_user(viewer, housemate)
    assert not can_view_house(viewer, house)
    assert visible_house_ids(viewer) == set()


@pytest.mark.django_db
def test_house_role_checks_respect_rank_order():
    viewer = create_user("viewer@example.test", "Viewer")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=viewer, house=house, role=Role.MANAGER)

    assert has_house_role(viewer, house, Role.READ_ONLY)
    assert has_house_role(viewer, house, Role.MEMBER)
    assert has_house_role(viewer, house, Role.MANAGER)
    assert not has_house_role(viewer, house, Role.ADMIN)


@pytest.mark.django_db
def test_kingdom_membership_allows_kingdom_and_house_visibility():
    viewer = create_user("viewer@example.test", "Viewer")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    house = House.objects.create(key="bramble", name="House Bramble", kingdom=kingdom)
    KingdomMembership.objects.create(user=viewer, kingdom=kingdom, role=Role.READ_ONLY)

    assert can_view_kingdom(viewer, kingdom)
    assert can_view_house(viewer, house)
    assert visible_house_ids(viewer) == {house.id}


@pytest.mark.django_db
def test_superuser_can_view_users_houses_and_kingdoms():
    viewer = get_user_model().objects.create_superuser(
        email="admin@example.test",
        password="swordfish",
        display_name="Admin",
    )
    target = create_user("target@example.test", "Target")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    house = House.objects.create(key="bramble", name="House Bramble", kingdom=kingdom)

    assert can_view_user(viewer, target)
    assert can_view_house(viewer, house)
    assert can_view_kingdom(viewer, kingdom)
    assert visible_house_ids(viewer) == {house.id}
