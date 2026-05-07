from django.contrib import admin

from ownership.models import OwnershipRule


@admin.register(OwnershipRule)
class OwnershipRuleAdmin(admin.ModelAdmin):
    list_display = ("entity_type", "ruleset")
    list_filter = ("ruleset",)
    search_fields = ("entity_type",)
