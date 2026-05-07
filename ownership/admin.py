from django.contrib import admin

from ownership.models import House, HouseMembership, Kingdom, KingdomMembership, OwnershipRule


class HouseMembershipInline(admin.TabularInline):
    model = HouseMembership
    extra = 0
    autocomplete_fields = ("user",)


class KingdomMembershipInline(admin.TabularInline):
    model = KingdomMembership
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(Kingdom)
class KingdomAdmin(admin.ModelAdmin):
    list_display = ("key", "name")
    search_fields = ("key", "name")
    inlines = (KingdomMembershipInline,)


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "kingdom")
    list_filter = ("kingdom",)
    search_fields = ("key", "name")
    inlines = (HouseMembershipInline,)


@admin.register(HouseMembership)
class HouseMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "house", "role", "active")
    list_filter = ("role", "active", "house")
    search_fields = ("user__email", "user__display_name", "house__key", "house__name")
    autocomplete_fields = ("user", "house")


@admin.register(KingdomMembership)
class KingdomMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "kingdom", "role", "active")
    list_filter = ("role", "active", "kingdom")
    search_fields = ("user__email", "user__display_name", "kingdom__key", "kingdom__name")
    autocomplete_fields = ("user", "kingdom")


@admin.register(OwnershipRule)
class OwnershipRuleAdmin(admin.ModelAdmin):
    list_display = ("entity_type", "ruleset")
    list_filter = ("ruleset",)
    search_fields = ("entity_type",)
