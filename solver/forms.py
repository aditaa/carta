from decimal import Decimal

from django import forms

from rulesets.models import ItemReference, Ruleset
from solver.services import SolverTarget


class SolverTargetForm(forms.Form):
    target = forms.ChoiceField(label="Desired output")
    quantity = forms.DecimalField(
        min_value=Decimal("0.01"),
        decimal_places=2,
        max_digits=12,
        initial=Decimal("1"),
    )

    def __init__(self, ruleset: Ruleset | None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ruleset = ruleset
        self.fields["target"].choices = _target_choices(ruleset)

    def solver_target(self) -> SolverTarget:
        item_type, item_key = self.cleaned_data["target"].split(":", 1)
        return SolverTarget(
            item_type=item_type,
            item_key=item_key,
            quantity=self.cleaned_data["quantity"],
        )


def _target_choices(ruleset: Ruleset | None) -> list[tuple[str, str]]:
    if ruleset is None:
        return []
    refs = (
        ItemReference.objects.filter(
            ruleset=ruleset,
            owner_type="production_recipe",
            purpose=ItemReference.Purpose.RECIPE_OUTPUT,
        )
        .values_list("item_type", "item_key")
        .distinct()
        .order_by("item_type", "item_key")
    )
    return [(f"{item_type}:{item_key}", f"{item_type}:{item_key}") for item_type, item_key in refs]
