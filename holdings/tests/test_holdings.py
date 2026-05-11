from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from holdings.models import HoldingAccount, HoldingBalance, HoldingLedgerEntry
from holdings.services import (
    can_edit_holding_account,
    correct,
    deposit,
    editable_holding_accounts,
    get_balance,
    transfer,
    visible_holding_accounts,
    withdraw,
)
from ownership.models import House, HouseMembership, Kingdom, KingdomMembership, Role
from resources.models import Currency, Resource
from rulesets.models import ItemReference, Ruleset

pytestmark = pytest.mark.django_db


def create_ruleset():
    ruleset = Ruleset.objects.create(
        game="Carta Arcanum",
        rules_version="test",
        schema_version="1",
        source_path="test.rules.json",
        raw_data={},
    )
    Resource.objects.create(ruleset=ruleset, key="wood", name="Wood")
    Currency.objects.create(ruleset=ruleset, key="copper", name="Copper", copper_value=1)
    return ruleset


def create_user(email="denizen@example.test"):
    return get_user_model().objects.create_user(
        email=email,
        password="swordfish",
        display_name="Test Denizen",
    )


def test_holding_account_validates_single_owner():
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    account = HoldingAccount(scope=HoldingAccount.Scope.DENIZEN, user=user, house=house)

    with pytest.raises(ValidationError, match="exactly one owner"):
        account.full_clean()


def test_house_denizen_account_requires_user_and_house():
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    account = HoldingAccount(scope=HoldingAccount.Scope.HOUSE_DENIZEN, user=user, house=house)

    account.full_clean()

    invalid = HoldingAccount(scope=HoldingAccount.Scope.HOUSE_DENIZEN, user=user)
    with pytest.raises(ValidationError, match="one user and one house"):
        invalid.full_clean()


def test_can_model_denizen_house_kingdom_and_three_crowns_accounts():
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")

    HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=user)
    HoldingAccount.objects.create(scope=HoldingAccount.Scope.HOUSE, house=house)
    HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.HOUSE_DENIZEN,
        user=create_user("house-held@example.test"),
        house=House.objects.create(key="house-held", name="House Held"),
    )
    HoldingAccount.objects.create(scope=HoldingAccount.Scope.KINGDOM, kingdom=kingdom)
    HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.THREE_CROWNS_DENIZEN,
        user=create_user("three-crowns-denizen@example.test"),
    )
    HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.THREE_CROWNS_HOUSE,
        house=House.objects.create(key="crown-house", name="Crown House"),
    )
    HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.THREE_CROWNS_KINGDOM,
        kingdom=Kingdom.objects.create(key="crown-kingdom", name="Crown Kingdom"),
    )

    assert HoldingAccount.objects.count() == 7


def test_deposit_creates_balance_and_ledger_entry():
    ruleset = create_ruleset()
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=create_user())

    balance = deposit(
        account=account,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        quantity=Decimal("5"),
        note="Starting stock",
    )

    assert balance.quantity == Decimal("5")
    entry = HoldingLedgerEntry.objects.get()
    assert entry.action == HoldingLedgerEntry.Action.DEPOSIT
    assert entry.note == "Starting stock"


def test_withdraw_requires_available_quantity():
    ruleset = create_ruleset()
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=create_user())
    deposit(
        account=account,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        quantity=Decimal("2"),
    )

    with pytest.raises(ValidationError, match="Insufficient holdings"):
        withdraw(
            account=account,
            ruleset=ruleset,
            item_type=ItemReference.ItemType.RESOURCE,
            item_key="wood",
            quantity=Decimal("3"),
        )


def test_transfer_moves_quantity_between_accounts():
    ruleset = create_ruleset()
    source = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=create_user())
    destination = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.DENIZEN,
        user=create_user("other@example.test"),
    )
    deposit(
        account=source,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.CURRENCY,
        item_key="copper",
        quantity=Decimal("10"),
    )

    source_balance, destination_balance = transfer(
        source=source,
        destination=destination,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.CURRENCY,
        item_key="copper",
        quantity=Decimal("4"),
    )

    assert source_balance.quantity == Decimal("6")
    assert destination_balance.quantity == Decimal("4")
    assert HoldingLedgerEntry.objects.filter(action=HoldingLedgerEntry.Action.TRANSFER).exists()


def test_correction_sets_balance_quantity():
    ruleset = create_ruleset()
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=create_user())

    balance = correct(
        account=account,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        quantity=Decimal("7"),
    )

    assert balance.quantity == Decimal("7")
    assert get_balance(
        account=account,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
    ).quantity == Decimal("7")


