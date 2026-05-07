from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.forms import UserChangeForm, UserCreationForm
from accounts.models import DenizenProfile, User


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
