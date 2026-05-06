import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getCurrentDenizen, login } from "./api";

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              access_token: "test-token",
              token_type: "bearer",
              denizen: { id: 1, email: "one@example.test", display_name: "Denizen One" },
            }),
            {
              headers: { "Content-Type": "application/json" },
              status: 200,
            },
          ),
        ),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts login credentials as JSON", async () => {
    await login("one@example.test", "swordfish");

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.objectContaining({
        body: JSON.stringify({ email: "one@example.test", password: "swordfish" }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      }),
    );
  });

  it("sends bearer auth for current denizen requests", async () => {
    await getCurrentDenizen("test-token");

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/auth/me",
      expect.objectContaining({
        headers: { Authorization: "Bearer test-token" },
      }),
    );
  });

  it("throws on failed HTTP responses", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 401 }));

    await expect(getCurrentDenizen("expired-token")).rejects.toThrow("Request failed: 401");
  });
});