def test_balance_rejects_unknown_rules_item():
    ruleset = create_ruleset()
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=create_user())

    with pytest.raises(ValidationError, match="resource:stone does not exist"):
        HoldingBalance(
            account=account,
            ruleset=ruleset,
            item_type=ItemReference.ItemType.RESOURCE,
            item_key="stone",
            quantity=Decimal("1"),
        ).full_clean()


def test_special_item_type_is_not_supported_for_holdings():
    ruleset = create_ruleset()
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=create_user())

    with pytest.raises(ValidationError, match="not a supported holding item type"):
        deposit(
            account=account,
            ruleset=ruleset,
            item_type=ItemReference.ItemType.SPECIAL,
            item_key="favor",
            quantity=Decimal("1"),
        )


def test_visible_holding_accounts_includes_personal_and_shared_house_accounts():
    viewer = create_user()
    housemate = create_user("housemate@example.test")
    stranger = create_user("stranger@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=viewer, house=house)
    HouseMembership.objects.create(user=housemate, house=house)
    personal = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=viewer)
    shared_house = HoldingAccount.objects.create(scope=HoldingAccount.Scope.HOUSE, house=house)
    stranger_account = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.DENIZEN,
        user=stranger,
    )

    visible_ids = set(visible_holding_accounts(viewer).values_list("id", flat=True))

    assert personal.id in visible_ids
    assert shared_house.id in visible_ids
    assert stranger_account.id not in visible_ids


def test_house_denizen_account_requires_visibility_to_user_and_house():
    viewer = create_user()
    housemate = create_user("housemate@example.test")
    stranger = create_user("stranger@example.test")
    house = House.objects.create(key="bramble", name="House Bramble")
    other_house = House.objects.create(key="other", name="Other House")
    HouseMembership.objects.create(user=viewer, house=house)
    HouseMembership.objects.create(user=housemate, house=house)
    visible_account = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.HOUSE_DENIZEN,
        user=housemate,
        house=house,
    )
    hidden_account = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.HOUSE_DENIZEN,
        user=stranger,
        house=other_house,
    )

    visible_ids = set(visible_holding_accounts(viewer).values_list("id", flat=True))

    assert visible_account.id in visible_ids
    assert hidden_account.id not in visible_ids


def test_editable_holding_accounts_require_owner_or_member_role():
    viewer = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    kingdom = Kingdom.objects.create(key="valrann", name="ValRann")
    HouseMembership.objects.create(user=viewer, house=house, role=Role.READ_ONLY)
    KingdomMembership.objects.create(user=viewer, kingdom=kingdom, role=Role.MEMBER)
    personal = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=viewer)
    read_only_house = HoldingAccount.objects.create(scope=HoldingAccount.Scope.HOUSE, house=house)
    editable_kingdom = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.KINGDOM,
        kingdom=kingdom,
    )

    editable_ids = set(editable_holding_accounts(viewer).values_list("id", flat=True))

    assert personal.id in editable_ids
    assert editable_kingdom.id in editable_ids
    assert read_only_house.id not in editable_ids
    assert not can_edit_holding_account(viewer=viewer, account=read_only_house)


def test_holdings_page_requires_login(client):
    response = client.get(reverse("holdings:index"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_holdings_page_lists_visible_accounts_and_balances(client):
    ruleset = create_ruleset()
    viewer = create_user()
    stranger = create_user("stranger@example.test")
    account = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.DENIZEN,
        user=viewer,
        name="Personal Stores",
    )
    HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.DENIZEN,
        user=stranger,
        name="Hidden Stores",
    )
    deposit(
        account=account,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        quantity=Decimal("4"),
    )
    client.force_login(viewer)

    response = client.get(reverse("holdings:index"))

    assert response.status_code == 200
    assert b"Personal Stores" in response.content
    assert reverse("holdings:detail", args=[account.id]).encode() in response.content
    assert b"4.00 resource:wood" in response.content
    assert b"Hidden Stores" not in response.content


def test_holding_detail_page_requires_login(client):
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=create_user())

    response = client.get(reverse("holdings:detail", args=[account.id]))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_holding_detail_page_shows_balances_and_ledger(client):
    ruleset = create_ruleset()
    user = create_user()
    account = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.DENIZEN,
        user=user,
        name="Personal Stores",
    )
    deposit(
        account=account,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        quantity=Decimal("4"),
        note="Starting stock",
    )
    correct(
        account=account,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        quantity=Decimal("6"),
        note="Inventory correction",
    )
    client.force_login(user)

    response = client.get(reverse("holdings:detail", args=[account.id]))

    assert response.status_code == 200
    assert b"Personal Stores" in response.content
    assert b"resource:wood" in response.content
    assert b"6.00" in response.content
    assert b"Deposit" in response.content
    assert b"Starting stock" in response.content
    assert b"Correction" in response.content
    assert b"Inventory correction" in response.content


