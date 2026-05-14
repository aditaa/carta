import pytest
from django.urls import reverse

from progression.models import PhaseDefinition, PhaseUnlock, TitleDefinition
from rulesets.models import Ruleset


def create_user(email="progression@example.test"):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name="Progression User",
    )


@pytest.fixture
def ruleset(db):
    return Ruleset.objects.create(
        game="Carta Arcanum",
        rules_version="test",
        schema_version="1",
        source_path="test.rules.json",
        raw_data={},
    )


@pytest.mark.django_db
def test_progression_page_requires_login(client):
    response = client.get(reverse("progression:index"))

    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_progression_page_shows_empty_ruleset_state(client, ruleset):
    user = create_user()
    client.force_login(user)

    response = client.get(reverse("progression:index"))

    assert response.status_code == 200
    assert b"Carta Arcanum test" in response.content
    assert b"No phases are defined" in response.content
    assert b"No titles are defined" in response.content


@pytest.mark.django_db
def test_progression_page_shows_phase_unlocks_and_titles(client, ruleset):
    user = create_user()
    phase = PhaseDefinition.objects.create(
        ruleset=ruleset,
        key="settlement",
        name="Settlement",
        requirements=[{"kind": "building_count", "amount": 3}],
    )
    PhaseUnlock.objects.create(
        phase=phase,
        key="advanced_buildings",
        name="Advanced Buildings",
        unlock_type="building_category",
    )
    TitleDefinition.objects.create(
        ruleset=ruleset,
        key="baron",
        name="Baron",
        category="noble",
    )
    client.force_login(user)

    response = client.get(reverse("progression:index"))

    assert response.status_code == 200
    assert b"Settlement" in response.content
    assert b"Advanced Buildings" in response.content
    assert b"Baron" in response.content
    assert b"noble" in response.content
