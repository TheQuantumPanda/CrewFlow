import { CrewFlowBrand } from "../components/Brand";
import { ArrowLeft, Info, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { landingFor, useAuth } from "../auth/AuthContext";
import { Field, FormError } from "../components/ui";
import { CONSOLE_DEMOS, DemoAccounts, Orbits } from "./AuthLayout";

const POLICY = [
  { tone: "teal", text: "Only super admins and admins get through this door" },
  { tone: "amber", text: "Console sessions end after 30 idle minutes" },
  { tone: "ember", text: "Every sign-in and refusal lands in the audit log" },
];

/** The admin console's own sign-in: a separate door with stricter rules. */
export function AdminLogin() {
  const { adminLogin } = useAuth();
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
      const user = await adminLogin(username.trim(), password);
      navigate(landingFor(user), { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <div className="console-auth">
      <div className="console-scan" aria-hidden="true" />
      <Orbits />

      <header className="console-auth-top">
        <div className="auth-brand">
          <CrewFlowBrand />
          <span className="console-tag">ADMIN</span>
        </div>
        <Link to="/login" className="console-back">
          <ArrowLeft size={14} /> Back to workspace sign in
        </Link>
      </header>

      <section className="console-auth-intro rise">
        <div className="shield">
          <span className="shield-ping" />
          <ShieldCheck />
        </div>
        <h1>
          Admin
          <br />
          console<span className="caret">_</span>
        </h1>
        <p>Separate door, stricter rules. Manage people, roles and access for the whole workspace.</p>
        <ul className="policy">
          {POLICY.map((p) => (
            <li key={p.text}>
              <span className={`policy-dot tone-${p.tone}`} />
              {p.text}
            </li>
          ))}
        </ul>
      </section>

      <div className="console-card rise d2">
        <div className="eyebrow">Console sign in</div>
        <FormError message={error} />
        <form onSubmit={onSubmit} noValidate>
          <Field label="Admin ID" htmlFor="admin-username">
            <input
              id="admin-username"
              className="mono"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              autoFocus
            />
          </Field>
          <Field label="Password" htmlFor="admin-password">
            <input
              id="admin-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </Field>
          <button type="submit" className="btn btn-primary btn-lg btn-block btn-glow" disabled={submitting}>
            {submitting ? "Verifying…" : "Enter console"}
          </button>
        </form>
        <div className="console-note">
          <Info size={16} />
          Anyone without an admin role is refused here, and the attempt is logged.
        </div>
        <DemoAccounts
          accounts={CONSOLE_DEMOS}
          onPick={(user, pass) => {
            setUsername(user);
            setPassword(pass);
          }}
        />
      </div>
    </div>
  );
}
