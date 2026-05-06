class Permission:
    HOUSE_VIEW = "house.view"
    HOUSE_MANAGE_BANK = "house.manage_bank"
    HOUSE_MANAGE_DENIZEN_HOLDINGS = "house.manage_denizen_holdings"
    HOUSE_GRANT_PERMISSIONS = "house.grant_permissions"
    KINGDOM_VIEW = "kingdom.view"
    KINGDOM_MANAGE_BANK = "kingdom.manage_bank"
    KINGDOM_GRANT_PERMISSIONS = "kingdom.grant_permissions"
    THREE_CROWNS_MANAGE_HOUSE_ACCOUNT = "three_crowns.manage_house_account"
    THREE_CROWNS_MANAGE_KINGDOM_ACCOUNT = "three_crowns.manage_kingdom_account"


HOUSE_PERMISSIONS = {
    Permission.HOUSE_VIEW,
    Permission.HOUSE_MANAGE_BANK,
    Permission.HOUSE_MANAGE_DENIZEN_HOLDINGS,
    Permission.HOUSE_GRANT_PERMISSIONS,
    Permission.THREE_CROWNS_MANAGE_HOUSE_ACCOUNT,
}

KINGDOM_PERMISSIONS = {
    Permission.KINGDOM_VIEW,
    Permission.KINGDOM_MANAGE_BANK,
    Permission.KINGDOM_GRANT_PERMISSIONS,
    Permission.THREE_CROWNS_MANAGE_KINGDOM_ACCOUNT,
}

SCOPE_HOUSE = "house"
SCOPE_KINGDOM = "kingdom"
