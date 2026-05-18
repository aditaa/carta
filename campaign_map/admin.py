from django.contrib import admin

from campaign_map.models import CampaignMapVersion


@admin.register(CampaignMapVersion)
class CampaignMapVersionAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "version", "map_type", "parent_key", "is_active", "imported_at")
    list_filter = ("map_type", "key", "is_active")
    search_fields = ("key", "name", "version", "source_path", "notes")
    readonly_fields = ("imported_at", "created_at")
