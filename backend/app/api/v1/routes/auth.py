from fastapi import APIRouter

from app.domains.auth.schemas import VisibilityPreview, VisibilityScope
from app.domains.auth.service import (
    MembershipVisibility,
    get_visibility_service,
)

router = APIRouter()


@router.get("/visibility-preview", response_model=VisibilityPreview)
def visibility_preview() -> VisibilityPreview:
    return VisibilityPreview(
        baseline="A user can see their own data.",
        house_scope=(
            "A user with house permission can see their own data plus users "
            "and assets in that house."
        ),
        future_roles=["admin", "house_manager", "read_only_member"],
    )


@router.get("/sample-scope", response_model=VisibilityScope)
def sample_visibility_scope() -> VisibilityScope:
    visibility_service = get_visibility_service()
    return visibility_service.build_scope(
        user_id=1,
        memberships=[
            MembershipVisibility(
                house_id=10,
                user_ids={1, 2, 3},
                can_view_house=True,
            ),
            MembershipVisibility(
                house_id=20,
                user_ids={1, 4},
                can_view_house=False,
            ),
        ],
    )
