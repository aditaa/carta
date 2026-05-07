from django.contrib import admin

from production.models import ProductionRecipe


@admin.register(ProductionRecipe)
class ProductionRecipeAdmin(admin.ModelAdmin):
    list_display = ("key", "building", "recipe_type", "ruleset")
    list_filter = ("ruleset", "recipe_type", "building")
    search_fields = ("key", "building__key", "building__name")
