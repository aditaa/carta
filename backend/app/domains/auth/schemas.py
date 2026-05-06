from pydantic import BaseModel, Field


class VisibilityPreview(BaseModel):
    baseline: str
    house_scope: str
    future_roles: list[str] = Field(default_factory=list)


class VisibilityScope(BaseModel):
    denizen_id: int
    visible_denizen_ids: list[int] = Field(default_factory=list)
    visible_house_ids: list[int] = Field(default_factory=list)
    visible_kingdom_ids: list[int] = Field(default_factory=list)


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthDenizen(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    religion: str | None = None
    primary_house_id: int | None = None
    primary_kingdom_id: int | None = None
    is_active: bool


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    denizen: AuthDenizen


class DenizenHoldingItem(BaseModel):
    id: int
    item_type: str
    item_key: str
    amount: float
    note: str | None = None


class SharedHoldingItem(BaseModel):
    id: int
    scope_type: str
    scope_id: int
    denizen_id: int | None = None
    item_type: str
    item_key: str
    amount: float
    note: str | None = None


class ThreeCrownsHoldingItem(BaseModel):
    id: int
    account_type: str
    account_id: int
    item_type: str
    item_key: str
    amount: float
    note: str | None = None


class VisibleHoldings(BaseModel):
    denizen: list[DenizenHoldingItem] = Field(default_factory=list)
    house: list[SharedHoldingItem] = Field(default_factory=list)
    house_denizen: list[SharedHoldingItem] = Field(default_factory=list)
    kingdom: list[SharedHoldingItem] = Field(default_factory=list)
    three_crowns: list[ThreeCrownsHoldingItem] = Field(default_factory=list)
