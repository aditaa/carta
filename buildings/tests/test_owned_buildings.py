import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from buildings.models import BuildingDefinition, OwnedBuilding
from ownership.models import House, Kingdom
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
