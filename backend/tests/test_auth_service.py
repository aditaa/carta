import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domains.auth.models import User
from app.domains.auth.service import AuthenticationService, hash_password, verify_password

pytestmark = pytest.mark.unit


def test_password_hash_verification_round_trip() -> None:
    stored_hash = hash_password("correct horse battery")

    assert verify_password("correct horse battery", stored_hash)
    assert not verify_password("wrong password", stored_hash)


def test_authentication_rejects_inactive_user() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        db.add(
            User(
                email="inactive@example.test",
                display_name="Inactive User",
                password_hash=hash_password("secret"),
                is_active=False,
            )
        )
        db.commit()

        assert (
            AuthenticationService().authenticate_user(
                db,
                "inactive@example.test",
                "secret",
            )
            is None
        )
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_token_round_trip_returns_active_user() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        user = User(
            email="token@example.test",
            display_name="Token User",
            password_hash=hash_password("secret"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        service = AuthenticationService()
        token = service.create_access_token(user, "test-secret", 30)
        token_user = service.user_from_token(db, token, "test-secret")

        assert token_user is not None
        assert token_user.email == "token@example.test"
        assert service.user_from_token(db, token, "wrong-secret") is None
    finally:
        db.close()
        Base.metadata.drop_all(engine)
