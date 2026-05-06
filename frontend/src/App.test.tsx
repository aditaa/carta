import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const rulesPayload = {
  game: "Carta Arcanum",
  rules_version: "2.1.4",
  schema_version: "1.0.0",
  currencies: [{ key: "tower", name: "Tower", copper_value: 3 }],
  resources: [{ key: "crops", name: "Crops", category: "basic" }],
  units: [{ key: "peasant", name: "Peasant", category: "labor" }],
  settlement_tiers: [{ key: "homestead", name: "Homestead" }],
  building_definitions: [
    { key: "farm", name: "Farm", category: "basic", upkeep: [] },
    { key: "market", name: "Market", category: "basic", upkeep: [] },
  ],
  production_recipes: [{ key: "farm_victual", building_key: "farm", recipe_type: "special" }],
  transports: [{ key: "carriage", name: "Carriage", transport_type: "caravan" }],
};

const buildingsPayload = {
  items: [
    {
      id: 1,
      owner_user_id: 1,
      building_definition_id: "farm",
      count: 2,
      display_name: "North Farm",
    },
    {
      id: 2,
      owner_user_id: 2,
      house_id: 10,
      building_definition_id: "market",
      count: 1,
    },
  ],
  note: "Demo data",
};

const upkeepPayload = {
  lines: [],
  totals: [
    { item_type: "resource", item_key: "crops", amount: 2 },
    { item_type: "currency", item_key: "tower", amount: 3 },
  ],
};

const authPayload = {
  access_token: "test-token",
  token_type: "bearer",
  user: {
    id: 2,
    email: "two@example.test",
    display_name: "User Two",
    is_active: true,
  },
};

describe("App", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.endsWith("/rules/current")) {
          return Promise.resolve(jsonResponse(rulesPayload));
        }
        if (url.endsWith("/buildings/upkeep-preview")) {
          return Promise.resolve(jsonResponse(upkeepPayload));
        }
        if (url.endsWith("/buildings")) {
          return Promise.resolve(jsonResponse(buildingsPayload));
        }
        if (url.endsWith("/auth/login") && init?.method === "POST") {
          return Promise.resolve(jsonResponse(authPayload));
        }
        if (url.endsWith("/auth/me")) {
          return Promise.resolve(jsonResponse(authPayload.user));
        }
        return Promise.resolve(new Response(null, { status: 404 }));
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders rules, registry, and upkeep data from the API", async () => {
    render(<App />);

    expect(await screen.findByText("North Farm")).toBeInTheDocument();
    expect(screen.getByText("Market")).toBeInTheDocument();
    expect(screen.getByText("Rules version")).toBeInTheDocument();
    expect(screen.getByText("2.1.4")).toBeInTheDocument();
    expect(screen.getByText("crops")).toBeInTheDocument();
    expect(screen.getByText("tower")).toBeInTheDocument();
  });

  it("refreshes dashboard data on command", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("North Farm");
    await user.click(screen.getByRole("button", { name: "Refresh dashboard data" }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(6);
    });
  });

  it("signs in and signs out with the auth API", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText("Email"), "two@example.test");
    await user.type(screen.getByLabelText("Password"), "swordfish");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("User Two")).toBeInTheDocument();
    expect(localStorage.getItem("carta-auth-token")).toBe("test-token");

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(localStorage.getItem("carta-auth-token")).toBeNull();
  });
});

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
    status: 200,
  });
}
