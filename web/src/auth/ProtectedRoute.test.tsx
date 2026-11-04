import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { keys } from "../api/hooks";
import type { Permission, Role, User } from "../api/types";
import { AuthProvider } from "./AuthContext";
import { ProtectedRoute, PublicOnlyRoute } from "./ProtectedRoute";

const clients: QueryClient[] = [];

function user(role: Role, permissions: Permission[]): User {
  return {
    id: 901,
    username: "routing.fixture",
    role,
    permissions,
    grantable_roles: [],
    is_active: true,
    is_locked: false,
    created_at: "2026-01-01T00:00:00",
    last_login_at: null,
  };
}

function LocationProbe() {
  const location = useLocation();
  const navigate = useNavigate();
  return (
    <>
      <output data-testid="pathname">{location.pathname}</output>
      <output data-testid="location-state">{JSON.stringify(location.state)}</output>
      <button onClick={() => navigate(-1)}>History back</button>
    </>
  );
}

function CurrentLocation() {
  return <output data-testid="current-path">{useLocation().pathname}</output>;
}

/** Exercise the real providers and guards, with a settled /me cache answer.
 * The small route tree makes redirect state/history observable; it does not
 * replace the separate browser checks of CrewFlow's actual App route tree. */
function renderGuard(entries: string[], account: User | null | undefined) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  clients.push(client);
  if (account !== undefined) client.setQueryData(keys.me, account);
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={entries}>
        <CurrentLocation />
        <AuthProvider>
          <Routes>
            <Route element={<ProtectedRoute permission="tasks.manage" />}>
              <Route path="/tasks" element={<LocationProbe />} />
            </Route>
            <Route element={<ProtectedRoute permission="console.access" />}>
              <Route path="/admin/roles" element={<LocationProbe />} />
            </Route>
            <Route element={<PublicOnlyRoute />}>
              <Route path="/login" element={<LocationProbe />} />
              <Route path="/admin/login" element={<LocationProbe />} />
            </Route>
            {["/before", "/my-tasks", "/overview", "/admin"].map((path) => (
              <Route key={path} path={path} element={<LocationProbe />} />
            ))}
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function expectPath(path: string) {
  await waitFor(() => expect(screen.getByTestId("pathname").textContent).toBe(path));
}

afterEach(() => {
  cleanup();
  for (const client of clients.splice(0)) client.clear();
  vi.unstubAllGlobals();
});

describe("routing and access regression", () => {
  it.each([
    ["/tasks", "/login"],
    ["/admin/roles", "/admin/login"],
  ])("sends a signed-out visit to %s through %s, retaining origin state", async (from, door) => {
    renderGuard([from], null);
    await expectPath(door);
    expect(JSON.parse(screen.getByTestId("location-state").textContent!)).toEqual({ from });
  });

  it("waits for /me instead of prematurely redirecting a loading visitor", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    renderGuard(["/tasks"], undefined);
    expect(screen.getByRole("status", { name: "Loading CrewFlow" })).toBeInTheDocument();
    expect(screen.queryByTestId("pathname")).not.toBeInTheDocument();
    expect(screen.getByTestId("current-path").textContent).toBe("/tasks");
  });

  it("replaces a denied route rather than adding it back to history", async () => {
    renderGuard(["/before", "/tasks"], user("employee", []));
    await expectPath("/my-tasks");
    fireEvent.click(screen.getByRole("button", { name: "History back" }));
    await expectPath("/before");
  });

  it("allows a user holding the server-supplied task permission", async () => {
    renderGuard(["/tasks"], user("manager", ["tasks.manage"]));
    await expectPath("/tasks");
  });

  it("does not derive permissions merely from the role name", async () => {
    renderGuard(["/tasks"], user("manager", []));
    await expectPath("/my-tasks");
  });

  const landings: [Role, Permission[], string][] = [
    ["super_admin", ["console.access", "dashboard.view"], "/admin"],
    ["admin", ["console.access", "dashboard.view"], "/admin"],
    ["hr", ["dashboard.view"], "/overview"],
    ["manager", ["dashboard.view"], "/overview"],
    ["team_lead", ["dashboard.view"], "/overview"],
    ["employee", [], "/my-tasks"],
    ["auditor", ["dashboard.view"], "/overview"],
  ];
  it.each(landings)("retains the public-page landing for %s", async (role, permissions, landing) => {
    renderGuard(["/login"], user(role, permissions));
    await expectPath(landing);
  });
});
