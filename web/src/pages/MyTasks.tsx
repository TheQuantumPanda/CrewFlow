import { CheckCircle2, CircleDashed, Inbox, ListTodo, TrendingUp } from "lucide-react";
import { useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import { useMyAssignments, useUpdateAssignment } from "../api/hooks";
import { STATUSES, type Assignment, type Status } from "../api/types";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";
import {
  Donut,
  Empty,
  Field,
  FormError,
  Meter,
  Metric,
  Panel,
  PriorityBadge,
  SkeletonRows,
  StatusBadge,
} from "../components/ui";
import { relativeTime } from "../lib/format";

export function MyTasks() {
  const { data: assignments, isLoading, isError } = useMyAssignments();
  const [editing, setEditing] = useState<Assignment | null>(null);

  const items = assignments ?? [];
  const done = items.filter((item) => item.status === "Completed").length;
  const active = items.filter((item) => item.status === "In Progress").length;
  const average = items.length
    ? Math.round(items.reduce((sum, item) => sum + item.completion_percentage, 0) / items.length)
    : 0;

  return (
    <div className="my-task-workspace">
      {isError ? <FormError message="Could not load your assignments. Please refresh and try again." /> : null}
      <div className="metric-grid">
        <Metric label="Assigned to me" value={items.length} icon={<ListTodo />} />
        <Metric label="In progress" value={active} icon={<CircleDashed />} />
        <Metric label="Completed" value={done} icon={<CheckCircle2 />} />
        <Metric label="Average progress" value={`${average}%`} icon={<TrendingUp />} />
      </div>

      <div className="my-task-panels">
        <Panel title="Your progress">
          <div className="my-task-breakdown">
            <Donut percent={average} caption="average" />
            <div className="my-task-statuses">
              {STATUSES.map((status) => {
                const count = items.filter((item) => item.status === status).length;
                const share = items.length ? (count / items.length) * 100 : 0;
                return (
                  <div className="meter-row" key={status}>
                    <span className="meter-row-label">
                      <span className={`status-dot status-${status.replace(/\s+/g, "")}`} />
                      {status}
                    </span>
                    <Meter
                      percent={share}
                      status={status}
                      label={`${status}: ${count} of ${items.length}`}
                    />
                    <span className="meter-row-value">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </Panel>

        <Panel title="Next up">
          {items.filter((item) => item.status !== "Completed" && item.status !== "Cancelled")
            .length === 0 ? (
            <Empty icon={<CheckCircle2 />} title="All clear" message="Nothing outstanding." />
          ) : (
            <div className="detail-list">
              {items
                .filter((item) => item.status !== "Completed" && item.status !== "Cancelled")
                .slice(0, 5)
                .map((assignment) => (
                  <div key={assignment.id}>
                    <dt style={{ color: "var(--text)", fontWeight: 500 }}>
                      {assignment.task_title}
                    </dt>
                    <dd>
                      <PriorityBadge priority={assignment.task_priority} />
                    </dd>
                  </div>
                ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel title="Assigned tasks">
        {isLoading ? (
          <SkeletonRows count={4} />
        ) : items.length === 0 ? (
          <Empty
            icon={<Inbox />}
            title="Nothing on your plate"
            message="When a manager assigns you work, it shows up here."
          />
        ) : (
          <div className="task-grid">
            {items.map((assignment) => (
              <article key={assignment.id} className="card">
                <h3 className="card-title">{assignment.task_title}</h3>
                {assignment.task_description ? (
                  <p className="cell-secondary">{assignment.task_description}</p>
                ) : null}

                <div className="card-meta">
                  <StatusBadge status={assignment.status} />
                  <PriorityBadge priority={assignment.task_priority} />
                  {assignment.task_estimated_hours ? (
                    <span>{assignment.task_estimated_hours}h</span>
                  ) : null}
                </div>

                <Meter
                  percent={assignment.completion_percentage}
                  status={assignment.status}
                  label={`${assignment.completion_percentage}% complete`}
                />

                <div className="card-foot">
                  <time dateTime={assignment.updated_at}>
                    Updated {relativeTime(assignment.updated_at)}
                  </time>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => setEditing(assignment)}
                  >
                    Update
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </Panel>

      <UpdateDialog assignment={editing} onClose={() => setEditing(null)} />
    </div>
  );
}

function UpdateDialog({
  assignment,
  onClose,
}: {
  assignment: Assignment | null;
  onClose: () => void;
}) {
  const updateAssignment = useUpdateAssignment();
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<Status>("Pending");
  const [openFor, setOpenFor] = useState<number | null>(null);

  // Re-seed the form when a different card is opened.
  if (assignment && openFor !== assignment.id) {
    setOpenFor(assignment.id);
    setProgress(assignment.completion_percentage);
    setStatus(assignment.status);
    setError(null);
  }

  if (!assignment) return null;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const remarks = String(new FormData(event.currentTarget).get("remarks") ?? "");

    updateAssignment.mutate(
      { id: assignment!.id, status, completion_percentage: progress, remarks },
      {
        onSuccess: () => {
          toast(status === "Completed" ? "Task completed" : "Progress saved", "success");
          onClose();
        },
        onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save"),
      },
    );
  }

  return (
    <Modal
      open
      title="Update progress"
      subtitle={assignment.task_title ?? undefined}
      onClose={onClose}
      width={460}
      className="task-dialog"
    >
      <form onSubmit={onSubmit}>
        <div className="dialog-body">
          <FormError message={error} />

          <Field label="Status" htmlFor="assignment-status">
            <select
              id="assignment-status"
              value={status}
              onChange={(event) => {
                const next = event.target.value as Status;
                setStatus(next);
                // Marking something done and leaving the bar at 40% is a
                // mismatch the server corrects anyway — reflect it now.
                if (next === "Completed") setProgress(100);
              }}
            >
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </Field>

          <Field label={`Completion — ${progress}%`} htmlFor="assignment-progress">
            <input
              id="assignment-progress"
              type="range"
              min={0}
              max={100}
              step={5}
              value={progress}
              onChange={(event) => setProgress(Number(event.target.value))}
            />
          </Field>

          <Field label="Remarks" htmlFor="assignment-remarks">
            <textarea
              id="assignment-remarks"
              name="remarks"
              defaultValue={assignment.remarks ?? ""}
              placeholder="Notes for your manager…"
            />
          </Field>
        </div>

        <div className="dialog-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={updateAssignment.isPending}>
            {updateAssignment.isPending ? "Saving…" : "Save update"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
