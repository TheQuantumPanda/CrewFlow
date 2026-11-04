import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api, qs } from "./client";
import type {
  ActivityEntry,
  Assignment,
  DashboardStats,
  Department,
  Employee,
  Role,
  RoleMatrix,
  Task,
  User,
} from "./types";

export const keys = {
  me: ["me"] as const,
  tasks: (filters?: unknown) => ["tasks", filters] as const,
  assignments: ["assignments"] as const,
  myAssignments: ["assignments", "mine"] as const,
  employees: ["employees"] as const,
  departments: ["departments"] as const,
  stats: ["dashboard", "stats"] as const,
  activity: ["dashboard", "activity"] as const,
  roleMatrix: ["admin", "roles"] as const,
};

/**
 * Invalidates everything a write could plausibly have changed. Task and
 * assignment edits both move the dashboard counters, so refreshing only the
 * edited list leaves visibly stale numbers on screen.
 */
function useRefresh() {
  const queryClient = useQueryClient();
  return () => {
    for (const key of [["tasks"], ["assignments"], ["dashboard"], ["employees"], ["departments"]]) {
      void queryClient.invalidateQueries({ queryKey: key });
    }
  };
}

/* ---------------------------------- Auth --------------------------------- */

export function useMe(enabled = true) {
  return useQuery<User | null>({
    queryKey: keys.me,
    // "Nobody is signed in" is a successful answer to "who am I?", not a
    // failure, so a 401 is folded into `null` data instead of being left as a
    // query error. That distinction matters: an errored query keeps its error
    // even after setQueryData writes fresh data into it, so seeding this cache
    // on login would not clear it and the route guard would keep the visitor
    // on the login page until a full reload.
    queryFn: async () => {
      try {
        const response = await api.get<{ user: User }>("/api/auth/me");
        return response.user;
      } catch (error) {
        if (error instanceof ApiError && error.isUnauthorized) return null;
        throw error;
      }
    },
    retry: false,
    enabled,
  });
}

export interface TaskFilters {
  priority?: string;
  status?: string;
  search?: string;
}

/* ---------------------------------- Tasks -------------------------------- */

export function useTasks(filters: TaskFilters = {}) {
  return useQuery({
    queryKey: keys.tasks(filters),
    queryFn: () =>
      api
        .get<{ tasks: Task[]; total: number }>(`/api/tasks${qs({ ...filters, per_page: 200 })}`)
        .then((r) => r.tasks),
  });
}

export function useSaveTask() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<Task> & { id?: number }) =>
      id
        ? api.put<{ task: Task }>(`/api/tasks/${id}`, body)
        : api.post<{ task: Task }>("/api/tasks", body),
    onSuccess: refresh,
  });
}

export function useDeleteTask() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (id: number) => api.del(`/api/tasks/${id}`),
    onSuccess: refresh,
  });
}

/* ------------------------------- Assignments ------------------------------ */

export function useAssignments() {
  return useQuery({
    queryKey: keys.assignments,
    queryFn: () =>
      api.get<{ assignments: Assignment[] }>("/api/assignments").then((r) => r.assignments),
  });
}

export function useMyAssignments() {
  return useQuery({
    queryKey: keys.myAssignments,
    queryFn: () =>
      api.get<{ assignments: Assignment[] }>("/api/assignments/mine").then((r) => r.assignments),
  });
}

export function useAssignTask() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (body: { task_id: number; employee_id: number }) =>
      api.post("/api/assignments", body),
    onSuccess: refresh,
  });
}

export function useUpdateAssignment() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; status?: string; completion_percentage?: number; remarks?: string }) =>
      api.put<{ assignment: Assignment }>(`/api/assignments/${id}/status`, body),
    onSuccess: refresh,
  });
}

export function useRemoveAssignment() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (id: number) => api.del(`/api/assignments/${id}`),
    onSuccess: refresh,
  });
}

/* -------------------------- Employees & departments ----------------------- */

export function useEmployees(enabled = true) {
  return useQuery({
    queryKey: keys.employees,
    queryFn: () => api.get<{ employees: Employee[] }>("/api/employees").then((r) => r.employees),
    enabled,
  });
}

export function useDepartments(enabled = true) {
  return useQuery({
    queryKey: keys.departments,
    queryFn: () =>
      api.get<{ departments: Department[] }>("/api/departments").then((r) => r.departments),
    enabled,
  });
}

export function useSaveEmployee() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ id, ...body }: Record<string, unknown> & { id?: number }) =>
      id
        ? api.put<{ employee: Employee }>(`/api/employees/${id}`, body)
        : api.post<{ employee: Employee }>("/api/employees", body),
    onSuccess: refresh,
  });
}

export function useDeleteEmployee() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (id: number) => api.del(`/api/employees/${id}`),
    onSuccess: refresh,
  });
}

export function useChangeRole() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: ({ id, role }: { id: number; role: Role }) =>
      api.put<{ employee: Employee }>(`/api/employees/${id}/role`, { role }),
    onSuccess: refresh,
  });
}

export function useUnlockEmployee() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (id: number) => api.post<{ employee: Employee }>(`/api/employees/${id}/unlock`),
    onSuccess: refresh,
  });
}

export function useRoleMatrix() {
  return useQuery({
    queryKey: keys.roleMatrix,
    queryFn: () => api.get<RoleMatrix>("/api/admin/roles"),
    staleTime: Infinity,
  });
}

export function useCreateDepartment() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (body: { name: string; description?: string }) =>
      api.post<{ department: Department }>("/api/departments", body),
    onSuccess: refresh,
  });
}

/* -------------------------------- Dashboard ------------------------------- */

export function useStats() {
  return useQuery({
    queryKey: keys.stats,
    queryFn: () =>
      api
        .get<{ stats: DashboardStats; recent_activity: ActivityEntry[] }>("/api/dashboard/stats"),
  });
}

export function useActivity(enabled = true) {
  return useQuery({
    queryKey: keys.activity,
    queryFn: () =>
      api
        .get<{ activity: ActivityEntry[] }>("/api/dashboard/activity?limit=60")
        .then((r) => r.activity),
    enabled,
  });
}
