import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.auth.models import User
from app.domains.auth.schemas import AuthUser, VisibilityScope

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 210_000


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
    def authenticate_user(self, db: Session, email: str, password: str) -> User | None:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_access_token(self, user: User, secret_key: str, expires_minutes: int) -> str:
        expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)
        payload = {"sub": user.id, "exp": int(expires_at.timestamp())}
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        encoded_payload = _base64url_encode(payload_bytes)
        signature = _sign(encoded_payload, secret_key)
        return f"{encoded_payload}.{signature}"

    def user_from_token(self, db: Session, token: str, secret_key: str) -> User | None:
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
        user_id = payload.get("sub")
        if not isinstance(user_id, int):
            return None
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        return user

    def serialize_user(self, user: User) -> AuthUser:
        return AuthUser(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
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
