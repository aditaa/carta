from dataclasses import dataclass


class PlatformPermission:
    VIEW_USER = "accounts.view_user"
    CHANGE_USER = "accounts.change_user"
    VIEW_DENIZEN_PROFILE = "accounts.view_denizenprofile"
    CHANGE_DENIZEN_PROFILE = "accounts.change_denizenprofile"
    VIEW_HOUSE = "ownership.view_house"
    VIEW_HOUSE_MEMBERSHIP = "ownership.view_housemembership"
    VIEW_KINGDOM = "ownership.view_kingdom"
    VIEW_KINGDOM_MEMBERSHIP = "ownership.view_kingdommembership"


class RolePresetKey:
    PLAYER = "player"
    HOUSE_MANAGER = "house_manager"
    KINGDOM_ADMIN = "kingdom_admin"
    APP_STAFF = "app_staff"


@dataclass(frozen=True)
class RolePreset:
    key: str
    name: str
    permissions: tuple[str, ...]


ROLE_PRESETS: dict[str, RolePreset] = {
    RolePresetKey.PLAYER: RolePreset(
        key=RolePresetKey.PLAYER,
        name="Player",
        permissions=(),
    ),
    RolePresetKey.HOUSE_MANAGER: RolePreset(
        key=RolePresetKey.HOUSE_MANAGER,
        name="House Manager",
        permissions=(
            PlatformPermission.VIEW_USER,
            PlatformPermission.VIEW_DENIZEN_PROFILE,
            PlatformPermission.VIEW_HOUSE,
            PlatformPermission.VIEW_HOUSE_MEMBERSHIP,
        ),
    ),
    RolePresetKey.KINGDOM_ADMIN: RolePreset(
        key=RolePresetKey.KINGDOM_ADMIN,
        name="Kingdom Admin",
        permissions=(
            PlatformPermission.VIEW_USER,
            PlatformPermission.VIEW_DENIZEN_PROFILE,
            PlatformPermission.VIEW_HOUSE,
            PlatformPermission.VIEW_HOUSE_MEMBERSHIP,
            PlatformPermission.VIEW_KINGDOM,
            PlatformPermission.VIEW_KINGDOM_MEMBERSHIP,
        ),
    ),
    RolePresetKey.APP_STAFF: RolePreset(
        key=RolePresetKey.APP_STAFF,
        name="App Staff",
        permissions=(
            PlatformPermission.VIEW_USER,
            PlatformPermission.CHANGE_USER,
            PlatformPermission.VIEW_DENIZEN_PROFILE,
            PlatformPermission.CHANGE_DENIZEN_PROFILE,
        ),
    ),
}


class AuditAction:
    APPLICATION_SETTINGS_UPDATED = "application_settings_updated"
    GIT_CHECKOUT_RESET = "git_checkout_reset"
    GIT_FILE_RESTORED = "git_file_restored"
    HOUSE_MEMBERSHIP_REMOVED = "house_membership_removed"
    HOUSE_UPDATED = "house_updated"
    KINGDOM_MEMBERSHIP_REMOVED = "kingdom_membership_removed"
    KINGDOM_UPDATED = "kingdom_updated"
    MEMBERSHIP_INVITATION_ACCEPTED = "membership_invitation_accepted"
    MEMBERSHIP_INVITATION_CANCELLED = "membership_invitation_cancelled"
    MEMBERSHIP_INVITATION_CREATED = "membership_invitation_created"
    MEMBERSHIP_INVITATION_DECLINED = "membership_invitation_declined"
    OWN_PASSWORD_CHANGED = "own_password_changed"
    TEST_EMAIL_SENT = "test_email_sent"
    UPGRADE_REUSED_RUNNING_JOB = "upgrade_reused_running_job"
    UPGRADE_STARTED = "upgrade_started"
    USER_ACCESS_UPDATED = "user_access_updated"
    USER_CREATED = "user_created"
    USER_DISABLED = "user_disabled"
    USER_ENABLED = "user_enabled"
    USER_PASSWORD_CHANGED = "user_password_changed"
