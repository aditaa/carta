import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from buildings.models import BuildingDefinition, OwnedBuilding
from buildings.services import registry_summary, visible_owned_buildings
from ownership.models import House, HouseMembership, Kingdom, KingdomMembership
from rulesets.models import Ruleset

pytestmark = pytest.mark.django_db


def create_ruleset(version="test"):
    return Ruleset.objects.create(
        game="Carta Arcanum",
        rules_version=version,
        schema_version="1",
        source_path=f"{version}.rules.json",
        raw_data={},
    )


def create_definition(ruleset):
    return BuildingDefinition.objects.create(
        ruleset=ruleset,
        key="orchard",
        name="Orchard",
        category="basic",
    )


def create_user(email="builder@example.test"):
    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name="Builder",
    )


def test_owned_building_requires_exactly_one_owner():
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    building = OwnedBuilding(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        house=house,
    )

    with pytest.raises(ValidationError, match="exactly one owner"):
        building.full_clean()


def test_owned_building_owner_scope_must_match_owner_field():
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    house = House.objects.create(key="bramble", name="House Bramble")
    building = OwnedBuilding(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        house=house,
    )

    with pytest.raises(ValidationError, match="Denizen-owned buildings"):
        building.full_clean()


def test_owned_building_ruleset_must_match_definition_ruleset():
    ruleset = create_ruleset()
    other_ruleset = create_ruleset("other")
    definition = create_definition(ruleset)
    building = OwnedBuilding(
        ruleset=other_ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=create_user(),
    )

    with pytest.raises(ValidationError, match="ruleset must match"):
        building.full_clean()


def test_can_model_denizen_house_and_kingdom_buildings():
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")

    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        nickname="Aster's Orchard",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.HOUSE,
        house=house,
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.KINGDOM,
        kingdom=kingdom,
    )

    assert OwnedBuilding.objects.count() == 3
    assert str(OwnedBuilding.objects.get(nickname="Aster's Orchard")) == "Aster's Orchard"


def test_visible_owned_buildings_includes_personal_and_shared_house_buildings():
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    viewer = create_user()
    housemate = create_user("housemate@example.test")
    stranger = create_user("stranger@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=viewer, house=house)
    HouseMembership.objects.create(user=housemate, house=house)
    personal = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=viewer,
    )
    shared_house = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.HOUSE,
        house=house,
    )
    hidden = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=stranger,
    )

    visible_ids = set(visible_owned_buildings(viewer).values_list("id", flat=True))

    assert personal.id in visible_ids
    assert shared_house.id in visible_ids
    assert hidden.id not in visible_ids


def test_registry_summary_counts_visible_buildings_by_status_and_category():
    ruleset = create_ruleset()
    orchard = create_definition(ruleset)
    keep = BuildingDefinition.objects.create(
        ruleset=ruleset,
        key="keep",
        name="Keep",
        category="defensive",
    )
    user = create_user()
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.ACTIVE,
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=keep,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        status=OwnedBuilding.Status.DAMAGED,
    )

    summary = registry_summary(visible_owned_buildings(user))

    assert summary["total"] == 2
    assert summary["by_status"] == [
        {"status": "active", "count": 1},
        {"status": "damaged", "count": 1},
    ]
    assert summary["by_category"] == [
        {"definition__category": "basic", "count": 1},
        {"definition__category": "defensive", "count": 1},
    ]


def test_building_registry_page_requires_login(client):
    response = client.get(reverse("buildings:index"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_building_registry_page_lists_visible_buildings(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    viewer = create_user()
    stranger = create_user("stranger@example.test")
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=viewer,
        nickname="Visible Orchard",
        location="North field",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=stranger,
        nickname="Hidden Orchard",
    )
    client.force_login(viewer)

    response = client.get(reverse("buildings:index"))

    assert response.status_code == 200
    assert b"Visible Orchard" in response.content
    assert b"North field" in response.content
    assert b"Hidden Orchard" not in response.content


def test_building_create_page_requires_login(client):
    response = client.get(reverse("buildings:create"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_user_can_create_personal_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    client.force_login(user)

    response = client.post(
        reverse("buildings:create"),
        {
            "definition": definition.id,
            "owner": f"user:{user.id}",
            "nickname": "New Orchard",
            "location": "South field",
            "status": OwnedBuilding.Status.ACTIVE,
            "notes": "Freshly planted.",
        },
    )

    assert response.status_code == 302
    building = OwnedBuilding.objects.get(nickname="New Orchard")
    assert building.ruleset == ruleset
    assert building.user == user
    assert building.location == "South field"


def test_house_member_can_create_house_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=user, house=house)
    client.force_login(user)

    response = client.post(
        reverse("buildings:create"),
        {
            "definition": definition.id,
            "owner": f"house:{house.id}",
            "nickname": "House Orchard",
            "status": OwnedBuilding.Status.ACTIVE,
        },
    )

    assert response.status_code == 302
    assert OwnedBuilding.objects.get(nickname="House Orchard").house == house


def test_non_member_cannot_create_house_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    client.force_login(user)

    response = client.post(
        reverse("buildings:create"),
        {
            "definition": definition.id,
            "owner": f"house:{house.id}",
            "nickname": "Invalid Orchard",
            "status": OwnedBuilding.Status.ACTIVE,
        },
    )

    assert response.status_code == 200
    assert not OwnedBuilding.objects.filter(nickname="Invalid Orchard").exists()


def test_kingdom_member_can_create_kingdom_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    KingdomMembership.objects.create(user=user, kingdom=kingdom)
    client.force_login(user)

    response = client.post(
        reverse("buildings:create"),
        {
            "definition": definition.id,
            "owner": f"kingdom:{kingdom.id}",
            "nickname": "Kingdom Orchard",
            "status": OwnedBuilding.Status.ACTIVE,
        },
    )

    assert response.status_code == 302
    assert OwnedBuilding.objects.get(nickname="Kingdom Orchard").kingdom == kingdom
