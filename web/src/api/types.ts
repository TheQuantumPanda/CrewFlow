export const ROLES = [
  "super_admin",
  "admin",
  "hr",
  "manager",
  "team_lead",
  "employee",
  "auditor",
] as const;
export type Role = (typeof ROLES)[number];

/** Mirrors backend/task_management/permissions.py. The server sends each user
 *  their own list on /me, so the UI never re-derives it from the role. */
export type Permission =
  | "dashboard.view"
  | "tasks.manage"
  | "tasks.delete"
  | "assignments.manage"
  | "assignments.view_all"
  | "people.view"
  | "people.manage"
  | "departments.manage"
  | "audit.view"
  | "console.access";

export const PRIORITIES = ["Low", "Medium", "High", "Urgent"] as const;
export const STATUSES = ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"] as const;

export type Priority = (typeof PRIORITIES)[number];
export type Status = (typeof STATUSES)[number];

export interface Employee {
  id: number;
  user_id: number;
  department_id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  position: string | null;
  hire_date: string | null;
  is_active: boolean;
  created_at: string;
  department_name: string | null;
  username: string | null;
  role: Role | null;
  is_locked: boolean;
  last_login_at: string | null;
}

export interface User {
  id: number;
  username: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  is_locked: boolean;
  permissions: Permission[];
  grantable_roles: Role[];
  employee?: Employee;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  notes: string | null;
  priority: Priority;
  estimated_hours: number | null;
  created_by: number;
  created_at: string;
  updated_at: string;
  assignment_count?: number;
}

export interface Assignment {
  id: number;
  task_id: number;
  employee_id: number;
  status: Status;
  completion_percentage: number;
  remarks: string | null;
  assigned_at: string;
  updated_at: string;
  task_title?: string | null;
  task_description?: string | null;
  task_priority?: Priority | null;
  task_estimated_hours?: number | null;
  employee_name?: string | null;
  employee_code?: string | null;
}

export interface Department {
  id: number;
  name: string;
  description: string | null;
}

export interface ActivityEntry {
  id: number;
  user_id: number | null;
  username: string;
  action: string;
  entity_type: string;
  entity_id: number | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  created_at: string;
}

export interface DashboardStats {
  total_tasks: number;
  total_employees: number;
  total_departments: number;
  total_assignments: number;
  completion_rate: number;
  by_status: Record<Status, number>;
}

export interface RoleMatrix {
  roles: { key: Role; label: string; level: number; scoped: boolean }[];
  permissions: { key: Permission; label: string; roles: Role[] }[];
}
