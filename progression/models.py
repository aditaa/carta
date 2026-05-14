from django.db import models

from rulesets.models import Ruleset


class TitleDefinition(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="titles")
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=120, blank=True)
    requirements = models.JSONField(default=list, blank=True)
    effects = models.JSONField(default=list, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["ruleset", "category", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "key"],
                name="unique_title_definition_ruleset_key",
            )
        ]

    def __str__(self) -> str:
        return self.name


class PhaseDefinition(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="phases")
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    requirements = models.JSONField(default=list, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["ruleset", "sort_order", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "key"],
                name="unique_phase_definition_ruleset_key",
            )
        ]

    def __str__(self) -> str:
        return self.name


class PhaseUnlock(models.Model):
    phase = models.ForeignKey(
        PhaseDefinition,
        on_delete=models.CASCADE,
        related_name="unlocks",
    )
    key = models.CharField(max_length=120)
    name = models.CharField(max_length=160)
    unlock_type = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["phase", "sort_order", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["phase", "key"],
                name="unique_phase_unlock_phase_key",
            )
        ]

    def __str__(self) -> str:
        return self.name
