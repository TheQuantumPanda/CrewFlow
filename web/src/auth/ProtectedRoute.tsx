import { Navigate, Outlet, useLocation } from "react-router-dom";

import type { Permission } from "../api/types";
import { FullPageSpinner } from "../components/Spinner";
import { landingFor, useAuth } from "./AuthContext";

/**
 * Route guard. This is a UX convenience only — every one of these rules is
 * also enforced server-side, because anything decided in the browser can be
 * edited in the browser.
 */
export function ProtectedRoute({ permission }: { permission?: Permission }) {
  const { user, isLoading, can } = useAuth();
  const location = useLocation();

  if (isLoading) return <FullPageSpinner />;
  if (!user) {
    const door = location.pathname.startsWith("/admin") ? "/admin/login" : "/login";
    return <Navigate to={door} replace state={{ from: location.pathname }} />;
  }
  if (permission && !can(permission)) return <Navigate to={landingFor(user)} replace />;

  return <Outlet />;
}

/** Bounces an already-signed-in visitor away from login and signup. */
export function PublicOnlyRoute() {
  const { user, isLoading } = useAuth();

  if (isLoading) return <FullPageSpinner />;
  if (user) return <Navigate to={landingFor(user)} replace />;

  return <Outlet />;
}
