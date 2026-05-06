from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cli import create_denizen, import_rules
from app.db.base import Base
from app.domains.auth.models import Denizen, DenizenRole
from app.domains.auth.service import verify_password

pytestmark = pytest.mark.unit


def build_test_sessionmaker():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False), engine


def test_import_rules_cli_loads_dataset_and_reports_ruleset_id(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    SessionLocal, engine = build_test_sessionmaker()
    rules_file = Path(__file__).resolve().parents[2] / "rules" / "carta-arcanum-2.1.4.rules.json"
    monkeypatch.setattr(import_rules, "SessionLocal", SessionLocal)
    monkeypatch.setattr("sys.argv", ["import_rules", str(rules_file)])

    try:
        import_rules.main()
    finally:
        Base.metadata.drop_all(engine)

    assert "Imported Carta Arcanum 2.1.4 as ruleset_id=1" in capsys.readouterr().out


def test_create_denizen_cli_creates_lowercase_active_denizen_with_password(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    SessionLocal, engine = build_test_sessionmaker()
    monkeypatch.setattr(create_denizen, "SessionLocal", SessionLocal)
    monkeypatch.setattr(
        "sys.argv",
        [
            "create_denizen",
            "--email",
            "One@Example.Test",
            "--display-name",
            "Denizen One",
            "--role",
            "member",
            "--password",
            "swordfish",
        ],
    )

    try:
        create_denizen.main()
        with SessionLocal() as db:
            denizen = db.scalar(select(Denizen).where(Denizen.email == "one@example.test"))
    finally:
        Base.metadata.drop_all(engine)

    assert denizen is not None
    assert denizen.display_name == "Denizen One"
    assert denizen.role == DenizenRole.member
    assert denizen.is_active
    assert verify_password("swordfish", denizen.password_hash)
    assert "Denizen ready: one@example.test" in capsys.readouterr().out


def test_create_denizen_cli_updates_existing_denizen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal, engine = build_test_sessionmaker()
    with SessionLocal() as db:
        db.add(
            Denizen(
                email="one@example.test",
                display_name="Old Name",
                role=DenizenRole.read_only,
                is_active=False,
            )
        )
        db.commit()

    monkeypatch.setattr(create_denizen, "SessionLocal", SessionLocal)
    monkeypatch.setattr(
        "sys.argv",
        [
            "create_denizen",
            "--email",
            "one@example.test",
            "--display-name",
            "New Name",
            "--role",
            "admin",
            "--religion",
            "The Loom",
            "--password",
            "new-secret",
        ],
    )

    try:
        create_denizen.main()
        with SessionLocal() as db:
            denizens = db.scalars(select(Denizen)).all()
            denizen = denizens[0]
    finally:
        Base.metadata.drop_all(engine)

    assert len(denizens) == 1
    assert denizen.display_name == "New Name"
    assert denizen.role == DenizenRole.admin
    assert denizen.religion == "The Loom"
    assert denizen.is_active
    assert verify_password("new-secret", denizen.password_hash)
