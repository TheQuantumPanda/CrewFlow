import { StrictMode, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { keys } from "../api/hooks";
import type { User } from "../api/types";
import { AuthProvider } from "../auth/AuthContext";
import { Departments } from "../pages/Departments";
import { Employees } from "../pages/Employees";
import { Tasks } from "../pages/Tasks";
import { ConfirmProvider } from "./ConfirmDialog";
import { ToastProvider } from "./Toast";

const clients: QueryClient[] = [];

function fixture(children: ReactNode, strict: boolean) {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  clients.push(client);
  client.setQueryData(keys.me, {
    id: 901, username: "modal.fixture", role: "super_admin", is_active: true, is_locked: false,
    created_at: "2026-01-01T00:00:00", last_login_at: null,
    permissions: ["tasks.manage", "tasks.delete", "assignments.manage", "people.view", "people.manage", "departments.manage"],
    grantable_roles: ["employee"],
  } satisfies User);
  client.setQueryData(keys.tasks({ priority: "", search: "" }), []);
  client.setQueryData(keys.assignments, []);
  client.setQueryData(keys.employees, []);
  client.setQueryData(keys.departments, [{ id: 201, name: "Fixture department", description: null }]);
  const ui = <QueryClientProvider client={client}><ToastProvider><ConfirmProvider><AuthProvider>{children}</AuthProvider></ConfirmProvider></ToastProvider></QueryClientProvider>;
  render(strict ? <StrictMode>{ui}</StrictMode> : ui);
}

afterEach(() => {
  cleanup();
  for (const client of clients.splice(0)) client.clear();
  document.body.style.overflow = "";
});

describe.each([false, true])("real autofocus-affected dialogs (StrictMode=%s)", (strict) => {
  const cases = [
    { component: <Tasks />, opener: "New task", title: "New task", field: "Title" },
    { component: <Employees />, opener: "Add person", title: "Add person", field: "First name" },
    { component: <Departments />, opener: "New department", title: "New department", field: "Name" },
  ];
  it.each(cases)("returns focus from $title to its keyboard opener", async ({ component, opener: name, title, field }) => {
    fixture(component, strict);
    const user = userEvent.setup();
    const opener = screen.getByRole("button", { name });
    for (let step = 0; step < 40 && document.activeElement !== opener; step++) await user.tab();
    expect(opener).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("dialog", { name: title })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: field })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("dialog")).toContainElement(document.activeElement as HTMLElement);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });
});
