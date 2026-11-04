import { CrewFlowBrand } from "../components/Brand";
import { ArrowRight, Lock } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { landingFor, useAuth } from "../auth/AuthContext";
import { Field, FormError } from "../components/ui";
import { AuthLayout, DemoAccounts, WORKSPACE_DEMOS } from "./AuthLayout";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const user = await login(username.trim(), password);
      navigate(landingFor(user), { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      headline="Work that"
      accent="moves."
      lede="Assign it, track it, ship it. Every role sees exactly what it should, and every change leaves a trail."
    >
      <div className="auth-card">
        <div className="auth-mobile-brand">
          <CrewFlowBrand />
        </div>

        <div className="eyebrow rise">Workspace sign in</div>
        <h1 className="rise d1">Welcome back</h1>
        <p className="auth-card-sub rise d1">For employees, team leads, managers, HR and auditors.</p>

        <FormError message={error} />

        <form onSubmit={onSubmit} noValidate className="rise d2">
          <Field label="Username" htmlFor="username">
            <input
              id="username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              autoFocus
            />
          </Field>

          <Field label="Password" htmlFor="password">
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </Field>

          <button type="submit" className="btn btn-primary btn-lg btn-block btn-glow" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
            <ArrowRight />
          </button>
        </form>

        <div className="or-divider rise d3">or</div>

        <Link to="/admin/login" className="console-link rise d3">
          <span>
            <Lock />
            Administrator? Open the admin console
          </span>
          <ArrowRight />
        </Link>

        <p className="auth-alt rise d4">
          New here? <Link to="/signup">Create an account</Link>
        </p>

        <DemoAccounts
          accounts={WORKSPACE_DEMOS}
          onPick={(user, pass) => {
            setUsername(user);
            setPassword(pass);
          }}
        />
      </div>
    </AuthLayout>
  );
}
