import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from buildings.forms import OwnedBuildingForm
from buildings.models import BuildingDefinition, BuildingLedgerEntry, OwnedBuilding
from buildings.services import (
    editable_owned_buildings,
    log_building_event,
    registry_summary,
    visible_owned_buildings,
)
from ownership.models import House, HouseMembership, Kingdom, KingdomMembership, Role
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


def test_owned_building_owner_label_returns_actual_owner():
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")

    denizen_building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
    )
    house_building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.HOUSE,
        house=house,
    )
    kingdom_building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.KINGDOM,
        kingdom=kingdom,
    )

    assert denizen_building.owner_label == f"Denizen: {user.display_name}"
    assert house_building.owner_label == f"House: {house.name}"
    assert kingdom_building.owner_label == f"Kingdom: {kingdom.name}"


def test_can_log_building_registry_event():
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        nickname="Aster's Orchard",
    )

    entry = log_building_event(
        building=building,
        actor=user,
        action=BuildingLedgerEntry.Action.CREATED,
        changes={"nickname": "Aster's Orchard"},
    )

    assert entry.building == building
    assert entry.actor == user
    assert entry.building_label == "Aster's Orchard"
    assert entry.changes == {"nickname": "Aster's Orchard"}


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


@pytest.mark.django_db
def test_visible_owned_buildings_includes_kingdom_buildings_for_members():
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    viewer = create_user()
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    KingdomMembership.objects.create(user=viewer, kingdom=kingdom)
    kingdom_building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.KINGDOM,
        kingdom=kingdom,
    )
    hidden = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.KINGDOM,
        kingdom=Kingdom.objects.create(key="other", name="Other Kingdom"),
    )

    visible_ids = set(visible_owned_buildings(viewer).values_list("id", flat=True))

    assert kingdom_building.id in visible_ids
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


def test_building_registry_page_filters_visible_buildings(client):
    ruleset = create_ruleset()
    orchard = create_definition(ruleset)
    keep = BuildingDefinition.objects.create(
        ruleset=ruleset,
        key="keep",
        name="Keep",
        category="defensive",
    )
    viewer = create_user()
    stranger = create_user("stranger@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=viewer, house=house)
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=viewer,
        nickname="Visible Orchard",
        status=OwnedBuilding.Status.ACTIVE,
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=keep,
        owner_scope=OwnedBuilding.OwnerScope.HOUSE,
        house=house,
        nickname="Visible Keep",
        status=OwnedBuilding.Status.DAMAGED,
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=keep,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=stranger,
        nickname="Hidden Keep",
        status=OwnedBuilding.Status.DAMAGED,
    )
    client.force_login(viewer)

    response = client.get(
        reverse("buildings:index"),
        {
            "status": OwnedBuilding.Status.DAMAGED,
            "category": "defensive",
            "owner_scope": OwnedBuilding.OwnerScope.HOUSE,
        },
    )

    assert response.status_code == 200
    assert b"Visible Keep" in response.content
    assert b"Visible Orchard" not in response.content
    assert b"Hidden Keep" not in response.content
    assert response.context["summary"]["total"] == 1


def test_building_registry_page_filters_by_owner(client):
    ruleset = create_ruleset()
    orchard = create_definition(ruleset)
    viewer = create_user()
    stranger = create_user("stranger@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=viewer, house=house)
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.HOUSE,
        house=house,
        nickname="House Orchard",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=viewer,
        nickname="Personal Orchard",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=stranger,
        nickname="Hidden Orchard",
    )
    client.force_login(viewer)

    response = client.get(
        reverse("buildings:index"),
        {
            "owner": f"house:{house.id}",
        },
    )

    assert response.status_code == 200
    assert b"House Orchard" in response.content
    assert b"Personal Orchard" not in response.content
    assert b"Hidden Orchard" not in response.content
    assert response.context["summary"]["total"] == 1


