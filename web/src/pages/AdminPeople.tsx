import { Lock, Plus, Search, ShieldCheck, Trash2, Unlock, Users } from "lucide-react";
import { useState } from "react";

import { ApiError } from "../api/client";
import {
  useChangeRole,
  useDeleteEmployee,
  useEmployees,
  useUnlockEmployee,
} from "../api/hooks";
import type { Employee, Role } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useConfirm } from "../components/ConfirmDialog";
import { useToast } from "../components/Toast";
import {
  Avatar,
  Empty,
  Metric,
  Panel,
  ROLE_LABELS,
  RoleBadge,
  SkeletonRows,
} from "../components/ui";
import { relativeTime } from "../lib/format";
import { EmployeeDialog } from "./Employees";

const FILTERS: { label: string; match: (e: Employee) => boolean }[] = [
  { label: "Everyone", match: () => true },
  { label: "Admins", match: (e) => e.role === "super_admin" || e.role === "admin" },
  { label: "HR", match: (e) => e.role === "hr" },
  { label: "Managers & leads", match: (e) => e.role === "manager" || e.role === "team_lead" },
  { label: "Employees", match: (e) => e.role === "employee" },
  { label: "Auditors", match: (e) => e.role === "auditor" },
  { label: "Locked", match: (e) => e.is_locked },
];

/** The admin console's directory: every account, its role and its access. */
export function AdminPeople() {
  const { user } = useAuth();
  const grantable = user?.grantable_roles ?? [];
  const { data: employees, isLoading, isError } = useEmployees();
  const changeRole = useChangeRole();
  const unlock = useUnlockEmployee();
  const deactivate = useDeleteEmployee();
  const confirm = useConfirm();
  const toast = useToast();

  const [filter, setFilter] = useState(FILTERS[0]);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Partial<Employee> | null>(null);

  const all = employees ?? [];
  const needle = search.trim().toLowerCase();
  const visible = all.filter(
    (e) =>
      filter.match(e) &&
      (!needle ||
        `${e.first_name} ${e.last_name} ${e.username} ${e.email} ${e.department_name}`
          .toLowerCase()
          .includes(needle)),
  );
  const canTouch = (e: Employee) => e.role !== null && grantable.includes(e.role);
  const fail = (fallback: string) => (error: Error) =>
    toast(error instanceof ApiError ? error.message : fallback, "error");

  async function onRoleChange(e: Employee, role: Role) {
    const ok = await confirm({
      title: `Make ${e.first_name} ${ROLE_LABELS[role].toLowerCase()}?`,
      message: `Their access changes on their very next request. This is written to the audit log.`,
      confirmLabel: "Change role",
    });
    if (!ok) return;
    changeRole.mutate(
      { id: e.id, role },
      { onSuccess: () => toast("Role updated", "success"), onError: fail("Could not change role") },
    );
  }

  async function onDeactivate(e: Employee) {
    const ok = await confirm({
      title: "Deactivate this account?",
      message: `${e.first_name} ${e.last_name} loses access immediately. Their work history is kept.`,
      confirmLabel: "Deactivate",
    });
    if (!ok) return;
    deactivate.mutate(e.id, {
      onSuccess: () => toast("Account deactivated", "success"),
      onError: fail("Could not deactivate"),
    });
  }

  const count = (match: (e: Employee) => boolean) => all.filter(match).length;

  return (
    <div className="management-workspace admin-workspace">
      <div className="metric-grid stagger">
        <Metric label="Active people" value={isLoading || isError ? "—" : all.length} icon={<Users />} />
        <Metric label="Admins" value={isLoading || isError ? "—" : count(FILTERS[1].match)} icon={<ShieldCheck />} />
        <Metric label="Locked accounts" value={isLoading || isError ? "—" : count((e) => e.is_locked)} icon={<Lock />} />
        <Metric
          label="Roles in use"
          value={isLoading || isError ? "—" : new Set(all.map((e) => e.role)).size}
          foot="of 7 available"
        />
      </div>

      <div className="chip-row" role="group" aria-label="Filter people">
        {FILTERS.map((f) => (
          <button
            key={f.label}
            type="button"
            className="chip"
            aria-pressed={f === filter}
            onClick={() => setFilter(f)}
          >
            {f.label}
            <span className="chip-count">{isError ? "—" : count(f.match)}</span>
          </button>
        ))}
      </div>

      <Panel
        flush
        title={isError ? filter.label : `${filter.label} · ${visible.length}`}
        actions={
          <div className="toolbar management-toolbar">
            <label className="management-search">
              <Search aria-hidden="true" />
              <input
                type="search"
                placeholder="Search name, username, team…"
                aria-label="Search people"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            {grantable.length > 0 ? (
              <button type="button" className="btn btn-primary" onClick={() => setEditing({})}>
                <Plus />
                New person
              </button>
            ) : null}
          </div>
        }
      >
        {isLoading ? (
          <SkeletonRows count={6} />
        ) : isError ? (
          <Empty icon={<Users />} title="Could not load accounts" message="Please refresh and try again." />
        ) : visible.length === 0 ? (
          <Empty icon={<Users />} title="No one matches" message="Try another filter or search." />
        ) : (
          <div className="table-wrap management-table">
            <table>
              <thead>
                <tr>
                  <th scope="col">Person</th>
                  <th scope="col">Role</th>
                  <th scope="col">Department</th>
                  <th scope="col">Status</th>
                  <th scope="col">Last sign-in</th>
                  <th scope="col">
                    <span>Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="stagger">
                {visible.map((e) => (
                  <tr key={e.id}>
                    <td>
                      <div className="cell-person">
                        <Avatar first={e.first_name} last={e.last_name} seed={e.email} size={32} />
                        <div style={{ minWidth: 0 }}>
                          <div className="cell-primary">
                            {e.first_name} {e.last_name}
                          </div>
                          <div className="cell-secondary mono">{e.username}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      {canTouch(e) ? (
                        <select
                          className={`role-select role-${e.role}`}
                          value={e.role ?? ""}
                          aria-label={`Role for ${e.first_name} ${e.last_name}`}
                          onChange={(event) => void onRoleChange(e, event.target.value as Role)}
                        >
                          {grantable.map((role) => (
                            <option key={role} value={role}>
                              {ROLE_LABELS[role]}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <RoleBadge role={e.role} />
                      )}
                    </td>
                    <td>{e.department_name}</td>
                    <td>
                      {e.is_locked ? (
                        <span className="state state-locked">
                          <span className="state-dot" />
                          Locked
                        </span>
                      ) : (
                        <span className="state state-active">
                          <span className="state-dot" />
                          Active
                        </span>
                      )}
                    </td>
                    <td className="muted">{e.last_login_at ? relativeTime(e.last_login_at) : "Never"}</td>
                    <td>
                      {canTouch(e) ? (
                        <div className="row-actions">
                          {e.is_locked ? (
                            <button
                              type="button"
                              className="btn btn-subtle btn-sm"
                              onClick={() =>
                                unlock.mutate(e.id, {
                                  onSuccess: () => toast("Account unlocked", "success"),
                                  onError: fail("Could not unlock"),
                                })
                              }
                            >
                              <Unlock />
                              Unlock
                            </button>
                          ) : null}
                          <button type="button" className="btn btn-subtle btn-sm" onClick={() => setEditing(e)}>
                            Edit
                          </button>
                          <button
                            type="button"
                            className="btn btn-subtle btn-sm btn-icon"
                            onClick={() => void onDeactivate(e)}
                            aria-label={`Deactivate ${e.first_name} ${e.last_name}`}
                          >
                            <Trash2 />
                          </button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <EmployeeDialog employee={editing} roles={grantable} onClose={() => setEditing(null)} />
    </div>
  );
}
