from django.contrib import admin

from buildings.models import BuildingDefinition, OwnedBuilding, SettlementTier


@admin.register(SettlementTier)
class SettlementTierAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "min_buildings", "max_buildings", "ruleset")
    list_filter = ("ruleset",)
    search_fields = ("key", "name")


@admin.register(BuildingDefinition)
class BuildingDefinitionAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "category", "map_visible", "settlement_requirement", "ruleset")
    list_filter = ("ruleset", "category", "map_visible", "settlement_requirement")
    search_fields = ("key", "name")


@admin.register(OwnedBuilding)
class OwnedBuildingAdmin(admin.ModelAdmin):
    list_display = ("definition", "nickname", "owner_scope", "status", "ruleset")
    list_filter = ("ruleset", "owner_scope", "status", "definition__category")
    search_fields = (
        "nickname",
        "location",
        "definition__key",
        "definition__name",
        "user__email",
        "user__display_name",
        "house__name",
        "kingdom__name",
    )
    autocomplete_fields = ("definition", "user", "house", "kingdom")
