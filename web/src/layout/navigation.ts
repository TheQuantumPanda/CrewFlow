import {
  CheckSquare,
  KeyRound,
  ShieldCheck,
  Building2,
  History,
  LayoutGrid,
  ListTodo,
  User,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { Permission } from "../api/types";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Single-key shortcut, pressed after `g` (g-then-o for Overview, vim style). */
  shortcut?: string;
  /** Hidden unless the signed-in user holds this permission. */
  permission?: Permission;
  group: "Console" | "Workspace";
  title: string;
  subtitle: string;
}

/** One source of truth for the sidebar, the command palette, and page titles. */
export const NAV_ITEMS: NavItem[] = [
  {
    to: "/admin",
    label: "Console · People",
    icon: ShieldCheck,
    shortcut: "G C",
    permission: "console.access",
    group: "Console",
    title: "Admin console",
    subtitle: "Accounts, roles and access across the workspace",
  },
  {
    to: "/admin/roles",
    label: "Roles & permissions",
    icon: KeyRound,
    shortcut: "G R",
    permission: "console.access",
    group: "Console",
    title: "Roles & permissions",
    subtitle: "Who can do what, and how far their reach goes",
  },
  {
    to: "/overview",
    label: "Overview",
    icon: LayoutGrid,
    shortcut: "G O",
    permission: "dashboard.view",
    group: "Workspace",
    title: "Overview",
    subtitle: "How the workspace is tracking",
  },
  {
    to: "/tasks",
    label: "Tasks",
    icon: ListTodo,
    shortcut: "G T",
    permission: "tasks.manage",
    group: "Workspace",
    title: "Tasks",
    subtitle: "Create work and assign it",
  },
  {
    to: "/employees",
    label: "People",
    icon: Users,
    shortcut: "G P",
    permission: "people.view",
    group: "Workspace",
    title: "People",
    subtitle: "Everyone with an account",
  },
  {
    to: "/departments",
    label: "Departments",
    icon: Building2,
    shortcut: "G D",
    permission: "people.view",
    group: "Workspace",
    title: "Departments",
    subtitle: "How the organisation is divided",
  },
  {
    to: "/activity",
    label: "Audit log",
    icon: History,
    shortcut: "G A",
    permission: "audit.view",
    group: "Workspace",
    title: "Audit log",
    subtitle: "Every change, who made it, and when",
  },
  {
    to: "/my-tasks",
    label: "My tasks",
    icon: CheckSquare,
    shortcut: "G M",
    group: "Workspace",
    title: "My tasks",
    subtitle: "Everything currently on your plate",
  },
  {
    to: "/profile",
    label: "Profile",
    icon: User,
    group: "Workspace",
    title: "Profile",
    subtitle: "Your account details and password",
  },
];

export function metaFor(pathname: string) {
  return (
    NAV_ITEMS.find((item) => item.to === pathname) ?? {
      title: "CrewFlow",
      subtitle: "",
    }
  );
}
