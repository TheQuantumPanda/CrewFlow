import {
  Building2,
  CheckCircle2,
  History,
  ListTodo,
  LogIn,
  Minus,
  Pencil,
  Plus,
  Trash2,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";

import { useStats } from "../api/hooks";
import type { ActivityEntry, Status } from "../api/types";
import { relativeTime } from "../lib/format";
import { Donut, Empty, Meter, Metric, Panel, SkeletonRows } from "../components/ui";

const STATUS_ORDER: Status[] = ["Pending", "In Progress", "Completed", "On Hold", "Cancelled"];

const ACTION_ICONS: Record<string, ReactNode> = {
  CREATE: <Plus />,
  UPDATE: <Pencil />,
  DELETE: <Trash2 />,
  LOGIN: <LogIn />,
  ADMIN_LOGIN: <LogIn />,
  CONSOLE_DENIED: <LogIn />,
  ROLE_CHANGE: <Users />,
  UNLOCK: <Pencil />,
  REGISTER: <Users />,
  CHANGE_PASSWORD: <Pencil />,
  SEED: <History />,
};

export function Overview() {
  const { data, isLoading, isError } = useStats();

  if (isError) {
    return (
      <Panel>
        <Empty title="Could not load the dashboard" message="Please refresh and try again." />
      </Panel>
    );
  }

  const stats = data?.stats;
  const activity = data?.recent_activity ?? [];
  const total = stats?.total_assignments ?? 0;
  const dash = (value?: number) => (value === undefined ? "—" : value);

  return (
    <div className="overview" aria-busy={isLoading}>
      <section className="overview-intro" aria-labelledby="overview-intro-title">
        <div>
          <p className="eyebrow">Your overview</p>
          <h2 id="overview-intro-title">Work in sync.</h2>
          <p className="overview-lede">Assignments, people and progress. A clear view of the work ahead.</p>
        </div>
        <span className="overview-context">
          <ListTodo size={16} aria-hidden="true" />
          {isLoading ? <span role="status">Loading overview…</span> : `${total} assignment${total === 1 ? "" : "s"}`}
        </span>
      </section>

      <div className="metric-grid overview-metrics">
        <Metric
          label="Tasks"
          value={dash(stats?.total_tasks)}
          icon={<ListTodo />}
          foot={stats ? `${total} assignment${total === 1 ? "" : "s"} in total` : undefined}
        />
        <Metric label="People" value={dash(stats?.total_employees)} icon={<Users />} foot="Active employee accounts" />
        <Metric label="Departments" value={dash(stats?.total_departments)} icon={<Building2 />} foot="Workspace structure" />
        <Metric
          label="Completed"
          value={stats ? `${stats.completion_rate}%` : "—"}
          icon={<CheckCircle2 />}
          foot={
            stats ? `${stats.by_status.Completed ?? 0} of ${total} assignments done` : undefined
          }
        />
      </div>

      <div className="overview-panels">
        <div className="overview-distribution">
          <Panel title="Assignment breakdown">
            {isLoading ? (
              <SkeletonRows count={5} />
            ) : (
              <div className="overview-breakdown">
                <div className="overview-completion">
                  <Donut percent={stats?.completion_rate ?? 0} caption="complete" size={156} />
                  <p>{stats?.by_status.Completed ?? 0} of {total} assignments complete</p>
                </div>
                <div className="overview-statuses">
                  {STATUS_ORDER.map((status) => {
                    const count = stats?.by_status?.[status] ?? 0;
                    const share = total ? (count / total) * 100 : 0;
                    return (
                      <div className="meter-row" key={status}>
                        <span className="meter-row-label">
                          <span className={`status-dot status-${status.replace(/\s+/g, "")}`} />
                          {status}
                        </span>
                        <Meter
                          percent={share}
                          status={status}
                          label={`${status}: ${count} of ${total}`}
                        />
                        <span className="meter-row-value">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            {!isLoading && total === 0 ? (
              <p className="overview-empty-note">No assignments yet. Status and progress will appear here as work is assigned.</p>
            ) : null}
          </Panel>
        </div>
        <div className="overview-activity">
          <Panel title="Recent activity" flush>
            {isLoading ? <SkeletonRows count={5} /> : <ActivityFeed entries={activity} />}
          </Panel>
        </div>
      </div>
    </div>
  );
}

export function ActivityFeed({ entries }: { entries: ActivityEntry[] }) {
  if (entries.length === 0) {
    return (
      <Empty
        icon={<History />}
        title="Nothing yet"
        message="Activity appears here as people create and update work."
      />
    );
  }

  return (
    <ul className="feed">
      {entries.map((entry) => (
        <li key={entry.id} className="feed-item">
          <span className={`feed-icon feed-icon--${entry.action.toLowerCase()}`}>
            {ACTION_ICONS[entry.action] ?? <Minus />}
          </span>
          <div className="feed-body">
            <div className="feed-text">
              <strong>{entry.username}</strong> {describe(entry)}
            </div>
            <time className="feed-time" dateTime={entry.created_at}>
              {relativeTime(entry.created_at)}
            </time>
          </div>
        </li>
      ))}
    </ul>
  );
}

function describe(entry: ActivityEntry) {
  const label =
    (entry.after_state?.title as string | undefined) ??
    (entry.before_state?.title as string | undefined) ??
    (entry.after_state?.name as string | undefined) ??
    null;

  const subject = label ? `“${label}”` : `${entry.entity_type} #${entry.entity_id ?? "?"}`;

  switch (entry.action) {
    case "CREATE":
      return `created ${entry.entity_type} ${subject}`;
    case "UPDATE":
      return `updated ${entry.entity_type} ${subject}`;
    case "DELETE":
      return `deleted ${entry.entity_type} ${subject}`;
    case "LOGIN":
      return "signed in";
    case "REGISTER":
      return "created an account";
    case "CHANGE_PASSWORD":
      return "changed their password";
    default:
      return `${entry.action.toLowerCase()} ${entry.entity_type}`;
  }
}
