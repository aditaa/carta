from pydantic import BaseModel, Field


class VisibilityPreview(BaseModel):
    baseline: str
    house_scope: str
    future_roles: list[str] = Field(default_factory=list)


class VisibilityScope(BaseModel):
    user_id: int
    visible_user_ids: list[int] = Field(default_factory=list)
    visible_house_ids: list[int] = Field(default_factory=list)


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUser(BaseModel):
    id: int
    email: str
    display_name: str
    is_active: bool


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser
