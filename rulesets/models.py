from django.db import models


class Ruleset(models.Model):
    game = models.CharField(max_length=160)
    rules_version = models.CharField(max_length=80)
    schema_version = models.CharField(max_length=80)
    source_path = models.CharField(max_length=500)
    metadata = models.JSONField(default=dict, blank=True)
    raw_data = models.JSONField(default=dict)
    imported_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["game", "rules_version"]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "rules_version"],
                name="unique_ruleset_game_version",
            )
        ]

    def __str__(self) -> str:
        return f"{self.game} {self.rules_version}"


class RulesetImportLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    ruleset = models.ForeignKey(
        Ruleset,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="import_logs",
    )
    source_path = models.CharField(max_length=500)
    status = models.CharField(max_length=24, choices=Status.choices)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.status}: {self.source_path}"
