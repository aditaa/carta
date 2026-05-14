from django.contrib import admin

from progression.models import PhaseDefinition, PhaseUnlock, TitleDefinition


@admin.register(TitleDefinition)
class TitleDefinitionAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "category", "ruleset")
    list_filter = ("ruleset", "category")
    search_fields = ("key", "name", "category")


class PhaseUnlockInline(admin.TabularInline):
    model = PhaseUnlock
    extra = 0
    fields = ("key", "name", "unlock_type", "sort_order")


@admin.register(PhaseDefinition)
class PhaseDefinitionAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "sort_order", "ruleset")
    list_filter = ("ruleset",)
    search_fields = ("key", "name", "description")
    inlines = [PhaseUnlockInline]


@admin.register(PhaseUnlock)
class PhaseUnlockAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "unlock_type", "phase")
    list_filter = ("phase__ruleset", "unlock_type")
    search_fields = ("key", "name", "unlock_type", "description")
