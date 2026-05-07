from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from ownership.models import House, Kingdom
from resources.models import Currency, Resource, Unit
from rulesets.models import ItemReference, Ruleset


class HoldingAccount(models.Model):
    class Scope(models.TextChoices):
        DENIZEN = "denizen", "Denizen"
        HOUSE = "house", "House"
        HOUSE_DENIZEN = "house_denizen", "House-held denizen"
        KINGDOM = "kingdom", "Kingdom"
        THREE_CROWNS_DENIZEN = "three_crowns_denizen", "Three Crowns denizen"
        THREE_CROWNS_HOUSE = "three_crowns_house", "Three Crowns house"
        THREE_CROWNS_KINGDOM = "three_crowns_kingdom", "Three Crowns kingdom"

    scope = models.CharField(max_length=40, choices=Scope.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="holding_accounts",
    )
    house = models.ForeignKey(
        House,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="holding_accounts",
    )
    kingdom = models.ForeignKey(
        Kingdom,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="holding_accounts",
    )
    name = models.CharField(max_length=160, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scope", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "user"],
                name="unique_holding_account_scope_user",
            ),
            models.UniqueConstraint(
                fields=["scope", "house"],
                name="unique_holding_account_scope_house",
            ),
            models.UniqueConstraint(
                fields=["scope", "kingdom"],
                name="unique_holding_account_scope_kingdom",
            ),
        ]

    def clean(self):
        super().clean()
        linked_owners = [self.user_id, self.house_id, self.kingdom_id]
        if self.scope == self.Scope.HOUSE_DENIZEN:
            if not self.user_id or not self.house_id or self.kingdom_id:
                raise ValidationError(
                    "House-held denizen accounts must link to one user and one house."
                )
            return
        if sum(owner is not None for owner in linked_owners) != 1:
            raise ValidationError("A holding account must link to exactly one owner.")
        if self.scope in {self.Scope.DENIZEN, self.Scope.THREE_CROWNS_DENIZEN} and not self.user_id:
            raise ValidationError("Denizen holding accounts must link to a user.")
        if self.scope in {self.Scope.HOUSE, self.Scope.THREE_CROWNS_HOUSE} and not self.house_id:
            raise ValidationError("House holding accounts must link to a house.")
        if (
            self.scope in {self.Scope.KINGDOM, self.Scope.THREE_CROWNS_KINGDOM}
            and not self.kingdom_id
        ):
            raise ValidationError("Kingdom holding accounts must link to a kingdom.")

    def __str__(self) -> str:
        if self.name:
            return self.name
        return f"{self.get_scope_display()} account"


class HoldingBalance(models.Model):
    account = models.ForeignKey(HoldingAccount, on_delete=models.CASCADE, related_name="balances")
    ruleset = models.ForeignKey(Ruleset, on_delete=models.PROTECT, related_name="holding_balances")
    item_type = models.CharField(max_length=24, choices=ItemReference.ItemType.choices)
    item_key = models.CharField(max_length=160)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["account", "item_type", "item_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "ruleset", "item_type", "item_key"],
                name="unique_holding_balance_account_ruleset_item",
            )
        ]

    def clean(self):
        super().clean()
        validate_holding_item(self.ruleset, self.item_type, self.item_key)

    def __str__(self) -> str:
        return f"{self.account}: {self.quantity} {self.item_type}:{self.item_key}"


class HoldingLedgerEntry(models.Model):
    class Action(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        WITHDRAWAL = "withdrawal", "Withdrawal"
        TRANSFER = "transfer", "Transfer"
        CORRECTION = "correction", "Correction"

    ruleset = models.ForeignKey(Ruleset, on_delete=models.PROTECT, related_name="holding_ledger")
    account = models.ForeignKey(
        HoldingAccount,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    related_account = models.ForeignKey(
        HoldingAccount,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="related_ledger_entries",
    )
    action = models.CharField(max_length=24, choices=Action.choices)
    item_type = models.CharField(max_length=24, choices=ItemReference.ItemType.choices)
    item_key = models.CharField(max_length=160)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def clean(self):
        super().clean()
        validate_holding_item(self.ruleset, self.item_type, self.item_key)

    def __str__(self) -> str:
        return f"{self.action} {self.quantity} {self.item_type}:{self.item_key}"


def validate_holding_item(ruleset: Ruleset, item_type: str, item_key: str) -> None:
    model_by_type = {
        ItemReference.ItemType.RESOURCE: Resource,
        ItemReference.ItemType.CURRENCY: Currency,
        ItemReference.ItemType.UNIT: Unit,
    }
    item_model = model_by_type.get(item_type)
    if item_model is None:
        raise ValidationError(f"{item_type} is not a supported holding item type.")
    if not item_model.objects.filter(ruleset=ruleset, key=item_key).exists():
        raise ValidationError(f"{item_type}:{item_key} does not exist in {ruleset}.")
