from django.db import models

from rulesets.models import Ruleset


class OwnershipRule(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="ownership_rules")
    entity_type = models.CharField(max_length=120)
    allowed = models.JSONField(default=list, blank=True)
    not_allowed = models.JSONField(default=list, blank=True)
    notes = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["ruleset", "entity_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "entity_type"],
                name="unique_ownership_rule_ruleset_entity_type",
            )
        ]

    def __str__(self) -> str:
        return self.entity_type
