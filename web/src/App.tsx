import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute, PublicOnlyRoute } from "./auth/ProtectedRoute";
import { ConfirmProvider } from "./components/ConfirmDialog";
import { ToastProvider } from "./components/Toast";
import { AppShell } from "./layout/AppShell";
import { Activity } from "./pages/Activity";
import { AdminLogin } from "./pages/AdminLogin";
import { AdminPeople } from "./pages/AdminPeople";
import { AdminRoles } from "./pages/AdminRoles";
import { Departments } from "./pages/Departments";
import { Employees } from "./pages/Employees";
import { Login } from "./pages/Login";
import { MyTasks } from "./pages/MyTasks";
import { NotFound } from "./pages/NotFound";
import { Overview } from "./pages/Overview";
import { Profile } from "./pages/Profile";
import { Signup } from "./pages/Signup";
import { Tasks } from "./pages/Tasks";
import { ThemeProvider } from "./theme";

export function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <ConfirmProvider>
          <AuthProvider>
            <Routes>
              <Route element={<PublicOnlyRoute />}>
                <Route path="/login" element={<Login />} />
                <Route path="/signup" element={<Signup />} />
                <Route path="/admin/login" element={<AdminLogin />} />
              </Route>

              {/* Each screen is gated by the permission it needs. The same
                  rules are enforced on the server; these only keep the UI honest. */}
              <Route element={<ProtectedRoute />}>
                <Route element={<AppShell />}>
                  {(
                    [
                      ["/admin", "console.access", <AdminPeople />],
                      ["/admin/roles", "console.access", <AdminRoles />],
                      ["/overview", "dashboard.view", <Overview />],
                      ["/tasks", "tasks.manage", <Tasks />],
                      ["/employees", "people.view", <Employees />],
                      ["/departments", "people.view", <Departments />],
                      ["/activity", "audit.view", <Activity />],
                      ["/my-tasks", undefined, <MyTasks />],
                      ["/profile", undefined, <Profile />],
                    ] as const
                  ).map(([path, permission, element]) => (
                    <Route key={path} element={<ProtectedRoute permission={permission} />}>
                      <Route path={path} element={element} />
                    </Route>
                  ))}
                </Route>
              </Route>

              <Route path="/" element={<Navigate to="/login" replace />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </AuthProvider>
        </ConfirmProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
