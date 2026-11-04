import { AlertCircle, Inbox } from "lucide-react";
import type { ReactNode } from "react";

import type { Role, Status } from "../api/types";
import { avatarStyle, initials, statusSlug } from "../lib/format";

/* --------------------------------- Panel ---------------------------------- */

export function Panel({
  title,
  actions,
  children,
  flush = false,
}: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  flush?: boolean;
}) {
  return (
    <section className="panel">
      {title || actions ? (
        <header className="panel-header">
          {title ? <h2>{title}</h2> : null}
          <div className="spacer" />
          {actions}
        </header>
      ) : null}
      <div className={flush ? "panel-body panel-body--flush" : "panel-body"}>{children}</div>
    </section>
  );
}

/* -------------------------------- Metric ---------------------------------- */

export function Metric({
  label,
  value,
  icon,
  foot,
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  foot?: ReactNode;
}) {
  return (
    <div className="metric">
      <div className="metric-label">
        {icon}
        {label}
      </div>
      <div className="metric-value">{value}</div>
      {foot ? <div className="metric-foot">{foot}</div> : null}
    </div>
  );
}

/* --------------------------------- Status --------------------------------- */

/**
 * A neutral pill with a coloured dot. Five fully-saturated pills in one table
 * column is noise; five dots is a column you can scan down.
 */
export function StatusBadge({ status }: { status?: Status | string | null }) {
  if (!status) return null;
  return (
    <span className="badge">
      <span className={`status-dot status-${statusSlug(status)}`} />
      {status}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority?: string | null }) {
  if (!priority) return null;
  return <span className={`badge badge-priority badge-${priority}`}>{priority}</span>;
}

export const ROLE_LABELS: Record<Role, string> = {
  super_admin: "Super admin",
  admin: "Admin",
  hr: "HR",
  manager: "Manager",
  team_lead: "Team lead",
  employee: "Employee",
  auditor: "Auditor",
};

export function RoleBadge({ role }: { role?: Role | null }) {
  if (!role) return null;
  return <span className={`badge role-chip role-${role}`}>{ROLE_LABELS[role] ?? role}</span>;
}

/* --------------------------------- Avatar --------------------------------- */

export function Avatar({
  first,
  last,
  seed,
  size = 26,
}: {
  first?: string | null;
  last?: string | null;
  seed?: string | null;
  size?: number;
}) {
  return (
    <span
      className="avatar"
      aria-hidden="true"
      style={{
        ...avatarStyle(seed ?? `${first}${last}`),
        width: size,
        height: size,
        fontSize: Math.round(size * 0.4),
      }}
    >
      {initials(first, last)}
    </span>
  );
}

export function AvatarStack({
  people,
  max = 3,
}: {
  people: { name?: string | null; seed?: string | null }[];
  max?: number;
}) {
  if (people.length === 0) return <span className="muted text-sm">Unassigned</span>;

  const shown = people.slice(0, max);
  const extra = people.length - shown.length;

  return (
    <span className="avatar-stack" title={people.map((p) => p.name).join(", ")}>
      {shown.map((person, index) => {
        const [first, last] = (person.name ?? "?").split(" ");
        return <Avatar key={index} first={first} last={last} seed={person.seed} size={22} />;
      })}
      {extra > 0 ? <span className="avatar-more">+{extra}</span> : null}
    </span>
  );
}

/* -------------------------------- Progress -------------------------------- */

export function Meter({
  percent,
  status,
  label,
}: {
  percent: number;
  status?: Status | string | null;
  label?: string;
}) {
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <div
      className="meter"
      role="meter"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label ?? `${Math.round(clamped)}% complete`}
    >
      <span
        className={`meter-fill${status ? ` status-${statusSlug(status)}` : ""}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

export function Donut({
  percent,
  size = 132,
  caption,
}: {
  percent: number;
  size?: number;
  caption?: string;
}) {
  const stroke = 8;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, percent));

  return (
    <div className="donut" style={{ width: size, height: size }}>
      <svg width={size} height={size} aria-hidden="true">
        <circle
          className="donut-track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
        />
        <circle
          className="donut-value"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped / 100)}
        />
      </svg>
      <span className="donut-label">{Math.round(clamped)}%</span>
      {caption ? <span className="donut-caption">{caption}</span> : null}
    </div>
  );
}

/* ------------------------------ Empty state ------------------------------- */

export function Empty({
  title,
  message,
  icon,
  action,
}: {
  title: string;
  message?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">{icon ?? <Inbox />}</span>
      <h3>{title}</h3>
      {message ? <p>{message}</p> : null}
      {action}
    </div>
  );
}

/* -------------------------------- Skeleton -------------------------------- */

export function SkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <div>
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="skeleton-row">
          <div className="skeleton skeleton-avatar" />
          <div style={{ flex: 1 }}>
            <div className="skeleton skeleton-line" style={{ width: "44%" }} />
            <div className="skeleton skeleton-line" style={{ width: "26%", marginBottom: 0 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/* --------------------------------- Forms ---------------------------------- */

export function Field({
  label,
  hint,
  htmlFor,
  children,
}: {
  label: string;
  hint?: string;
  htmlFor?: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label htmlFor={htmlFor}>{label}</label>
      {children}
      {hint ? <span className="hint">{hint}</span> : null}
    </div>
  );
}

export function FormError({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <div className="form-error" role="alert">
      <AlertCircle />
      <span>{message}</span>
    </div>
  );
}
