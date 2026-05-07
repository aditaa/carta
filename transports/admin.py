from django.contrib import admin

from transports.models import TransportDefinition


@admin.register(TransportDefinition)
class TransportDefinitionAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "transport_type", "health", "storage", "quarters", "ruleset")
    list_filter = ("ruleset", "transport_type")
    search_fields = ("key", "name")
