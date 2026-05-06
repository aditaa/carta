import type { BuildingRegistrySummary, BuildingUpkeepSummary, RulesDataset } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function getCurrentRules(): Promise<RulesDataset> {
  return fetchJson<RulesDataset>("/rules/current");
}

export function getBuildingRegistry(): Promise<BuildingRegistrySummary> {
  return fetchJson<BuildingRegistrySummary>("/buildings");
}

export function getUpkeepPreview(): Promise<BuildingUpkeepSummary> {
  return fetchJson<BuildingUpkeepSummary>("/buildings/upkeep-preview");
}
