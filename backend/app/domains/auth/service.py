import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.auth.models import (
    Denizen,
    DenizenHolding,
    HouseHolding,
    HouseMembership,
    KingdomHolding,
    KingdomMembership,
)
from app.domains.auth.schemas import (
    AuthDenizen,
    DenizenHoldingItem,
    SharedHoldingItem,
    VisibilityScope,
    VisibleHoldings,
)

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 210_000


@dataclass(frozen=True)
class MembershipVisibility:
    house_id: int
    denizen_ids: set[int]
    can_view_house: bool


@dataclass(frozen=True)
class KingdomVisibility:
    kingdom_id: int
    denizen_ids: set[int]
    can_view_kingdom: bool


class VisibilityService:
    def build_scope(
        self,
        denizen_id: int,
        memberships: list[MembershipVisibility],
        kingdom_memberships: list[KingdomVisibility] | None = None,
    ) -> VisibilityScope:
        visible_denizen_ids = {denizen_id}
        visible_house_ids: set[int] = set()
        visible_kingdom_ids: set[int] = set()

        for membership in memberships:
            if not membership.can_view_house:
                continue
            visible_house_ids.add(membership.house_id)
            visible_denizen_ids.update(membership.denizen_ids)

        for membership in kingdom_memberships or []:
            if not membership.can_view_kingdom:
                continue
            visible_kingdom_ids.add(membership.kingdom_id)
            visible_denizen_ids.update(membership.denizen_ids)

        return VisibilityScope(
            denizen_id=denizen_id,
            visible_denizen_ids=sorted(visible_denizen_ids),
            visible_house_ids=sorted(visible_house_ids),
            visible_kingdom_ids=sorted(visible_kingdom_ids),
        )


def get_visibility_service() -> VisibilityService:
    return VisibilityService()


def hash_password(password: str, salt: str | None = None) -> str:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        password_salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    )
    return (
        f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${password_salt}$"
        f"{base64.urlsafe_b64encode(digest).decode('ascii')}"
    )


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iterations, salt, expected_digest = stored_hash.split("$", maxsplit=3)
    except ValueError:
        return False
    if algorithm != PASSWORD_ALGORITHM:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    )
    actual_digest = base64.urlsafe_b64encode(digest).decode("ascii")
    return hmac.compare_digest(actual_digest, expected_digest)


class AuthenticationService:
    def authenticate_denizen(self, db: Session, email: str, password: str) -> Denizen | None:
        denizen = db.scalar(select(Denizen).where(Denizen.email == email.lower()))
        if denizen is None or not denizen.is_active:
            return None
        if not verify_password(password, denizen.password_hash):
            return None
        return denizen

    def create_access_token(
        self,
        denizen: Denizen,
        secret_key: str,
        expires_minutes: int,
    ) -> str:
        expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)
        payload = {"sub": denizen.id, "exp": int(expires_at.timestamp())}
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        encoded_payload = _base64url_encode(payload_bytes)
        signature = _sign(encoded_payload, secret_key)
        return f"{encoded_payload}.{signature}"

    def denizen_from_token(self, db: Session, token: str, secret_key: str) -> Denizen | None:
        try:
            encoded_payload, signature = token.split(".", maxsplit=1)
        except ValueError:
            return None
        if not hmac.compare_digest(_sign(encoded_payload, secret_key), signature):
            return None
        try:
            payload = json.loads(_base64url_decode(encoded_payload))
        except (json.JSONDecodeError, ValueError):
            return None
        if int(payload.get("exp", 0)) < int(datetime.now(UTC).timestamp()):
            return None
        denizen_id = payload.get("sub")
        if not isinstance(denizen_id, int):
            return None
        denizen = db.get(Denizen, denizen_id)
        if denizen is None or not denizen.is_active:
            return None
        return denizen

    def serialize_denizen(self, denizen: Denizen) -> AuthDenizen:
        return AuthDenizen(
            id=denizen.id,
            email=denizen.email,
            display_name=denizen.display_name,
            role=denizen.role.value,
            religion=denizen.religion,
            primary_house_id=denizen.primary_house_id,
            primary_kingdom_id=denizen.primary_kingdom_id,
            is_active=denizen.is_active,
        )

    def build_visibility_scope_from_db(self, db: Session, denizen_id: int) -> VisibilityScope:
        house_ids = [
            row.house_id
            for row in db.scalars(
                select(HouseMembership).where(
                    HouseMembership.denizen_id == denizen_id,
                    HouseMembership.can_view_house.is_(True),
                )
            )
        ]
        kingdom_ids = [
            row.kingdom_id
            for row in db.scalars(
                select(KingdomMembership).where(
                    KingdomMembership.denizen_id == denizen_id,
                    KingdomMembership.can_view_kingdom.is_(True),
                )
            )
        ]
        visible_denizen_ids = {denizen_id}
        if house_ids:
            visible_denizen_ids.update(
                db.scalars(
                    select(HouseMembership.denizen_id).where(
                        HouseMembership.house_id.in_(house_ids)
                    )
                )
            )
        if kingdom_ids:
            visible_denizen_ids.update(
                db.scalars(
                    select(KingdomMembership.denizen_id).where(
                        KingdomMembership.kingdom_id.in_(kingdom_ids)
                    )
                )
            )

        return VisibilityScope(
            denizen_id=denizen_id,
            visible_denizen_ids=sorted(visible_denizen_ids),
            visible_house_ids=sorted(set(house_ids)),
            visible_kingdom_ids=sorted(set(kingdom_ids)),
        )

    def list_visible_holdings(self, db: Session, scope: VisibilityScope) -> VisibleHoldings:
        denizen_holdings = db.scalars(
            select(DenizenHolding).where(DenizenHolding.denizen_id == scope.denizen_id)
        ).all()
        house_holdings = []
        if scope.visible_house_ids:
            house_holdings = db.scalars(
                select(HouseHolding).where(HouseHolding.house_id.in_(scope.visible_house_ids))
            ).all()
        kingdom_holdings = []
        if scope.visible_kingdom_ids:
            kingdom_holdings = db.scalars(
                select(KingdomHolding).where(
                    KingdomHolding.kingdom_id.in_(scope.visible_kingdom_ids)
                )
            ).all()

        return VisibleHoldings(
            denizen=[
                DenizenHoldingItem(
                    id=holding.id,
                    item_type=holding.item_type,
                    item_key=holding.item_key,
                    amount=float(holding.amount),
                    note=holding.note,
                )
                for holding in denizen_holdings
            ],
            house=[
                SharedHoldingItem(
                    id=holding.id,
                    scope_type="house",
                    scope_id=holding.house_id,
                    item_type=holding.item_type,
                    item_key=holding.item_key,
                    amount=float(holding.amount),
                    note=holding.note,
                )
                for holding in house_holdings
            ],
            kingdom=[
                SharedHoldingItem(
                    id=holding.id,
                    scope_type="kingdom",
                    scope_id=holding.kingdom_id,
                    item_type=holding.item_type,
                    item_key=holding.item_key,
                    amount=float(holding.amount),
                    note=holding.note,
                )
                for holding in kingdom_holdings
            ],
        )


def get_authentication_service() -> AuthenticationService:
    return AuthenticationService()


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _sign(encoded_payload: str, secret_key: str) -> str:
    digest = hmac.new(
        secret_key.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _base64url_encode(digest)
