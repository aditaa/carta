from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.domains.auth.schemas import (
    AuthToken,
    AuthUser,
    LoginRequest,
    VisibilityPreview,
    VisibilityScope,
)
from app.domains.auth.service import (
    MembershipVisibility,
    get_authentication_service,
    get_visibility_service,
)

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


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


@router.post("/login", response_model=AuthToken)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthToken:
    settings = get_settings()
    auth_service = get_authentication_service()
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return AuthToken(
        access_token=auth_service.create_access_token(
            user,
            settings.auth_secret_key,
            settings.access_token_minutes,
        ),
        user=auth_service.serialize_user(user),
    )


@router.get("/me", response_model=AuthUser)
def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    settings = get_settings()
    auth_service = get_authentication_service()
    user = auth_service.user_from_token(db, credentials.credentials, settings.auth_secret_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
        )
    return auth_service.serialize_user(user)
