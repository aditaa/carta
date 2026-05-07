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


class ItemReference(models.Model):
    class ItemType(models.TextChoices):
        RESOURCE = "resource", "Resource"
        CURRENCY = "currency", "Currency"
        UNIT = "unit", "Unit"
        SPECIAL = "special", "Special"

    class Purpose(models.TextChoices):
        SETTLEMENT_UPGRADE_COST = "settlement_upgrade_cost", "Settlement upgrade cost"
        SETTLEMENT_UPKEEP = "settlement_upkeep", "Settlement upkeep"
        BUILD_COST = "build_cost", "Build cost"
        BUILDING_UPKEEP = "building_upkeep", "Building upkeep"
        RECIPE_INPUT = "recipe_input", "Recipe input"
        RECIPE_OUTPUT = "recipe_output", "Recipe output"
        TRANSPORT_BUILD_COST = "transport_build_cost", "Transport build cost"
        TRANSPORT_REPAIR_COST = "transport_repair_cost", "Transport repair cost"
        TRANSPORT_UPKEEP = "transport_upkeep", "Transport upkeep"

    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="item_refs")
    purpose = models.CharField(max_length=80, choices=Purpose.choices)
    owner_type = models.CharField(max_length=80)
    owner_key = models.CharField(max_length=160)
    item_type = models.CharField(max_length=24, choices=ItemType.choices)
    item_key = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ruleset", "owner_type", "owner_key", "purpose", "sort_order", "id"]
        indexes = [
            models.Index(fields=["ruleset", "owner_type", "owner_key", "purpose"]),
            models.Index(fields=["ruleset", "item_type", "item_key"]),
        ]

    def __str__(self) -> str:
        return f"{self.amount} {self.item_type}:{self.item_key}"
