import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domains.auth.models import (
    Denizen,
    DenizenHolding,
    DenizenRole,
    House,
    HouseMembership,
    Kingdom,
    KingdomMembership,
)
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
            Denizen(
                email="inactive@example.test",
                display_name="Inactive Denizen",
                password_hash=hash_password("secret"),
                is_active=False,
            )
        )
        db.commit()

        assert (
            AuthenticationService().authenticate_denizen(
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
        user = Denizen(
            email="token@example.test",
            display_name="Token Denizen",
            password_hash=hash_password("secret"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        service = AuthenticationService()
        token = service.create_access_token(user, "test-secret", 30)
        token_user = service.denizen_from_token(db, token, "test-secret")

        assert token_user is not None
        assert token_user.email == "token@example.test"
        assert service.denizen_from_token(db, token, "wrong-secret") is None
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_denizen_roles_default_to_read_only_and_serialize_profile_fields() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        denizen = Denizen(
            email="role@example.test",
            display_name="Role Denizen",
            religion="The Loom",
            primary_house_id=10,
            primary_kingdom_id=100,
        )
        db.add(denizen)
        db.commit()
        db.refresh(denizen)

        serialized = AuthenticationService().serialize_denizen(denizen)

        assert denizen.role == DenizenRole.read_only
        assert serialized.role == "read_only"
        assert serialized.religion == "The Loom"
        assert serialized.primary_house_id == 10
        assert serialized.primary_kingdom_id == 100
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_denizen_can_link_to_house_kingdom_and_hold_resources() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        db.add_all(
            [
                Kingdom(id=100, name="Test Kingdom"),
                House(id=10, name="Test House", kingdom_id=100),
                Denizen(
                    id=1,
                    email="hold@example.test",
                    display_name="Holding Denizen",
                    role=DenizenRole.member,
                    religion="Old Roads",
                    primary_house_id=10,
                    primary_kingdom_id=100,
                ),
                HouseMembership(
                    denizen_id=1,
                    house_id=10,
                    role=DenizenRole.manager,
                    can_view_house=True,
                ),
                KingdomMembership(
                    denizen_id=1,
                    kingdom_id=100,
                    role=DenizenRole.read_only,
                    can_view_kingdom=True,
                ),
                DenizenHolding(
                    denizen_id=1,
                    item_type="resource",
                    item_key="crops",
                    amount=12,
                    note="Personal hold",
                ),
            ]
        )
        db.commit()

        service = AuthenticationService()
        scope = service.build_visibility_scope_from_db(db, denizen_id=1)
        denizen = db.get(Denizen, 1)

        assert scope.visible_house_ids == [10]
        assert scope.visible_kingdom_ids == [100]
        assert scope.visible_denizen_ids == [1]
        assert denizen is not None
        assert denizen.holdings[0].item_key == "crops"
        assert denizen.memberships[0].role == DenizenRole.manager
    finally:
        db.close()
        Base.metadata.drop_all(engine)
