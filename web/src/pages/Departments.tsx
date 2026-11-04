import { Building2, Plus } from "lucide-react";
import { useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import { useCreateDepartment, useDepartments, useEmployees } from "../api/hooks";
import { useAuth } from "../auth/AuthContext";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";
import { Avatar, Empty, Field, FormError, Panel, SkeletonRows } from "../components/ui";
import { pluralise } from "../lib/format";

export function Departments() {
  const { can } = useAuth();
  const { data: departments, isLoading, isError } = useDepartments();
  const { data: employees, isError: membersError } = useEmployees();
  const [adding, setAdding] = useState(false);

  const members = new Map<number, typeof employees extends undefined ? never : NonNullable<typeof employees>>();
  for (const employee of employees ?? []) {
    const list = members.get(employee.department_id) ?? [];
    list.push(employee);
    members.set(employee.department_id, list);
  }

  return (
    <div className="management-workspace departments-workspace">
      <Panel
        flush
        title="Departments"
        actions={
          can("departments.manage") ? (
            <button type="button" className="btn btn-primary" onClick={() => setAdding(true)}>
              <Plus />
              New department
            </button>
          ) : null
        }
      >
        {isLoading ? (
          <SkeletonRows count={4} />
        ) : isError ? (
          <Empty icon={<Building2 />} title="Could not load departments" message="Please refresh and try again." />
        ) : (departments ?? []).length === 0 ? (
          <Empty
            icon={<Building2 />}
            title="No departments yet"
            message="Create one to start grouping your team."
          />
        ) : (
          <div className="table-wrap management-table">
            <table>
              <thead>
                <tr>
                  <th scope="col">Department</th>
                  <th scope="col">Description</th>
                  <th scope="col">People</th>
                  <th scope="col">Members</th>
                </tr>
              </thead>
              <tbody>
                {(departments ?? []).map((department) => {
                  const people = members.get(department.id) ?? [];
                  return (
                    <tr key={department.id}>
                      <td>
                        <div className="cell-person">
                          <span className="empty-icon department-symbol">
                            <Building2 size={16} />
                          </span>
                          <span className="cell-primary">{department.name}</span>
                        </div>
                      </td>
                      <td className="muted">{department.description || "—"}</td>
                      <td className="cell-numeric">
                        {membersError ? "Unavailable" : pluralise(people.length, "person", "people")}
                      </td>
                      <td>
                        {membersError ? (
                          <span className="muted text-sm">Unavailable</span>
                        ) : (
                          <span className="avatar-stack">
                            {people.slice(0, 5).map((person) => (
                              <Avatar
                                key={person.id}
                                first={person.first_name}
                                last={person.last_name}
                                seed={person.email}
                                size={26}
                              />
                            ))}
                            {people.length > 5 ? (
                              <span className="avatar-more">+{people.length - 5}</span>
                            ) : null}
                            {people.length === 0 ? <span className="muted text-sm">—</span> : null}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <DepartmentDialog open={adding} onClose={() => setAdding(false)} />
    </div>
  );
}

function DepartmentDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const createDepartment = useCreateDepartment();
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const form = new FormData(event.currentTarget);
    createDepartment.mutate(
      {
        name: String(form.get("name") ?? "").trim(),
        description: String(form.get("description") ?? "").trim(),
      },
      {
        onSuccess: () => {
          toast("Department created", "success");
          onClose();
        },
        onError: (err) => setError(err instanceof ApiError ? err.message : "Could not create it"),
      },
    );
  }

  return (
    <Modal open title="New department" onClose={onClose} width={420} className="management-dialog">
      <form onSubmit={onSubmit}>
        <div className="dialog-body">
          <FormError message={error} />

          <Field label="Name" htmlFor="dept-name">
            <input id="dept-name" name="name" required placeholder="Engineering" />
          </Field>

          <Field label="Description" htmlFor="dept-description">
            <textarea
              id="dept-description"
              name="description"
              placeholder="What does this team do?"
            />
          </Field>
        </div>

        <div className="dialog-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={createDepartment.isPending}>
            Create
          </button>
        </div>
      </form>
    </Modal>
  );
}