def test_building_registry_page_filters_by_visible_denizen_owner(client):
    ruleset = create_ruleset()
    orchard = create_definition(ruleset)
    viewer = create_user("viewer@example.test")
    viewer.display_name = "Viewer"
    viewer.save()
    housemate = create_user("housemate@example.test")
    housemate.display_name = "Housemate"
    housemate.save()
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=viewer, house=house)
    HouseMembership.objects.create(user=housemate, house=house)
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=viewer,
        nickname="Personal Orchard",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=housemate,
        nickname="Housemate Orchard",
    )
    client.force_login(viewer)

    response = client.get(
        reverse("buildings:index"),
        {
            "owner": f"user:{housemate.id}",
        },
    )

    assert response.status_code == 200
    assert b"Housemate" in response.content
    assert b"Housemate Orchard" in response.content
    assert b"Personal Orchard" not in response.content
    assert response.context["summary"]["total"] == 1


def test_building_registry_superuser_can_filter_by_any_visible_owner(client):
    ruleset = create_ruleset()
    orchard = create_definition(ruleset)
    admin = get_user_model().objects.create_superuser(
        email="admin@example.test",
        password="swordfish",
        display_name="Admin",
    )
    owner = create_user("owner@example.test")
    owner.display_name = "Owner"
    owner.save()
    house = House.objects.create(key="bramble", name="House Bramble")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=owner,
        nickname="Owner Orchard",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.HOUSE,
        house=house,
        nickname="House Orchard",
    )
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=orchard,
        owner_scope=OwnedBuilding.OwnerScope.KINGDOM,
        kingdom=kingdom,
        nickname="Kingdom Orchard",
    )
    client.force_login(admin)

    response = client.get(
        reverse("buildings:index"),
        {
            "owner": f"user:{owner.id}",
        },
    )

    assert response.status_code == 200
    assert b"Owner" in response.content
    assert b"House: House Bramble" in response.content
    assert b"Kingdom: ValRann" in response.content
    assert b"Owner Orchard" in response.content
    assert b"House Orchard" not in response.content
    assert b"Kingdom Orchard" not in response.content
    assert response.context["summary"]["total"] == 1


def test_building_registry_page_ignores_invalid_choice_filters(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        nickname="Visible Orchard",
    )
    client.force_login(user)

    response = client.get(
        reverse("buildings:index"),
        {
            "status": "not-real",
            "owner_scope": "not-real",
        },
    )

    assert response.status_code == 200
    assert b"Visible Orchard" in response.content


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
    assert BuildingLedgerEntry.objects.filter(
        building=building,
        action=BuildingLedgerEntry.Action.CREATED,
    ).exists()


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


def test_read_only_house_member_cannot_create_house_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=user, house=house, role=Role.READ_ONLY)
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


def test_malformed_owner_choice_shows_form_error():
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    form = OwnedBuildingForm(
        user,
        {
            "definition": definition.id,
            "owner": "user:not-a-number",
            "nickname": "Invalid Orchard",
            "status": OwnedBuilding.Status.ACTIVE,
        },
    )
    form.fields["owner"].choices = [*form.fields["owner"].choices, ("user:not-a-number", "Bad")]

    assert not form.is_valid()
    assert "Choose a valid owner." in form.non_field_errors()
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


def test_visible_buildings_can_be_read_without_edit_access(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=user, house=house, role=Role.READ_ONLY)
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.HOUSE,
        house=house,
        nickname="House Orchard",
    )
    client.force_login(user)

    response = client.get(reverse("buildings:index"))

    assert building.id in set(visible_owned_buildings(user).values_list("id", flat=True))
    assert building.id not in set(editable_owned_buildings(user).values_list("id", flat=True))
    assert response.status_code == 200
    assert b"House Orchard" in response.content
    assert b"Read only" in response.content
    assert reverse("buildings:edit", args=[building.id]).encode() not in response.content


