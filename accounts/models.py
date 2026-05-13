from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.managers import UserManager
from ownership.models import House, Kingdom, Role


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


class ApplicationSetting(models.Model):
    key = models.SlugField(max_length=80, unique=True)
    label = models.CharField(max_length=160)
    value = models.TextField(blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["label", "key"]

    def __str__(self) -> str:
        return self.label


class AuditLogEntry(models.Model):
    actor = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_log_entries",
    )
    action = models.CharField(max_length=80)
    target_type = models.CharField(max_length=120)
    target_id = models.CharField(max_length=120, blank=True)
    target_label = models.CharField(max_length=255, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.action} {self.target_label or self.target_type}"


class MembershipInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"

    inviter = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="sent_membership_invitations",
    )
    invitee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_membership_invitations",
    )
    house = models.ForeignKey(
        House,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="membership_invitations",
    )
    kingdom = models.ForeignKey(
        Kingdom,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="membership_invitations",
    )
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def clean(self):
        super().clean()
        if bool(self.house_id) == bool(self.kingdom_id):
            raise ValidationError("Invitation must target exactly one house or kingdom.")

    @property
    def target_label(self) -> str:
        if self.house_id:
            return f"House: {self.house.name}"
        if self.kingdom_id:
            return f"Kingdom: {self.kingdom.name}"
        return "Membership"

    def __str__(self) -> str:
        return f"{self.invitee} -> {self.target_label}"
