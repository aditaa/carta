from django.db import models

from rulesets.models import Ruleset


class TransportDefinition(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="transports")
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=160)
    transport_type = models.CharField(max_length=120)
    home_requirement = models.TextField(blank=True)
    health = models.PositiveIntegerField()
    storage = models.PositiveIntegerField()
    quarters = models.PositiveIntegerField()
    actions = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["ruleset", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "key"],
                name="unique_transport_definition_ruleset_key",
            )
        ]

    def __str__(self) -> str:
        return self.name
