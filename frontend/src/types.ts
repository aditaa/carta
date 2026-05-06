export type RulesRef = {
  item_type: "currency" | "resource" | "unit" | "special";
  item_key: string;
  amount: number;
};

export type RulesDataset = {
  game: string;
  rules_version: string;
  schema_version: string;
  currencies: Array<{ key: string; name: string; copper_value?: number | null }>;
  resources: Array<{ key: string; name: string; category: string }>;
  units: Array<{ key: string; name: string; category: string }>;
  settlement_tiers: Array<{ key: string; name: string }>;
  building_definitions: Array<{
    key: string;
    name: string;
    category: string;
    upkeep: RulesRef[];
  }>;
  production_recipes: Array<{ key: string; building_key: string; recipe_type: string }>;
  transports: Array<{ key: string; name: string; transport_type: string }>;
};

export type BuildingRegistryItem = {
  id: number;
  owner_denizen_id: number;
  building_definition_id: string;
  count: number;
  house_id?: number | null;
  display_name?: string | null;
};

export type BuildingRegistrySummary = {
  items: BuildingRegistryItem[];
  note?: string | null;
};

export type BuildingUpkeepLine = {
  building_registry_id: number;
  building_definition_id: string;
  count: number;
  upkeep: RulesRef[];
};

export type BuildingUpkeepSummary = {
  lines: BuildingUpkeepLine[];
  totals: RulesRef[];
};

export type AuthDenizen = {
  id: number;
  email: string;
  display_name: string;
  role: string;
  religion?: string | null;
  primary_house_id?: number | null;
  primary_kingdom_id?: number | null;
  is_active: boolean;
};

export type AuthToken = {
  access_token: string;
  token_type: "bearer";
  denizen: AuthDenizen;
};
