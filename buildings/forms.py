from django import forms
from django.core.exceptions import ValidationError

from buildings.models import BuildingDefinition, OwnedBuilding
from buildings.services import building_owner_choices
from ownership.models import House
from ownership.services import visible_house_ids, visible_kingdom_ids


class OwnedBuildingForm(forms.ModelForm):
    owner = forms.ChoiceField()

    class Meta:
        model = OwnedBuilding
        fields = ("definition", "owner", "nickname", "location", "status", "notes")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["definition"].queryset = BuildingDefinition.objects.select_related(
            "ruleset"
        ).order_by("name")
        self.fields["owner"].choices = self._owner_choices()
        if self.instance.pk:
            self.fields["owner"].initial = self._initial_owner()

    def clean(self):
        cleaned_data = super().clean()
        definition = cleaned_data.get("definition")
        owner = cleaned_data.get("owner")
        if definition is not None:
            self.instance.ruleset = definition.ruleset
        if owner:
            self._apply_owner(self.instance, owner)
        return cleaned_data

    def save(self, commit=True):
        building = super().save(commit=False)
        if commit:
            building.full_clean()
            building.save()
            self.save_m2m()
        return building

    def _owner_choices(self):
        return building_owner_choices(self.user)

    def _initial_owner(self):
        if self.instance.user_id:
            return f"user:{self.instance.user_id}"
        if self.instance.house_id:
            return f"house:{self.instance.house_id}"
        if self.instance.kingdom_id:
            return f"kingdom:{self.instance.kingdom_id}"
        return ""

    def _apply_owner(self, building: OwnedBuilding, owner_value: str) -> None:
        owner_type, _, raw_id = owner_value.partition(":")
        if not raw_id or not raw_id.isdigit():
            raise ValidationError("Choose a valid owner.")

        owner_id = int(raw_id)
        building.user = None
        building.house = None
        building.kingdom = None
        if owner_type == "user" and owner_id == self.user.id:
            building.owner_scope = OwnedBuilding.OwnerScope.DENIZEN
            building.user = self.user
            return
        if (
            owner_type == "house"
            and House.objects.filter(
                id__in=visible_house_ids(self.user),
                id=raw_id,
            ).exists()
        ):
            building.owner_scope = OwnedBuilding.OwnerScope.HOUSE
            building.house_id = raw_id
            return
        if owner_type == "kingdom" and owner_id in visible_kingdom_ids(self.user):
            building.owner_scope = OwnedBuilding.OwnerScope.KINGDOM
            building.kingdom_id = raw_id
            return

        raise ValidationError("Choose a valid owner.")
