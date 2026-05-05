from pydantic import BaseModel, Field


class VisibilityPreview(BaseModel):
    baseline: str
    house_scope: str
    future_roles: list[str] = Field(default_factory=list)


class VisibilityScope(BaseModel):
    user_id: int
    visible_user_ids: list[int] = Field(default_factory=list)
    visible_house_ids: list[int] = Field(default_factory=list)
