import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, qs } from "./client";

function mockFetch(response: { ok?: boolean; status?: number; body?: unknown }) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: response.ok ?? true,
    status: response.status ?? 200,
    json: () => Promise.resolve(response.body ?? {}),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function setCsrfCookie(value: string) {
  Object.defineProperty(document, "cookie", {
    configurable: true,
    get: () => `other=1; taskforge_csrf=${value}; another=2`,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("CSRF token handling", () => {
  it("echoes the double-submit cookie on a mutating request", async () => {
    setCsrfCookie("token-abc123");
    const fetchMock = mockFetch({ body: { ok: true } });

    await api.post("/api/tasks", { title: "x" });

    const headers = fetchMock.mock.calls[0][1].headers;
    expect(headers["X-CSRF-Token"]).toBe("token-abc123");
  });

  it("picks the right cookie when several are set", async () => {
    setCsrfCookie("only-this-one");
    const fetchMock = mockFetch({ body: {} });

    await api.del("/api/tasks/1");

    expect(fetchMock.mock.calls[0][1].headers["X-CSRF-Token"]).toBe("only-this-one");
  });

  it("does not send the header on a read", async () => {
    setCsrfCookie("token-abc123");
    const fetchMock = mockFetch({ body: { tasks: [] } });

    await api.get("/api/tasks");

    expect(fetchMock.mock.calls[0][1].headers["X-CSRF-Token"]).toBeUndefined();
  });

  it("always sends the session cookie", async () => {
    setCsrfCookie("t");
    const fetchMock = mockFetch({ body: {} });

    await api.get("/api/auth/me");

    expect(fetchMock.mock.calls[0][1].credentials).toBe("same-origin");
  });
});

describe("error handling", () => {
  it("surfaces the server's message rather than a status code", async () => {
    mockFetch({ ok: false, status: 400, body: { error: "Title is required" } });

    await expect(api.post("/api/tasks", {})).rejects.toThrow("Title is required");
  });

  it("falls back to the status when the body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: () => Promise.reject(new Error("not json")),
      }),
    );

    await expect(api.get("/api/tasks")).rejects.toThrow("Request failed (502)");
  });

  it("flags an expired session so callers can redirect", async () => {
    mockFetch({ ok: false, status: 401, body: { error: "Authentication required" } });

    await expect(api.get("/api/auth/me")).rejects.toMatchObject({ status: 401 });
    await api.get("/api/auth/me").catch((error) => {
      expect(error).toBeInstanceOf(ApiError);
      expect(error.isUnauthorized).toBe(true);
      expect(error.isForbidden).toBe(false);
    });
  });
});

describe("query strings", () => {
  it("drops empty values so a cleared filter is not sent", () => {
    expect(qs({ priority: "", status: undefined, search: null, page: 1 })).toBe("?page=1");
  });

  it("returns an empty string when nothing is set", () => {
    expect(qs({ priority: "" })).toBe("");
  });

  it("encodes values", () => {
    expect(qs({ search: "a b&c" })).toBe("?search=a+b%26c");
  });
});