def test_holding_detail_page_rejects_hidden_account(client):
    viewer = create_user()
    stranger = create_user("stranger@example.test")
    account = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.DENIZEN,
        user=stranger,
        name="Hidden Stores",
    )
    client.force_login(viewer)

    response = client.get(reverse("holdings:detail", args=[account.id]))

    assert response.status_code == 404
    assert b"Hidden Stores" not in response.content


def test_holding_adjust_page_requires_login(client):
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=create_user())

    response = client.get(reverse("holdings:adjust", args=[account.id]))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_user_can_deposit_to_visible_holding_account(client):
    ruleset = create_ruleset()
    user = create_user()
    account = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.DENIZEN,
        user=user,
        name="Personal Stores",
    )
    client.force_login(user)

    response = client.post(
        reverse("holdings:adjust", args=[account.id]),
        {
            "action": HoldingLedgerEntry.Action.DEPOSIT,
            "ruleset": ruleset.id,
            "item_type": ItemReference.ItemType.RESOURCE,
            "item_key": "wood",
            "quantity": "6",
            "note": "Event payout",
        },
    )

    assert response.status_code == 302
    balance = HoldingBalance.objects.get(account=account, item_key="wood")
    assert balance.quantity == Decimal("6")
    entry = HoldingLedgerEntry.objects.get(account=account)
    assert entry.action == HoldingLedgerEntry.Action.DEPOSIT
    assert entry.note == "Event payout"


def test_user_can_withdraw_from_visible_holding_account(client):
    ruleset = create_ruleset()
    user = create_user()
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=user)
    deposit(
        account=account,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        quantity=Decimal("6"),
    )
    client.force_login(user)

    response = client.post(
        reverse("holdings:adjust", args=[account.id]),
        {
            "action": HoldingLedgerEntry.Action.WITHDRAWAL,
            "ruleset": ruleset.id,
            "item_type": ItemReference.ItemType.RESOURCE,
            "item_key": "wood",
            "quantity": "2",
        },
    )

    assert response.status_code == 302
    balance = HoldingBalance.objects.get(account=account, item_key="wood")
    assert balance.quantity == Decimal("4")
    assert HoldingLedgerEntry.objects.filter(
        account=account,
        action=HoldingLedgerEntry.Action.WITHDRAWAL,
    ).exists()


def test_user_can_correct_visible_holding_account(client):
    ruleset = create_ruleset()
    user = create_user()
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=user)
    deposit(
        account=account,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.CURRENCY,
        item_key="copper",
        quantity=Decimal("10"),
    )
    client.force_login(user)

    response = client.post(
        reverse("holdings:adjust", args=[account.id]),
        {
            "action": HoldingLedgerEntry.Action.CORRECTION,
            "ruleset": ruleset.id,
            "item_type": ItemReference.ItemType.CURRENCY,
            "item_key": "copper",
            "quantity": "3",
            "note": "Corrected count",
        },
    )

    assert response.status_code == 302
    balance = HoldingBalance.objects.get(account=account, item_key="copper")
    assert balance.quantity == Decimal("3")
    assert HoldingLedgerEntry.objects.filter(
        account=account,
        action=HoldingLedgerEntry.Action.CORRECTION,
        note="Corrected count",
    ).exists()


def test_user_cannot_adjust_hidden_holding_account(client):
    ruleset = create_ruleset()
    viewer = create_user()
    stranger = create_user("stranger@example.test")
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=stranger)
    client.force_login(viewer)

    response = client.post(
        reverse("holdings:adjust", args=[account.id]),
        {
            "action": HoldingLedgerEntry.Action.DEPOSIT,
            "ruleset": ruleset.id,
            "item_type": ItemReference.ItemType.RESOURCE,
            "item_key": "wood",
            "quantity": "4",
        },
    )

    assert response.status_code == 404
    assert not HoldingBalance.objects.filter(account=account).exists()


def test_read_only_house_member_cannot_adjust_house_holding_account(client):
    ruleset = create_ruleset()
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.HOUSE, house=house)
    HouseMembership.objects.create(user=user, house=house, role=Role.READ_ONLY)
    client.force_login(user)

    response = client.post(
        reverse("holdings:adjust", args=[account.id]),
        {
            "action": HoldingLedgerEntry.Action.DEPOSIT,
            "ruleset": ruleset.id,
            "item_type": ItemReference.ItemType.RESOURCE,
            "item_key": "wood",
            "quantity": "4",
        },
    )

    assert response.status_code == 404
    assert not HoldingBalance.objects.filter(account=account).exists()


