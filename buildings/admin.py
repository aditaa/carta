from django.contrib import admin

from buildings.models import BuildingDefinition, SettlementTier


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
