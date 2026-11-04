import { CrewFlowBrand } from "../components/Brand";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError, api } from "../api/client";
import type { Department } from "../api/types";
import { landingFor, useAuth } from "../auth/AuthContext";
import { Field, FormError } from "../components/ui";
import { AuthLayout } from "./AuthLayout";

const EMPTY = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  department_id: "",
  position: "",
  username: "",
  password: "",
};

export function Signup() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fields, setFields] = useState(EMPTY);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // The department picker is public on purpose: a visitor has to choose one
  // before they have an account to authenticate with.
  useEffect(() => {
    api
      .get<{ departments: Department[] }>("/api/auth/departments")
      .then((response) => {
        setDepartments(response.departments);
        setFields((current) =>
          current.department_id
            ? current
            : { ...current, department_id: String(response.departments[0]?.id ?? "") },
        );
      })
      .catch(() => setError("Could not load departments. Please refresh and try again."));
  }, []);

  function set(key: keyof typeof EMPTY) {
    return (event: { target: { value: string } }) =>
      setFields((current) => ({ ...current, [key]: event.target.value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const user = await register({ ...fields, department_id: Number(fields.department_id) });
      navigate(landingFor(user), { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create your account.");
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      headline="Join your team"
      accent="in a minute."
      lede="Create your employee account, pick your department, and your manager can start assigning you work straight away."
    >
      <div className="auth-card auth-card--wide">
        <div className="auth-mobile-brand">
          <CrewFlowBrand />
        </div>

        <h1>Create account</h1>
        <p className="auth-card-sub">
          You will be added as an employee — managers and admins are created by an administrator.
        </p>

        <FormError message={error} />

        <form onSubmit={onSubmit} noValidate>
          <div className="form-row">
            <Field label="First name" htmlFor="first-name">
              <input
                id="first-name"
                autoComplete="given-name"
                value={fields.first_name}
                onChange={set("first_name")}
                required
                autoFocus
              />
            </Field>
            <Field label="Last name" htmlFor="last-name">
              <input
                id="last-name"
                autoComplete="family-name"
                value={fields.last_name}
                onChange={set("last_name")}
                required
              />
            </Field>
          </div>

          <div className="form-row">
            <Field label="Email" htmlFor="email">
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={fields.email}
                onChange={set("email")}
                required
              />
            </Field>
            <Field label="Phone" htmlFor="phone">
              <input
                id="phone"
                autoComplete="tel"
                value={fields.phone}
                onChange={set("phone")}
                required
              />
            </Field>
          </div>

          <div className="form-row">
            <Field label="Department" htmlFor="department">
              <select
                id="department"
                value={fields.department_id}
                onChange={set("department_id")}
                required
              >
                {departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Position" htmlFor="position">
              <input
                id="position"
                placeholder="Software Engineer"
                value={fields.position}
                onChange={set("position")}
              />
            </Field>
          </div>

          <div className="form-row">
            <Field
              label="Username"
              htmlFor="new-username"
              hint="Letters, numbers, dot, dash or underscore."
            >
              <input
                id="new-username"
                autoComplete="username"
                value={fields.username}
                onChange={set("username")}
                required
              />
            </Field>
            <Field
              label="Password"
              htmlFor="new-password"
              hint="8+ characters, with a letter and a number."
            >
              <input
                id="new-password"
                type="password"
                autoComplete="new-password"
                value={fields.password}
                onChange={set("password")}
                required
              />
            </Field>
          </div>

          <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="auth-alt">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </AuthLayout>
  );
}
