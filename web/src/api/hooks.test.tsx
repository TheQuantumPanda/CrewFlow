import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { keys, useMe } from "./hooks";

function wrapper(client: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

function newClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function respondWith(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status < 400,
      status,
      json: () => Promise.resolve(body),
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useMe", () => {
  it("reports a signed-out visitor as null data, not as an error", async () => {
    respondWith(401, { error: "Authentication required" });
    const client = newClient();

    const { result } = renderHook(() => useMe(), { wrapper: wrapper(client) });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toBeNull();
    expect(result.current.isError).toBe(false);
  });

  /**
   * Regression test. A query left in an error state keeps that error even
   * after setQueryData writes fresh data into it, so seeding the cache on
   * login did not flip the route guard to "signed in" and the visitor stayed
   * stuck on the login page until a full page reload.
   */
  it("accepts a user seeded into the cache after an unauthenticated load", async () => {
    respondWith(401, { error: "Authentication required" });
    const client = newClient();

    const { result } = renderHook(() => useMe(), { wrapper: wrapper(client) });
    await waitFor(() => expect(result.current.data).toBeNull());

    client.setQueryData(keys.me, {
      id: 1,
      username: "priya.mehta",
      role: "manager",
      is_active: true,
      created_at: "2026-01-01T00:00:00",
      last_login_at: null,
    });

    await waitFor(() => expect(result.current.data?.username).toBe("priya.mehta"));
    expect(result.current.isError).toBe(false);
  });

  it("still surfaces a genuine server failure", async () => {
    respondWith(500, { error: "Something went wrong on the server" });
    const client = newClient();

    const { result } = renderHook(() => useMe(), { wrapper: wrapper(client) });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("returns the signed-in user", async () => {
    respondWith(200, { user: { id: 3, username: "aarav.sharma", role: "employee" } });
    const client = newClient();

    const { result } = renderHook(() => useMe(), { wrapper: wrapper(client) });

    await waitFor(() => expect(result.current.data?.role).toBe("employee"));
  });
});
