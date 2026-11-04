import { Link } from "react-router-dom";

import { landingFor, useAuth } from "../auth/AuthContext";

export function NotFound() {
  const { user } = useAuth();
  const home = user ? landingFor(user) : "/login";

  return (
    <div className="centered-page">
      <div>
        <div className="not-found-code">404</div>
        <h1 style={{ marginTop: "var(--space-2)" }}>That page does not exist</h1>
        <p className="muted text-sm" style={{ margin: "var(--space-2) 0 var(--space-5)" }}>
          The link may be out of date, or the page may have moved.
        </p>
        <Link className="btn btn-primary" to={home}>
          Back to CrewFlow
        </Link>
      </div>
    </div>
  );
}
