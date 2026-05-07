from django.db import models

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
