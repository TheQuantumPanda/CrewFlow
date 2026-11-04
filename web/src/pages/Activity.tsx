import { History } from "lucide-react";
import { useState } from "react";

import { useActivity } from "../api/hooks";
import { Empty, Panel, SkeletonRows } from "../components/ui";
import { ActivityFeed } from "./Overview";

const FILTERS = ["All", "CREATE", "UPDATE", "DELETE", "LOGIN", "ADMIN_LOGIN", "ROLE_CHANGE"] as const;

export function Activity() {
  const { data: entries, isLoading, isError } = useActivity();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");

  const visible = (entries ?? []).filter((entry) => filter === "All" || entry.action === filter);

  return (
    <div className="management-workspace audit-workspace">
      <Panel
        flush
        title="Audit trail"
        actions={
          <div className="segmented" role="group" aria-label="Filter activity">
            {FILTERS.map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={filter === value}
                onClick={() => setFilter(value)}
              >
                {value === "All" ? "All" : value.charAt(0) + value.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
        }
      >
        {isLoading ? (
          <SkeletonRows count={8} />
        ) : isError ? (
          <Empty icon={<History />} title="Could not load activity" message="Please refresh and try again." />
        ) : visible.length === 0 ? (
          <Empty icon={<History />} title="No matching activity" message="Try a different filter." />
        ) : (
          <ActivityFeed entries={visible} />
        )}
      </Panel>
    </div>
  );
}
