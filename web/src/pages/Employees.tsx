import { Plus, Search, Trash2, Users } from "lucide-react";
import { useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import { useDeleteEmployee, useDepartments, useEmployees, useSaveEmployee } from "../api/hooks";
import type { Employee, Role } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useConfirm } from "../components/ConfirmDialog";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";
import {
  Avatar,
  Empty,
  Field,
  FormError,
  Panel,
  ROLE_LABELS,
  RoleBadge,
  SkeletonRows,
} from "../components/ui";

export function Employees() {
  const { user, can } = useAuth();
  const grantable = user?.grantable_roles ?? [];
  // You may only touch people ranked below you — the same rule the API applies.
  const canTouch = (employee: Employee) =>
    can("people.manage") && employee.role !== null && grantable.includes(employee.role);
  const { data: employees, isLoading, isError } = useEmployees();
  const deleteEmployee = useDeleteEmployee();
  const confirm = useConfirm();
  const toast = useToast();

  const [editing, setEditing] = useState<Partial<Employee> | null>(null);
  const [search, setSearch] = useState("");

  const needle = search.trim().toLowerCase();
  const visible = (employees ?? []).filter((employee) =>
    needle
      ? `${employee.first_name} ${employee.last_name} ${employee.email} ${employee.employee_code} ${employee.department_name}`
          .toLowerCase()
          .includes(needle)
      : true,
  );

  async function deactivate(employee: Employee) {
    const confirmed = await confirm({
      title: "Deactivate this account?",
      message: `${employee.first_name} ${employee.last_name} will lose access and disappear from assignment lists. Their work history is kept.`,
      confirmLabel: "Deactivate",
    });
    if (!confirmed) return;

    deleteEmployee.mutate(employee.id, {
      onSuccess: () => toast("Account deactivated", "success"),
      onError: (error) =>
        toast(error instanceof ApiError ? error.message : "Could not deactivate", "error"),
    });
  }

  return (
    <div className="management-workspace people-workspace">
      <Panel
        flush
        title={`Team${visible.length ? ` · ${visible.length}` : ""}`}
        actions={
          <div className="toolbar management-toolbar">
            <div className="management-search">
              <Search size={16} aria-hidden="true" />
              <input
                type="search"
                placeholder="Search people…"
                aria-label="Search people"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            {can("people.manage") ? (
              <button type="button" className="btn btn-primary" onClick={() => setEditing({})}>
                <Plus />
                Add person
              </button>
            ) : null}
          </div>
        }
      >
        {isLoading ? (
          <SkeletonRows count={5} />
        ) : isError ? (
          <Empty icon={<Users />} title="Could not load people" message="Please refresh and try again." />
        ) : visible.length === 0 ? (
          <Empty
            icon={<Users />}
            title={needle ? "No one matches" : "Nobody here yet"}
            message={needle ? "Try a different search." : "Add someone to get started."}
          />
        ) : (
          <div className="table-wrap management-table">
            <table>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Code</th>
                  <th scope="col">Department</th>
                  <th scope="col">Position</th>
                  <th scope="col">Role</th>
                  <th scope="col">
                    <span>Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.map((employee) => (
                  <tr key={employee.id}>
                    <td>
                      <div className="cell-person">
                        <Avatar
                          first={employee.first_name}
                          last={employee.last_name}
                          seed={employee.email}
                          size={32}
                        />
                        <div style={{ minWidth: 0 }}>
                          <div className="cell-primary">
                            {employee.first_name} {employee.last_name}
                          </div>
                          <div className="cell-secondary">{employee.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <code>{employee.employee_code}</code>
                    </td>
                    <td>{employee.department_name}</td>
                    <td className="muted">{employee.position || "—"}</td>
                    <td>
                      <RoleBadge role={employee.role} />
                    </td>
                    <td>
                      {canTouch(employee) ? (
                        <div className="row-actions">
                          <button
                            type="button"
                            className="btn btn-subtle btn-sm"
                            onClick={() => setEditing(employee)}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            className="btn btn-subtle btn-sm btn-icon"
                            onClick={() => deactivate(employee)}
                            aria-label={`Deactivate ${employee.first_name} ${employee.last_name}`}
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

/** Add or edit a person. `roles` is what the signed-in user may grant. */
export function EmployeeDialog({
  employee,
  roles,
  onClose,
}: {
  employee: Partial<Employee> | null;
  roles: Role[];
  onClose: () => void;
}) {
  const { data: departments } = useDepartments(employee !== null);
  const saveEmployee = useSaveEmployee();
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);

  if (!employee) return null;
  const isNew = !employee.id;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const form = new FormData(event.currentTarget);
    const payload: Record<string, unknown> = {
      id: employee!.id,
      first_name: String(form.get("first_name") ?? "").trim(),
      last_name: String(form.get("last_name") ?? "").trim(),
      email: String(form.get("email") ?? "").trim(),
      phone: String(form.get("phone") ?? "").trim(),
      position: String(form.get("position") ?? "").trim(),
      department_id: Number(form.get("department_id")),
    };

    if (isNew) {
      payload.username = String(form.get("username") ?? "").trim();
      payload.password = String(form.get("password") ?? "");
      payload.role = String(form.get("role") ?? "employee");
      payload.employee_code = String(form.get("employee_code") ?? "").trim();
    }

    saveEmployee.mutate(payload, {
      onSuccess: () => {
        toast(isNew ? "Person added" : "Details updated", "success");
        onClose();
      },
      onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save"),
    });
  }

  return (
    <Modal open title={isNew ? "Add person" : "Edit person"} onClose={onClose} width={560} className="management-dialog">
      <form onSubmit={onSubmit}>
        <div className="dialog-body">
          <FormError message={error} />

          <div className="form-row">
            <Field label="First name" htmlFor="emp-first">
              <input
                id="emp-first"
                name="first_name"
                defaultValue={employee.first_name ?? ""}
                required
                autoFocus
              />
            </Field>
            <Field label="Last name" htmlFor="emp-last">
              <input id="emp-last" name="last_name" defaultValue={employee.last_name ?? ""} required />
            </Field>
          </div>

          <div className="form-row">
            <Field label="Email" htmlFor="emp-email">
              <input
                id="emp-email"
                name="email"
                type="email"
                defaultValue={employee.email ?? ""}
                required
              />
            </Field>
            <Field label="Phone" htmlFor="emp-phone">
              <input id="emp-phone" name="phone" defaultValue={employee.phone ?? ""} required />
            </Field>
          </div>

          <div className="form-row">
            <Field label="Department" htmlFor="emp-dept">
              <select
                id="emp-dept"
                name="department_id"
                defaultValue={employee.department_id ?? ""}
                required
              >
                {(departments ?? []).map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Position" htmlFor="emp-position">
              <input id="emp-position" name="position" defaultValue={employee.position ?? ""} />
            </Field>
          </div>

          {isNew ? (
            <>
              <div className="form-row">
                <Field label="Employee code" htmlFor="emp-code" hint="e.g. ENG-007">
                  <input id="emp-code" name="employee_code" required />
                </Field>
                <Field label="Role" htmlFor="emp-role" hint="Only roles below your own.">
                  <select id="emp-role" name="role" defaultValue="employee">
                    {roles.map((role) => (
                      <option key={role} value={role}>
                        {ROLE_LABELS[role]}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>

              <div className="form-row">
                <Field label="Username" htmlFor="emp-username">
                  <input id="emp-username" name="username" autoComplete="off" required />
                </Field>
                <Field
                  label="Temporary password"
                  htmlFor="emp-password"
                  hint="8+ characters, with a letter and a number."
                >
                  <input
                    id="emp-password"
                    name="password"
                    type="password"
                    autoComplete="new-password"
                    required
                  />
                </Field>
              </div>
            </>
          ) : null}
        </div>

        <div className="dialog-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saveEmployee.isPending}>
            {saveEmployee.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
