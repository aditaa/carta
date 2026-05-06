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
    HouseDenizenHolding,
    HouseHolding,
    HouseMembership,
    Kingdom,
    KingdomHolding,
    KingdomMembership,
    ThreeCrownsHolding,
)
from app.domains.auth.permissions import SCOPE_HOUSE, SCOPE_KINGDOM, Permission
from app.domains.auth.schemas import VisibilityScope
from app.domains.auth.service import (
    AuthenticationService,
    get_permission_service,
    hash_password,
    verify_password,
)

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
                    role=DenizenRole.admin,
                    can_view_house=True,
                ),
                KingdomMembership(
                    denizen_id=1,
                    kingdom_id=100,
                    role=DenizenRole.admin,
                    can_view_kingdom=True,
                ),
                DenizenHolding(
                    denizen_id=1,
                    item_type="resource",
                    item_key="crops",
                    amount=12,
                    note="Personal hold",
                ),
                HouseHolding(
                    house_id=10,
                    item_type="currency",
                    item_key="tower",
                    amount=7,
                    note="House bank",
                ),
                HouseDenizenHolding(
                    house_id=10,
                    denizen_id=1,
                    item_type="resource",
                    item_key="ore",
                    amount=5,
                    note="House-held denizen stash",
                ),
                KingdomHolding(
                    kingdom_id=100,
                    item_type="resource",
                    item_key="rarities",
                    amount=3,
                    note="Kingdom stash",
                ),
                ThreeCrownsHolding(
                    account_type="denizen",
                    denizen_id=1,
                    item_type="currency",
                    item_key="gold",
                    amount=2,
                    note="Three Crowns personal account",
                ),
                ThreeCrownsHolding(
                    account_type="house",
                    house_id=10,
                    item_type="resource",
                    item_key="crops",
                    amount=20,
                    note="Three Crowns house account",
                ),
                ThreeCrownsHolding(
                    account_type="kingdom",
                    kingdom_id=100,
                    item_type="currency",
                    item_key="tower",
                    amount=11,
                    note="Three Crowns kingdom account",
                ),
            ]
        )
        db.commit()

        service = AuthenticationService()
        scope = service.build_visibility_scope_from_db(db, denizen_id=1)
        holdings = service.list_visible_holdings(db, scope)
        denizen = db.get(Denizen, 1)

        assert scope.visible_house_ids == [10]
        assert scope.visible_kingdom_ids == [100]
        assert scope.visible_denizen_ids == [1]
        assert denizen is not None
        assert denizen.holdings[0].item_key == "crops"
        assert denizen.memberships[0].role == DenizenRole.admin
        assert [(item.item_key, item.amount) for item in holdings.denizen] == [("crops", 12.0)]
        assert [(item.scope_id, item.item_key, item.amount) for item in holdings.house] == [
            (10, "tower", 7.0)
        ]
        assert [
            (item.scope_id, item.denizen_id, item.item_key, item.amount)
            for item in holdings.house_denizen
        ] == [(10, 1, "ore", 5.0)]
        assert [(item.scope_id, item.item_key, item.amount) for item in holdings.kingdom] == [
            (100, "rarities", 3.0)
        ]
        assert [
            (item.account_type, item.account_id, item.item_key, item.amount)
            for item in holdings.three_crowns
        ] == [
            ("denizen", 1, "gold", 2.0),
            ("house", 10, "crops", 20.0),
            ("kingdom", 100, "tower", 11.0),
        ]
        assert service.can_edit_denizen_holdings(scope, denizen_id=1)
        assert service.can_edit_house_holdings(db, denizen_id=1, house_id=10)
        assert service.can_edit_house_denizen_holdings(db, denizen_id=1, house_id=10)
        assert service.can_edit_three_crowns_denizen_account(scope, account_denizen_id=1)
        assert service.can_edit_three_crowns_house_account(db, denizen_id=1, house_id=10)
        assert service.can_edit_three_crowns_kingdom_account(db, denizen_id=1, kingdom_id=100)
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_house_stashes_require_house_admin_role_to_edit() -> None:
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
                House(id=10, name="Admin House"),
                Denizen(id=1, email="admin@example.test", display_name="House Admin"),
                Denizen(id=2, email="manager@example.test", display_name="House Manager"),
                HouseMembership(denizen_id=1, house_id=10, role=DenizenRole.admin),
                HouseMembership(denizen_id=2, house_id=10, role=DenizenRole.manager),
            ]
        )
        db.commit()

        service = AuthenticationService()

        assert service.can_edit_house_holdings(db, denizen_id=1, house_id=10)
        assert service.can_edit_house_denizen_holdings(db, denizen_id=1, house_id=10)
        assert not service.can_edit_house_holdings(db, denizen_id=2, house_id=10)
        assert not service.can_edit_house_denizen_holdings(db, denizen_id=2, house_id=10)
        assert service.can_edit_denizen_holdings(
            VisibilityScope(denizen_id=2, visible_denizen_ids=[2]),
            denizen_id=2,
        )
        assert not service.can_edit_denizen_holdings(
            VisibilityScope(denizen_id=2, visible_denizen_ids=[2]),
            denizen_id=1,
        )
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_house_admin_can_grant_limited_bank_permission_to_manager() -> None:
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
                House(id=10, name="Grant House"),
                Denizen(id=1, email="admin@example.test", display_name="House Admin"),
                Denizen(id=2, email="manager@example.test", display_name="House Manager"),
                HouseMembership(denizen_id=1, house_id=10, role=DenizenRole.admin),
                HouseMembership(denizen_id=2, house_id=10, role=DenizenRole.manager),
            ]
        )
        db.commit()

        permissions = get_permission_service()

        assert not permissions.can(
            db,
            denizen_id=2,
            permission=Permission.HOUSE_MANAGE_BANK,
            scope_type=SCOPE_HOUSE,
            scope_id=10,
        )

        grant = permissions.create_grant(
            db,
            grantor_denizen_id=1,
            grantee_denizen_id=2,
            permission=Permission.HOUSE_MANAGE_BANK,
            scope_type=SCOPE_HOUSE,
            scope_id=10,
        )

        assert grant.permission == Permission.HOUSE_MANAGE_BANK
        assert permissions.can(
            db,
            denizen_id=2,
            permission=Permission.HOUSE_MANAGE_BANK,
            scope_type=SCOPE_HOUSE,
            scope_id=10,
        )
        assert AuthenticationService().can_edit_house_holdings(db, denizen_id=2, house_id=10)
        assert not permissions.can_grant(
            db,
            grantor_denizen_id=2,
            permission=Permission.HOUSE_MANAGE_DENIZEN_HOLDINGS,
            scope_type=SCOPE_HOUSE,
            scope_id=10,
        )
        with pytest.raises(PermissionError):
            permissions.create_grant(
                db,
                grantor_denizen_id=2,
                grantee_denizen_id=1,
                permission=Permission.HOUSE_GRANT_PERMISSIONS,
                scope_type=SCOPE_HOUSE,
                scope_id=10,
            )
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_kingdom_admin_can_grant_counting_house_permission() -> None:
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
                Kingdom(id=100, name="Grant Kingdom"),
                Denizen(id=1, email="admin@example.test", display_name="Kingdom Admin"),
                Denizen(id=2, email="manager@example.test", display_name="Kingdom Manager"),
                KingdomMembership(denizen_id=1, kingdom_id=100, role=DenizenRole.admin),
                KingdomMembership(denizen_id=2, kingdom_id=100, role=DenizenRole.manager),
            ]
        )
        db.commit()

        permissions = get_permission_service()

        assert permissions.create_grant(
            db,
            grantor_denizen_id=1,
            grantee_denizen_id=2,
            permission=Permission.THREE_CROWNS_MANAGE_KINGDOM_ACCOUNT,
            scope_type=SCOPE_KINGDOM,
            scope_id=100,
        )
        assert AuthenticationService().can_edit_three_crowns_kingdom_account(
            db,
            denizen_id=2,
            kingdom_id=100,
        )
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_three_crowns_accounts_use_respective_admin_permissions() -> None:
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
                Kingdom(id=100, name="Crown Kingdom"),
                House(id=10, name="Crown House", kingdom_id=100),
                Denizen(id=1, email="denizen@example.test", display_name="Denizen"),
                Denizen(id=2, email="house-admin@example.test", display_name="House Admin"),
                Denizen(id=3, email="kingdom-admin@example.test", display_name="Kingdom Admin"),
                Denizen(id=4, email="member@example.test", display_name="Member"),
                HouseMembership(denizen_id=2, house_id=10, role=DenizenRole.admin),
                HouseMembership(denizen_id=4, house_id=10, role=DenizenRole.member),
                KingdomMembership(denizen_id=3, kingdom_id=100, role=DenizenRole.admin),
                KingdomMembership(denizen_id=4, kingdom_id=100, role=DenizenRole.manager),
            ]
        )
        db.commit()

        service = AuthenticationService()

        assert service.can_edit_three_crowns_denizen_account(
            VisibilityScope(denizen_id=1, visible_denizen_ids=[1]),
            account_denizen_id=1,
        )
        assert not service.can_edit_three_crowns_denizen_account(
            VisibilityScope(denizen_id=4, visible_denizen_ids=[4]),
            account_denizen_id=1,
        )
        assert service.can_edit_three_crowns_house_account(db, denizen_id=2, house_id=10)
        assert not service.can_edit_three_crowns_house_account(db, denizen_id=4, house_id=10)
        assert service.can_edit_three_crowns_kingdom_account(db, denizen_id=3, kingdom_id=100)
        assert not service.can_edit_three_crowns_kingdom_account(db, denizen_id=4, kingdom_id=100)
    finally:
        db.close()
        Base.metadata.drop_all(engine)
