from django.contrib import admin

from rulesets.models import ItemReference, Ruleset, RulesetImportLog


@admin.register(Ruleset)
class RulesetAdmin(admin.ModelAdmin):
    list_display = ("game", "rules_version", "schema_version", "imported_at")
    search_fields = ("game", "rules_version", "schema_version")
    readonly_fields = ("created_at", "imported_at")


@admin.register(RulesetImportLog)
class RulesetImportLogAdmin(admin.ModelAdmin):
    list_display = ("source_path", "status", "ruleset", "created_at")
    list_filter = ("status",)
    search_fields = ("source_path", "message")
    readonly_fields = ("created_at",)


@admin.register(ItemReference)
class ItemReferenceAdmin(admin.ModelAdmin):
    list_display = (
        "purpose",
        "owner_type",
        "owner_key",
        "item_type",
        "item_key",
        "amount",
        "ruleset",
    )
    list_filter = ("ruleset", "purpose", "owner_type", "item_type")
    search_fields = ("owner_key", "item_key")
