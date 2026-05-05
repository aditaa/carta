from dataclasses import dataclass

from app.domains.auth.schemas import VisibilityScope


@dataclass(frozen=True)
class MembershipVisibility:
    house_id: int
    user_ids: set[int]
    can_view_house: bool


class VisibilityService:
    def build_scope(
        self,
        user_id: int,
        memberships: list[MembershipVisibility],
    ) -> VisibilityScope:
        visible_user_ids = {user_id}
        visible_house_ids: set[int] = set()

        for membership in memberships:
            if not membership.can_view_house:
                continue
            visible_house_ids.add(membership.house_id)
            visible_user_ids.update(membership.user_ids)

        return VisibilityScope(
            user_id=user_id,
            visible_user_ids=sorted(visible_user_ids),
            visible_house_ids=sorted(visible_house_ids),
        )


def get_visibility_service() -> VisibilityService:
    return VisibilityService()
