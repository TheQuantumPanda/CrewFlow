import { StrictMode, useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { keys } from "../api/hooks";
import type { User } from "../api/types";
import { AppShell } from "../layout/AppShell";
import { ThemeProvider } from "../theme";
import { AuthProvider, useAuth } from "./AuthContext";
import { ProtectedRoute, PublicOnlyRoute } from "./ProtectedRoute";

const clients: QueryClient[] = [];
const csrf = "logout-regression-csrf";
const scrollDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollIntoView");

function Probe({ visits }: { visits?: string[] }) {
  const { user } = useAuth();
  const location = useLocation();
  useEffect(() => { visits?.push(location.pathname); }, [location.pathname, visits]);
  return <><output data-testid="path">{location.pathname}</output><output data-testid="identity">{user?.role ?? "signed-out"}</output><Outlet /></>;
}

function mount(client: QueryClient, path: string, visits?: string[]) {
  return render(
    <StrictMode><QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}>
      <ThemeProvider><AuthProvider><Probe visits={visits} /><Routes>
        <Route element={<ProtectedRoute />}><Route element={<AppShell />}>
          <Route element={<ProtectedRoute permission="tasks.manage" />}><Route path="/tasks" element={<p>Task fixture</p>} /></Route>
          <Route element={<ProtectedRoute permission="console.access" />}><Route path="/admin" element={<p>Console fixture</p>} /></Route>
          <Route path="/my-tasks" element={<p>Assigned-work fixture</p>} />
        </Route></Route>
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<p>Workspace login fixture</p>} />
          <Route path="/admin/login" element={<p>Console login fixture</p>} />
        </Route>
      </Routes></AuthProvider></ThemeProvider>
    </MemoryRouter></QueryClientProvider></StrictMode>,
  );
}

function queryClient() {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  clients.push(client);
  return client;
}

afterEach(() => {
  cleanup();
  for (const client of clients.splice(0)) client.clear();
  vi.unstubAllGlobals();
  document.cookie = "taskforge_csrf=; Max-Age=0; Path=/";
  if (scrollDescriptor) Object.defineProperty(HTMLElement.prototype, "scrollIntoView", scrollDescriptor);
  else delete (HTMLElement.prototype as Partial<HTMLElement>).scrollIntoView;
});

const cases = [
  { role: "admin", path: "/tasks", door: "/admin/login", palette: false },
  { role: "super_admin", path: "/tasks", door: "/admin/login", palette: false },
  { role: "admin", path: "/admin", door: "/admin/login", palette: false },
  { role: "super_admin", path: "/admin", door: "/admin/login", palette: false },
  { role: "employee", path: "/my-tasks", door: "/login", palette: false },
  { role: "admin", path: "/tasks", door: "/admin/login", palette: true },
  { role: "employee", path: "/my-tasks", door: "/login", palette: true },
] as const;

describe("logout navigation with real auth/cache/guards and shell", () => {
  it.each(cases)("$role from $path, palette=$palette: clears auth and retains $door across refresh", async ({ role, path, door, palette }) => {
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: vi.fn() });
    document.cookie = `taskforge_csrf=${csrf}; Path=/`;
    const client = queryClient();
    const account: User = {
      id: 901, username: "logout.fixture", role, is_active: true, is_locked: false,
      created_at: "2026-01-01T00:00:00", last_login_at: null, grantable_roles: [],
      permissions: role === "employee" ? [] : ["console.access", "tasks.manage"],
    };
    client.setQueryData(keys.me, account);
    client.setQueryData(["tasks", "private-fixture"], ["must be removed"]);
    let signedOut = false;
    let completeLogout!: () => void;
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url === "/api/auth/logout" && init?.method === "POST") {
        return new Promise((resolve) => {
          completeLogout = () => {
            signedOut = true;
            resolve({ ok: true, status: 200, json: async () => ({ ok: true }) });
          };
        });
      }
      if (url === "/api/auth/me") {
        return Promise.resolve({ ok: !signedOut, status: signedOut ? 401 : 200,
          json: async () => signedOut ? { error: "Authentication required" } : { user: account } });
      }
      throw new Error("Unexpected fixture HTTP request");
    });
    vi.stubGlobal("fetch", fetchMock);
    const visits: string[] = [];
    const view = mount(client, path, visits);
    const user = userEvent.setup();
    if (palette) {
      await user.click(screen.getByRole("button", { name: "Open command palette" }));
      await user.type(screen.getByRole("textbox", { name: "Search commands" }), "Sign out");
      await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Sign out" }));
    } else {
      await user.click(screen.getByRole("button", { name: "Sign out" }));
    }
    expect(screen.getByTestId("path")).toHaveTextContent(path);
    expect(client.getQueryData(keys.me)).toEqual(account);
    const logoutRequest = fetchMock.mock.calls.find(([url]) => url === "/api/auth/logout")!;
    expect(logoutRequest[1]?.credentials).toBe("same-origin");
    expect(logoutRequest[1]?.headers).toMatchObject({ "X-CSRF-Token": csrf });

    await act(async () => { completeLogout(); });
    // Drain the real query notification scheduler and React redirect effects;
    // a transient correct URL must not conceal a later competing redirect.
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)); });
    await waitFor(() => expect(screen.getByTestId("identity")).toHaveTextContent("signed-out"));
    expect(client.getQueryData(keys.me)).toBeNull();
    expect(client.getQueryData(["tasks", "private-fixture"])).toBeUndefined();
    expect(screen.getByTestId("path").textContent).toBe(door);
    if (role !== "employee") expect(visits).not.toContain("/login");
    await expect(api.get("/api/auth/me")).rejects.toMatchObject({ status: 401 });

    // A fresh provider/router starts without cached identity and reads the
    // signed-out /me response, like a refresh of the resulting login page.
    view.unmount();
    mount(queryClient(), door);
    await waitFor(() => expect(screen.getByTestId("identity")).toHaveTextContent("signed-out"));
    await waitFor(() => expect(screen.queryByRole("status", { name: "Loading CrewFlow" })).not.toBeInTheDocument());
    expect(screen.getByTestId("path").textContent).toBe(door);
  });

  it.each(["admin", "super_admin"] as const)("keeps %s's console door when the guard observes auth clearing before caller navigation", async (role) => {
    const client = queryClient();
    client.setQueryData(keys.me, {
      id: 902, username: "guard-transition.fixture", role, is_active: true, is_locked: false,
      created_at: "2026-01-01T00:00:00", last_login_at: null, grantable_roles: [],
      permissions: ["console.access", "tasks.manage"],
    } satisfies User);
    const visits: string[] = [];
    mount(client, "/tasks", visits);
    expect(screen.getByTestId("identity")).toHaveTextContent(role);
    // This is the exact signed-out cache transition performed in logout's
    // finally block, isolated from the later AppShell navigation continuation.
    await act(async () => { client.setQueryData(keys.me, null); });
    await waitFor(() => expect(screen.getByTestId("identity")).toHaveTextContent("signed-out"));
    expect(client.getQueryData(keys.me)).toBeNull();
    expect(screen.getByTestId("path").textContent).toBe("/admin/login");
    expect(visits).not.toContain("/login");
  });
});
