from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from accounts.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=160)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.display_name or self.email


class DenizenProfile(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        RETIRED = "retired", "Retired"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="denizen_profile")
    character_name = models.CharField(max_length=160, blank=True)
    pronouns = models.CharField(max_length=80, blank=True)
    contact = models.CharField(max_length=255, blank=True)
    profile_note = models.TextField(blank=True)
    system_account = models.BooleanField(default=False)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    religion = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__email"]

    def __str__(self) -> str:
        return self.character_name or str(self.user)
