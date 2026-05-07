from django.conf import settings
from django.db import models

from rulesets.models import Ruleset


class Role(models.TextChoices):
    READ_ONLY = "read_only", "Read only"
    MEMBER = "member", "Member"
    MANAGER = "manager", "Manager"
    ADMIN = "admin", "Admin"


class Kingdom(models.Model):
    key = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "key"]

    def __str__(self) -> str:
        return self.name


class House(models.Model):
    key = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=160)
    kingdom = models.ForeignKey(
        Kingdom,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="houses",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "key"]

    def __str__(self) -> str:
        return self.name


class HouseMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="house_memberships",
    )
    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.MEMBER)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["house__name", "user__email"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "house"],
                name="unique_house_membership_user_house",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.house}"


class KingdomMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kingdom_memberships",
    )
    kingdom = models.ForeignKey(Kingdom, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.MEMBER)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kingdom__name", "user__email"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "kingdom"],
                name="unique_kingdom_membership_user_kingdom",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.kingdom}"


class OwnershipRule(models.Model):
    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="ownership_rules")
    entity_type = models.CharField(max_length=120)
    allowed = models.JSONField(default=list, blank=True)
    not_allowed = models.JSONField(default=list, blank=True)
    notes = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["ruleset", "entity_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["ruleset", "entity_type"],
                name="unique_ownership_rule_ruleset_entity_type",
            )
        ]

    def __str__(self) -> str:
        return self.entity_type
