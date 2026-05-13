from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.forms import UserChangeForm, UserCreationForm
from accounts.models import (
    ApplicationSetting,
    AuditLogEntry,
    DenizenProfile,
    MembershipInvitation,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    list_display = ("email", "display_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    ordering = ("email",)
    search_fields = ("email", "display_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identity", {"fields": ("display_name",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2"),
            },
        ),
    )


@admin.register(DenizenProfile)
class DenizenProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "character_name", "system_account", "status")
    list_filter = ("system_account", "status", "religion")
    search_fields = ("user__email", "user__display_name", "character_name")


@admin.register(ApplicationSetting)
class ApplicationSettingAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "updated_at")
    search_fields = ("key", "label", "value")
    readonly_fields = ("key",)


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_type", "target_label")
    list_filter = ("action", "target_type")
    search_fields = ("actor__email", "actor__display_name", "target_label", "action")
    readonly_fields = ("actor", "action", "target_type", "target_id", "target_label", "detail")


@admin.register(MembershipInvitation)
class MembershipInvitationAdmin(admin.ModelAdmin):
    list_display = ("invitee", "target_label", "role", "status", "inviter", "created_at")
    list_filter = ("status", "role", "house", "kingdom")
    search_fields = (
        "invitee__email",
        "invitee__display_name",
        "inviter__email",
        "house__name",
        "kingdom__name",
    )
    autocomplete_fields = ("invitee", "inviter", "house", "kingdom")
