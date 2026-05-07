from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from holdings.models import (
    HoldingAccount,
    HoldingBalance,
    HoldingLedgerEntry,
    validate_holding_item,
)
from ownership.services import can_view_house, can_view_kingdom, can_view_user
from rulesets.models import Ruleset


@transaction.atomic
def deposit(
    *,
    account: HoldingAccount,
    ruleset: Ruleset,
    item_type: str,
    item_key: str,
    quantity: Decimal,
    note: str = "",
) -> HoldingBalance:
    quantity = _positive_quantity(quantity)
    balance = _change_balance(
        account=account,
        ruleset=ruleset,
        item_type=item_type,
        item_key=item_key,
        delta=quantity,
    )
    _log_entry(
        account=account,
        ruleset=ruleset,
        action=HoldingLedgerEntry.Action.DEPOSIT,
        item_type=item_type,
        item_key=item_key,
        quantity=quantity,
        note=note,
    )
    return balance


@transaction.atomic
def withdraw(
    *,
    account: HoldingAccount,
    ruleset: Ruleset,
    item_type: str,
    item_key: str,
    quantity: Decimal,
    note: str = "",
) -> HoldingBalance:
    quantity = _positive_quantity(quantity)
    balance = get_balance(
        account=account,
        ruleset=ruleset,
        item_type=item_type,
        item_key=item_key,
    )
    if balance.quantity < quantity:
        raise ValidationError("Insufficient holdings.")
    balance = _change_balance(
        account=account,
        ruleset=ruleset,
        item_type=item_type,
        item_key=item_key,
        delta=-quantity,
    )
    _log_entry(
        account=account,
        ruleset=ruleset,
        action=HoldingLedgerEntry.Action.WITHDRAWAL,
        item_type=item_type,
        item_key=item_key,
        quantity=quantity,
        note=note,
    )
    return balance


@transaction.atomic
def transfer(
    *,
    source: HoldingAccount,
    destination: HoldingAccount,
    ruleset: Ruleset,
    item_type: str,
    item_key: str,
    quantity: Decimal,
    note: str = "",
) -> tuple[HoldingBalance, HoldingBalance]:
    quantity = _positive_quantity(quantity)
    source_balance = withdraw(
        account=source,
        ruleset=ruleset,
        item_type=item_type,
        item_key=item_key,
        quantity=quantity,
        note=note,
    )
    destination_balance = deposit(
        account=destination,
        ruleset=ruleset,
        item_type=item_type,
        item_key=item_key,
        quantity=quantity,
        note=note,
    )
    HoldingLedgerEntry.objects.create(
        account=source,
        related_account=destination,
        ruleset=ruleset,
        action=HoldingLedgerEntry.Action.TRANSFER,
        item_type=item_type,
        item_key=item_key,
        quantity=quantity,
        note=note,
    )
    return source_balance, destination_balance


@transaction.atomic
def correct(
    *,
    account: HoldingAccount,
    ruleset: Ruleset,
    item_type: str,
    item_key: str,
    quantity: Decimal,
    note: str = "",
) -> HoldingBalance:
    if quantity < 0:
        raise ValidationError("Holding quantity cannot be negative.")
    validate_holding_item(ruleset, item_type, item_key)
    balance, _created = HoldingBalance.objects.select_for_update().get_or_create(
        account=account,
        ruleset=ruleset,
        item_type=item_type,
        item_key=item_key,
        defaults={"quantity": quantity},
    )
    balance.quantity = quantity
    balance.full_clean()
    balance.save()
    _log_entry(
        account=account,
        ruleset=ruleset,
        action=HoldingLedgerEntry.Action.CORRECTION,
        item_type=item_type,
        item_key=item_key,
        quantity=quantity,
        note=note,
    )
    return balance


def get_balance(
    *,
    account: HoldingAccount,
    ruleset: Ruleset,
    item_type: str,
    item_key: str,
) -> HoldingBalance:
    validate_holding_item(ruleset, item_type, item_key)
    balance, _created = HoldingBalance.objects.get_or_create(
        account=account,
        ruleset=ruleset,
        item_type=item_type,
        item_key=item_key,
        defaults={"quantity": Decimal("0")},
    )
    return balance


def visible_holding_accounts(viewer):
    accounts = HoldingAccount.objects.filter(active=True).select_related("user", "house", "kingdom")
    if not viewer.is_authenticated or not viewer.is_active:
        return HoldingAccount.objects.none()
    if viewer.is_superuser:
        return accounts

    visible_ids = [
        account.id for account in accounts if _can_view_account(viewer=viewer, account=account)
    ]
    return accounts.filter(id__in=visible_ids)


def _can_view_account(*, viewer, account: HoldingAccount) -> bool:
    if account.user_id is not None:
        return can_view_user(viewer, account.user)
    if account.house_id is not None:
        return can_view_house(viewer, account.house)
    if account.kingdom_id is not None:
        return can_view_kingdom(viewer, account.kingdom)
    return False


def _change_balance(
    *,
    account: HoldingAccount,
    ruleset: Ruleset,
    item_type: str,
    item_key: str,
    delta: Decimal,
) -> HoldingBalance:
    validate_holding_item(ruleset, item_type, item_key)
    balance, _created = HoldingBalance.objects.select_for_update().get_or_create(
        account=account,
        ruleset=ruleset,
        item_type=item_type,
        item_key=item_key,
        defaults={"quantity": Decimal("0")},
    )
    balance.quantity += delta
    if balance.quantity < 0:
        raise ValidationError("Holding quantity cannot be negative.")
    balance.full_clean()
    balance.save()
    return balance


def _log_entry(
    *,
    account: HoldingAccount,
    ruleset: Ruleset,
    action: HoldingLedgerEntry.Action,
    item_type: str,
    item_key: str,
    quantity: Decimal,
    note: str,
) -> HoldingLedgerEntry:
    entry = HoldingLedgerEntry(
        account=account,
        ruleset=ruleset,
        action=action,
        item_type=item_type,
        item_key=item_key,
        quantity=quantity,
        note=note,
    )
    entry.full_clean()
    entry.save()
    return entry


def _positive_quantity(quantity: Decimal) -> Decimal:
    if quantity <= 0:
        raise ValidationError("Holding quantity must be greater than zero.")
    return quantity
