from django.db import models

from buildings.models import BuildingDefinition
from rulesets.models import Ruleset


class ProductionRecipe(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="recipes")
    key = models.CharField(max_length=160)
    building = models.ForeignKey(
        BuildingDefinition,
        on_delete=models.CASCADE,
        related_name="production_recipes",
    )
    recipe_type = models.CharField(max_length=120)

    class Meta:
        ordering = ["ruleset", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "key"],
                name="unique_production_recipe_ruleset_key",
            )
        ]

    def __str__(self) -> str:
        return self.key
