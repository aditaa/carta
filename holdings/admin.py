from django.contrib import admin

from holdings.models import HoldingAccount, HoldingBalance, HoldingLedgerEntry


class HoldingBalanceInline(admin.TabularInline):
    model = HoldingBalance
    extra = 0


@admin.register(HoldingAccount)
class HoldingAccountAdmin(admin.ModelAdmin):
    list_display = ("scope", "name", "user", "house", "kingdom", "active")
    list_filter = ("scope", "active")
    search_fields = ("name", "user__email", "user__display_name", "house__name", "kingdom__name")
    inlines = (HoldingBalanceInline,)


@admin.register(HoldingBalance)
class HoldingBalanceAdmin(admin.ModelAdmin):
    list_display = ("account", "ruleset", "item_type", "item_key", "quantity")
    list_filter = ("ruleset", "item_type")
    search_fields = ("account__name", "item_key")


@admin.register(HoldingLedgerEntry)
class HoldingLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "account", "item_type", "item_key", "quantity")
    list_filter = ("ruleset", "action", "item_type")
    search_fields = ("account__name", "item_key", "note")
