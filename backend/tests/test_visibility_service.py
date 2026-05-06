import pytest

from app.domains.auth.service import MembershipVisibility, VisibilityService

pytestmark = pytest.mark.unit


def test_user_can_see_own_data_without_house_permissions() -> None:
    scope = VisibilityService().build_scope(denizen_id=1, memberships=[])

    assert scope.visible_denizen_ids == [1]
    assert scope.visible_house_ids == []


def test_house_permission_includes_house_denizens_and_house() -> None:
    scope = VisibilityService().build_scope(
        denizen_id=1,
        memberships=[
            MembershipVisibility(
                house_id=10,
                denizen_ids={1, 2, 3},
                can_view_house=True,
            )
        ],
    )

    assert scope.visible_denizen_ids == [1, 2, 3]
    assert scope.visible_house_ids == [10]


def test_membership_without_house_permission_does_not_expand_scope() -> None:
    scope = VisibilityService().build_scope(
        denizen_id=1,
        memberships=[
            MembershipVisibility(
                house_id=10,
                denizen_ids={1, 2, 3},
                can_view_house=False,
            )
        ],
    )

    assert scope.visible_denizen_ids == [1]
    assert scope.visible_house_ids == []
