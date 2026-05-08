from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from ownership.models import House, Kingdom
from rulesets.models import Ruleset


class SettlementTier(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="settlement_tiers")
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=160)
    min_buildings = models.PositiveIntegerField()
    max_buildings = models.PositiveIntegerField()
    prerequisites = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["ruleset", "min_buildings", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "key"],
                name="unique_settlement_tier_ruleset_key",
            )
        ]

    def __str__(self) -> str:
        return self.name


class BuildingDefinition(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="buildings")
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=120)
    map_visible = models.BooleanField(default=False)
    settlement_requirement = models.ForeignKey(
        SettlementTier,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="required_by_buildings",
    )
    requirements = models.JSONField(default=list, blank=True)
    effects = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["ruleset", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "key"],
                name="unique_building_definition_ruleset_key",
            )
        ]

    def __str__(self) -> str:
        return self.name


class OwnedBuilding(models.Model):
    class OwnerScope(models.TextChoices):
        DENIZEN = "denizen", "Denizen"
        HOUSE = "house", "House"
        KINGDOM = "kingdom", "Kingdom"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        DAMAGED = "damaged", "Damaged"

    ruleset = models.ForeignKey(Ruleset, on_delete=models.PROTECT, related_name="owned_buildings")
    definition = models.ForeignKey(
        BuildingDefinition,
        on_delete=models.PROTECT,
        related_name="owned_buildings",
    )
    owner_scope = models.CharField(max_length=24, choices=OwnerScope.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="owned_buildings",
    )
    house = models.ForeignKey(
        House,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="owned_buildings",
    )
    kingdom = models.ForeignKey(
        Kingdom,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="owned_buildings",
    )
    nickname = models.CharField(max_length=160, blank=True)
    location = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["definition__name", "nickname", "id"]
        indexes = [
            models.Index(fields=["owner_scope", "status"]),
            models.Index(fields=["ruleset", "definition"]),
        ]

    def clean(self):
        super().clean()
        if self.definition_id and self.ruleset_id and self.definition.ruleset_id != self.ruleset_id:
            raise ValidationError(
                "Owned building ruleset must match the building definition ruleset."
            )

        linked_owners = [self.user_id, self.house_id, self.kingdom_id]
        if sum(owner is not None for owner in linked_owners) != 1:
            raise ValidationError("An owned building must link to exactly one owner.")
        if self.owner_scope == self.OwnerScope.DENIZEN and not self.user_id:
            raise ValidationError("Denizen-owned buildings must link to a user.")
        if self.owner_scope == self.OwnerScope.HOUSE and not self.house_id:
            raise ValidationError("House-owned buildings must link to a house.")
        if self.owner_scope == self.OwnerScope.KINGDOM and not self.kingdom_id:
            raise ValidationError("Kingdom-owned buildings must link to a kingdom.")

    def __str__(self) -> str:
        return self.nickname or self.definition.name


class BuildingLedgerEntry(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        DELETED = "deleted", "Deleted"

    building = models.ForeignKey(
        OwnedBuilding,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="ledger_entries",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="building_ledger_entries",
    )
    action = models.CharField(max_length=24, choices=Action.choices)
    building_label = models.CharField(max_length=200)
    changes = models.JSONField(default=dict, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.action} {self.building_label}"