def test_holding_adjustment_reports_insufficient_holdings(client):
    ruleset = create_ruleset()
    user = create_user()
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=user)
    client.force_login(user)

    response = client.post(
        reverse("holdings:adjust", args=[account.id]),
        {
            "action": HoldingLedgerEntry.Action.WITHDRAWAL,
            "ruleset": ruleset.id,
            "item_type": ItemReference.ItemType.RESOURCE,
            "item_key": "wood",
            "quantity": "4",
        },
    )

    assert response.status_code == 200
    assert b"Insufficient holdings" in response.content
    assert not HoldingBalance.objects.filter(account=account, item_key="wood").exists()


def test_user_can_transfer_between_visible_holding_accounts(client):
    ruleset = create_ruleset()
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    HouseMembership.objects.create(user=user, house=house)
    source = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=user)
    destination = HoldingAccount.objects.create(scope=HoldingAccount.Scope.HOUSE, house=house)
    deposit(
        account=source,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        quantity=Decimal("8"),
    )
    client.force_login(user)

    response = client.post(
        reverse("holdings:transfer", args=[source.id]),
        {
            "destination": destination.id,
            "ruleset": ruleset.id,
            "item_type": ItemReference.ItemType.RESOURCE,
            "item_key": "wood",
            "quantity": "3",
            "note": "Shared with house",
        },
    )

    assert response.status_code == 302
    assert HoldingBalance.objects.get(account=source, item_key="wood").quantity == Decimal("5")
    assert HoldingBalance.objects.get(account=destination, item_key="wood").quantity == Decimal("3")
    assert HoldingLedgerEntry.objects.filter(
        account=source,
        related_account=destination,
        action=HoldingLedgerEntry.Action.TRANSFER,
        note="Shared with house",
    ).exists()


def test_user_cannot_transfer_to_hidden_holding_account(client):
    ruleset = create_ruleset()
    viewer = create_user()
    stranger = create_user("stranger@example.test")
    source = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=viewer)
    hidden_destination = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.DENIZEN,
        user=stranger,
    )
    deposit(
        account=source,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        quantity=Decimal("8"),
    )
    client.force_login(viewer)

    response = client.post(
        reverse("holdings:transfer", args=[source.id]),
        {
            "destination": hidden_destination.id,
            "ruleset": ruleset.id,
            "item_type": ItemReference.ItemType.RESOURCE,
            "item_key": "wood",
            "quantity": "3",
        },
    )

    assert response.status_code == 200
    assert b"Select a valid choice" in response.content
    assert HoldingBalance.objects.get(account=source, item_key="wood").quantity == Decimal("8")
    assert not HoldingBalance.objects.filter(account=hidden_destination).exists()


def test_user_cannot_transfer_to_read_only_holding_account(client):
    ruleset = create_ruleset()
    user = create_user()
    house = House.objects.create(key="bramble", name="House Bramble")
    source = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=user)
    read_only_destination = HoldingAccount.objects.create(
        scope=HoldingAccount.Scope.HOUSE,
        house=house,
    )
    HouseMembership.objects.create(user=user, house=house, role=Role.READ_ONLY)
    deposit(
        account=source,
        ruleset=ruleset,
        item_type=ItemReference.ItemType.RESOURCE,
        item_key="wood",
        quantity=Decimal("8"),
    )
    client.force_login(user)

    response = client.post(
        reverse("holdings:transfer", args=[source.id]),
        {
            "destination": read_only_destination.id,
            "ruleset": ruleset.id,
            "item_type": ItemReference.ItemType.RESOURCE,
            "item_key": "wood",
            "quantity": "3",
        },
    )

    assert response.status_code == 200
    assert b"Select a valid choice" in response.content
    assert HoldingBalance.objects.get(account=source, item_key="wood").quantity == Decimal("8")
    assert not HoldingBalance.objects.filter(account=read_only_destination).exists()


def test_htmx_adjust_form_request_returns_partial_template(client):
    user = create_user()
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=user)
    client.force_login(user)

    response = client.get(
        reverse("holdings:adjust", args=[account.id]),
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert b"adjust-form" in response.content
    assert b"csrfmiddlewaretoken" in response.content
    assert b"Save adjustment" in response.content


def test_htmx_adjust_form_submission_updates_balances_inline(client):
    ruleset = create_ruleset()
    user = create_user()
    account = HoldingAccount.objects.create(scope=HoldingAccount.Scope.DENIZEN, user=user)
    client.force_login(user)

    response = client.post(
        reverse("holdings:adjust", args=[account.id]),
        {
            "action": HoldingLedgerEntry.Action.DEPOSIT,
            "ruleset": ruleset.id,
            "item_type": ItemReference.ItemType.RESOURCE,
            "item_key": "wood",
            "quantity": "5",
            "note": "HTMX deposit",
        },
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert b"updated" in response.content  # Should contain updated account ID class
    assert b"5.00 resource:wood" in response.content  # Should show the new balance
    balance = HoldingBalance.objects.get(account=account, item_key="wood")
    assert balance.quantity == Decimal("5")
