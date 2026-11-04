import { useState, type FormEvent } from "react";

import { ApiError, api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";
import { Avatar, Field, FormError, Panel, RoleBadge } from "../components/ui";
import { relativeTime } from "../lib/format";

export function Profile() {
  const { user } = useAuth();
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const employee = user?.employee;

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const form = event.currentTarget;
    const data = new FormData(form);
    const next = String(data.get("newPassword") ?? "");

    if (next !== String(data.get("confirmPassword") ?? "")) {
      setError("The two new passwords do not match.");
      return;
    }

    setSaving(true);
    try {
      await api.post("/api/auth/change-password", {
        oldPassword: String(data.get("oldPassword") ?? ""),
        newPassword: next,
      });
      toast("Password updated", "success");
      form.reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update your password.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="management-workspace profile-workspace">
      <Panel title="Your details">
        <div className="profile-identity">
          <Avatar
            first={employee?.first_name ?? user?.username}
            last={employee?.last_name}
            seed={user?.username}
            size={52}
          />
          <div>
            <h3 style={{ fontSize: "var(--text-md)" }}>
              {employee ? `${employee.first_name} ${employee.last_name}` : user?.username}
            </h3>
            <p className="cell-secondary">{employee?.position || user?.role}</p>
          </div>
        </div>

        <dl className="detail-list">
          <div>
            <dt>Username</dt>
            <dd>{user?.username}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd>
              <RoleBadge role={user?.role} />
            </dd>
          </div>
          {employee ? (
            <>
              <div>
                <dt>Employee code</dt>
                <dd>
                  <code>{employee.employee_code}</code>
                </dd>
              </div>
              <div>
                <dt>Department</dt>
                <dd>{employee.department_name}</dd>
              </div>
              <div>
                <dt>Email</dt>
                <dd>{employee.email}</dd>
              </div>
              <div>
                <dt>Phone</dt>
                <dd>{employee.phone}</dd>
              </div>
            </>
          ) : null}
          <div>
            <dt>Last sign-in</dt>
            <dd>{user?.last_login_at ? relativeTime(user.last_login_at) : "This session"}</dd>
          </div>
        </dl>
      </Panel>

      <Panel title="Change password">
        <form onSubmit={changePassword} className="profile-password-form">
          <FormError message={error} />

          <Field label="Current password" htmlFor="old-password">
            <input
              id="old-password"
              name="oldPassword"
              type="password"
              autoComplete="current-password"
              required
            />
          </Field>

          <Field
            label="New password"
            htmlFor="new-password"
            hint="8+ characters, with a letter and a number."
          >
            <input
              id="new-password"
              name="newPassword"
              type="password"
              autoComplete="new-password"
              required
            />
          </Field>

          <Field label="Confirm new password" htmlFor="confirm-password">
            <input
              id="confirm-password"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
            />
          </Field>

          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Updating…" : "Update password"}
          </button>
        </form>
      </Panel>
    </div>
  );
}
