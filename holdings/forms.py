from django import forms
from django.core.exceptions import ValidationError

from holdings.models import HoldingAccount, HoldingLedgerEntry, validate_holding_item
from holdings.services import correct, deposit, withdraw
from rulesets.models import ItemReference, Ruleset


class HoldingAdjustmentForm(forms.Form):
    action = forms.ChoiceField(
        choices=[
            (HoldingLedgerEntry.Action.DEPOSIT, "Deposit"),
            (HoldingLedgerEntry.Action.WITHDRAWAL, "Withdrawal"),
            (HoldingLedgerEntry.Action.CORRECTION, "Correction"),
        ]
    )
    ruleset = forms.ModelChoiceField(queryset=Ruleset.objects.order_by("game", "rules_version"))
    item_type = forms.ChoiceField(
        choices=[
            (ItemReference.ItemType.RESOURCE, "Resource"),
            (ItemReference.ItemType.CURRENCY, "Currency"),
            (ItemReference.ItemType.UNIT, "Unit"),
        ]
    )
    item_key = forms.CharField(max_length=160)
    quantity = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2)
    note = forms.CharField(required=False, widget=forms.Textarea)

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        ruleset = cleaned_data.get("ruleset")
        item_type = cleaned_data.get("item_type")
        item_key = cleaned_data.get("item_key")
        quantity = cleaned_data.get("quantity")

        if (
            action
            in {
                HoldingLedgerEntry.Action.DEPOSIT,
                HoldingLedgerEntry.Action.WITHDRAWAL,
            }
            and quantity == 0
        ):
            self.add_error("quantity", "Quantity must be greater than zero.")

        if ruleset and item_type and item_key:
            try:
                validate_holding_item(ruleset, item_type, item_key)
            except ValidationError as error:
                self.add_error("item_key", error)
        return cleaned_data

    def save(self, account: HoldingAccount):
        action = self.cleaned_data["action"]
        data = {
            "account": account,
            "ruleset": self.cleaned_data["ruleset"],
            "item_type": self.cleaned_data["item_type"],
            "item_key": self.cleaned_data["item_key"],
            "quantity": self.cleaned_data["quantity"],
            "note": self.cleaned_data["note"],
        }
        if action == HoldingLedgerEntry.Action.DEPOSIT:
            return deposit(**data)
        if action == HoldingLedgerEntry.Action.WITHDRAWAL:
            return withdraw(**data)
        return correct(**data)