def test_user_can_edit_visible_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        nickname="Old Orchard",
    )
    client.force_login(user)

    response = client.post(
        reverse("buildings:edit", args=[building.id]),
        {
            "definition": definition.id,
            "owner": f"user:{user.id}",
            "nickname": "Renamed Orchard",
            "location": "East field",
            "status": OwnedBuilding.Status.DAMAGED,
            "notes": "Storm damage.",
        },
    )

    assert response.status_code == 302
    building.refresh_from_db()
    assert building.nickname == "Renamed Orchard"
    assert building.status == OwnedBuilding.Status.DAMAGED
    entry = BuildingLedgerEntry.objects.get(action=BuildingLedgerEntry.Action.UPDATED)
    assert entry.changes["nickname"] == {"from": "Old Orchard", "to": "Renamed Orchard"}


def test_htmx_building_create_form_request_returns_partial_template(client):
    ruleset = create_ruleset()
    create_definition(ruleset)
    user = create_user()
    client.force_login(user)

    response = client.get(reverse("buildings:create"), headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert b"Add building" in response.content
    assert b"hx-post" in response.content
    assert b"Cancel" in response.content


def test_htmx_building_edit_form_request_returns_partial_template(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        nickname="Old Orchard",
    )
    client.force_login(user)

    response = client.get(
        reverse("buildings:edit", args=[building.id]),
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert b"Edit building" in response.content
    assert b"hx-post" in response.content
    assert b"Cancel" in response.content


def test_user_cannot_edit_hidden_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    viewer = create_user()
    stranger = create_user("stranger@example.test")
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=stranger,
        nickname="Hidden Orchard",
    )
    client.force_login(viewer)

    response = client.get(reverse("buildings:edit", args=[building.id]))

    assert response.status_code == 404


def test_read_only_house_member_cannot_edit_visible_house_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=user, house=house, role=Role.READ_ONLY)
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.HOUSE,
        house=house,
        nickname="House Orchard",
    )
    client.force_login(user)

    response = client.post(
        reverse("buildings:edit", args=[building.id]),
        {
            "definition": definition.id,
            "owner": f"house:{house.id}",
            "nickname": "Compromised Orchard",
            "status": OwnedBuilding.Status.DAMAGED,
        },
    )

    assert response.status_code == 404
    building.refresh_from_db()
    assert building.nickname == "House Orchard"
    assert building.status == OwnedBuilding.Status.ACTIVE


def test_user_can_delete_visible_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=user,
        nickname="Old Orchard",
    )
    client.force_login(user)

    response = client.post(reverse("buildings:delete", args=[building.id]))

    assert response.status_code == 302
    assert not OwnedBuilding.objects.filter(id=building.id).exists()
    entry = BuildingLedgerEntry.objects.get(action=BuildingLedgerEntry.Action.DELETED)
    assert entry.building is None
    assert entry.building_label == "Old Orchard"


def test_user_cannot_delete_hidden_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    viewer = create_user()
    stranger = create_user("stranger@example.test")
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.DENIZEN,
        user=stranger,
        nickname="Hidden Orchard",
    )
    client.force_login(viewer)

    response = client.post(reverse("buildings:delete", args=[building.id]))

    assert response.status_code == 404
    assert OwnedBuilding.objects.filter(id=building.id).exists()


def test_read_only_kingdom_member_cannot_delete_visible_kingdom_building(client):
    ruleset = create_ruleset()
    definition = create_definition(ruleset)
    user = create_user()
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    KingdomMembership.objects.create(user=user, kingdom=kingdom, role=Role.READ_ONLY)
    building = OwnedBuilding.objects.create(
        ruleset=ruleset,
        definition=definition,
        owner_scope=OwnedBuilding.OwnerScope.KINGDOM,
        kingdom=kingdom,
        nickname="Kingdom Orchard",
    )
    client.force_login(user)

    response = client.post(reverse("buildings:delete", args=[building.id]))

    assert response.status_code == 404
    assert OwnedBuilding.objects.filter(id=building.id).exists()
