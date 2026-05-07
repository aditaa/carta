from django.contrib import admin

from resources.models import Currency, Resource, ResourceCategory, Unit


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "ruleset")
    list_filter = ("ruleset",)
    search_fields = ("key", "name")


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "copper_value", "ruleset")
    list_filter = ("ruleset",)
    search_fields = ("key", "name")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "category", "ruleset")
    list_filter = ("ruleset", "category")
    search_fields = ("key", "name")


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "category", "attack", "defense", "ruleset")
    list_filter = ("ruleset", "category")
    search_fields = ("key", "name")
