from django import forms
from django.core.exceptions import ValidationError

from buildings.models import BuildingDefinition, OwnedBuilding
from ownership.models import House, Kingdom, KingdomMembership
from ownership.services import visible_house_ids


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
        choices = [(f"user:{self.user.id}", f"{self.user.display_name}")]
        houses = House.objects.filter(id__in=visible_house_ids(self.user)).order_by("name")
        choices.extend((f"house:{house.id}", f"House: {house.name}") for house in houses)
        choices.extend(
            (f"kingdom:{kingdom.id}", f"Kingdom: {kingdom.name}")
            for kingdom in self._visible_kingdoms()
        )
        return choices

    def _visible_kingdoms(self):
        if self.user.is_superuser:
            return Kingdom.objects.order_by("name")
        kingdom_ids = KingdomMembership.objects.filter(
            user=self.user,
            active=True,
        ).values("kingdom_id")
        return Kingdom.objects.filter(id__in=kingdom_ids).order_by("name")

    def _apply_owner(self, building: OwnedBuilding, owner_value: str) -> None:
        owner_type, _, raw_id = owner_value.partition(":")
        if not raw_id:
            raise ValidationError("Choose a valid owner.")

        building.user = None
        building.house = None
        building.kingdom = None
        if owner_type == "user" and int(raw_id) == self.user.id:
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
        if owner_type == "kingdom" and self._visible_kingdoms().filter(id=raw_id).exists():
            building.owner_scope = OwnedBuilding.OwnerScope.KINGDOM
            building.kingdom_id = raw_id
            return

        raise ValidationError("Choose a valid owner.")
