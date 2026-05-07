from django.db import models

from rulesets.models import Ruleset


class ResourceCategory(models.Model):
    ruleset = models.ForeignKey(
        Ruleset, on_delete=models.CASCADE, related_name="resource_categories"
    )
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=160)

    class Meta:
        ordering = ["ruleset", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "key"],
                name="unique_resource_category_ruleset_key",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Currency(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="currencies")
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=160)
    copper_value = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ["ruleset", "copper_value", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "key"],
                name="unique_currency_ruleset_key",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Resource(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="resources")
    category = models.ForeignKey(
        ResourceCategory,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="resources",
    )
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=160)

    class Meta:
        ordering = ["ruleset", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "key"],
                name="unique_resource_ruleset_key",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Unit(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="units")
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=120)
    attack = models.IntegerField(blank=True, null=True)
    defense = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ["ruleset", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "key"],
                name="unique_unit_ruleset_key",
            )
        ]

    def __str__(self) -> str:
        return self.name
