import {
  ArrowUpDown,
  Columns3,
  ListTodo,
  Plus,
  Rows3,
  Search,
  Trash2,
  UserPlus,
} from "lucide-react";
import { useMemo, useState, type DragEvent, type FormEvent } from "react";

import { ApiError } from "../api/client";
import {
  useAssignTask,
  useAssignments,
  useDeleteTask,
  useEmployees,
  useRemoveAssignment,
  useSaveTask,
  useTasks,
  useUpdateAssignment,
} from "../api/hooks";
import { useAuth } from "../auth/AuthContext";
import { PRIORITIES, STATUSES, type Assignment, type Priority, type Status, type Task } from "../api/types";
import { useConfirm } from "../components/ConfirmDialog";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";
import {
  Avatar,
  AvatarStack,
  Empty,
  Field,
  FormError,
  Meter,
  Panel,
  PriorityBadge,
  SkeletonRows,
  StatusBadge,
} from "../components/ui";
import { relativeTime } from "../lib/format";

type View = "board" | "list";
type SortKey = "title" | "priority" | "updated_at";

const PRIORITY_RANK: Record<Priority, number> = { Urgent: 0, High: 1, Medium: 2, Low: 3 };

export function Tasks() {
  const [view, setView] = useState<View>("board");
  const [priority, setPriority] = useState("");
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Partial<Task> | null>(null);
  const [assigningTo, setAssigningTo] = useState<Task | null>(null);

  const tasks = useTasks({ priority, search });
  const assignments = useAssignments();

  return (
    <div className="task-workspace">
      {tasks.isError || assignments.isError ? (
        <FormError message="Could not load task data. Please refresh and try again." />
      ) : null}
      <Panel
        flush
        title="Backlog"
        actions={
          <div className="toolbar task-toolbar">
            <div className="segmented" role="tablist" aria-label="Task view">
              <button
                type="button"
                role="tab"
                aria-selected={view === "board"}
                onClick={() => setView("board")}
              >
                <Columns3 />
                Board
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={view === "list"}
                onClick={() => setView("list")}
              >
                <Rows3 />
                List
              </button>
            </div>

            <div className="task-search">
              <Search size={16} aria-hidden="true" />
              <input
                type="search"
                placeholder="Search tasks…"
                aria-label="Search tasks"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>

            <select
              aria-label="Filter by priority"
              value={priority}
              onChange={(event) => setPriority(event.target.value)}
              className="task-priority-filter"
            >
              <option value="">All priorities</option>
              {PRIORITIES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>

            <button type="button" className="btn btn-primary" onClick={() => setEditing({})}>
              <Plus />
              New task
            </button>
          </div>
        }
      >
        {tasks.isLoading || assignments.isLoading ? (
          <SkeletonRows count={5} />
        ) : view === "board" ? (
          <Board assignments={assignments.data ?? []} />
        ) : (
          <TaskTable
            tasks={tasks.data ?? []}
            assignments={assignments.data ?? []}
            onEdit={setEditing}
            onAssign={setAssigningTo}
            onNew={() => setEditing({})}
          />
        )}
      </Panel>

      <TaskDialog task={editing} onClose={() => setEditing(null)} />
      <AssignDialog task={assigningTo} onClose={() => setAssigningTo(null)} />
    </div>
  );
}

/* --------------------------------- Board ---------------------------------- */

function Board({ assignments }: { assignments: Assignment[] }) {
  const updateAssignment = useUpdateAssignment();
  const toast = useToast();
  const [dragOver, setDragOver] = useState<Status | null>(null);
  const [dragging, setDragging] = useState<number | null>(null);

  const columns = useMemo(() => {
    const grouped = new Map<Status, Assignment[]>(STATUSES.map((status) => [status, []]));
    for (const assignment of assignments) grouped.get(assignment.status)?.push(assignment);
    return grouped;
  }, [assignments]);

  function onDrop(event: DragEvent, status: Status) {
    event.preventDefault();
    setDragOver(null);
    setDragging(null);

    const id = Number(event.dataTransfer.getData("text/plain"));
    const assignment = assignments.find((item) => item.id === id);
    if (!assignment || assignment.status === status) return;

    updateAssignment.mutate(
      { id, status },
      {
        onSuccess: () => toast(`Moved to ${status}`, "success"),
        onError: (error) =>
          toast(error instanceof ApiError ? error.message : "Could not move that card", "error"),
      },
    );
  }

  if (assignments.length === 0) {
    return (
      <Empty
        icon={<Columns3 />}
        title="Nothing assigned yet"
        message="Create a task, then assign it to someone to see it on the board."
      />
    );
  }

  return (
    <>
      <div className="task-board-caption" role="status">
        {updateAssignment.isPending ? "Saving move…" : "Assignments by status"}
      </div>
      <div className="board" aria-label="Assignment board" aria-busy={updateAssignment.isPending}>
        {STATUSES.map((status) => {
          const items = columns.get(status) ?? [];
          const slug = status.replace(/\s+/g, "");

          return (
            <div
              key={status}
              className={`board-col${dragOver === status ? " drag-over" : ""}`}
              onDragOver={(event) => {
                event.preventDefault();
                setDragOver(status);
              }}
              onDragLeave={() => setDragOver((current) => (current === status ? null : current))}
              onDrop={(event) => onDrop(event, status)}
            >
              <div className="board-col-head">
                <span className={`status-dot status-${slug}`} />
                {status}
                <span className="board-col-count">{items.length}</span>
              </div>

              {items.map((assignment) => (
                <article
                  key={assignment.id}
                  className={`card${dragging === assignment.id ? " dragging" : ""}`}
                  draggable
                  onDragStart={(event) => {
                    event.dataTransfer.setData("text/plain", String(assignment.id));
                    setDragging(assignment.id);
                  }}
                  onDragEnd={() => setDragging(null)}
                >
                  <h3 className="card-title">{assignment.task_title}</h3>
                  {assignment.task_description ? (
                    <p className="task-summary">{assignment.task_description}</p>
                  ) : null}

                  <div className="card-meta">
                    <PriorityBadge priority={assignment.task_priority} />
                    {assignment.task_estimated_hours ? (
                      <span>{assignment.task_estimated_hours}h</span>
                    ) : null}
                  </div>

                  <Meter
                    percent={assignment.completion_percentage}
                    status={assignment.status}
                    label={`${assignment.task_title}: ${assignment.completion_percentage}% complete`}
                  />

                  <div className="card-foot">
                    <span className="task-owner">
                      <Avatar
                        first={assignment.employee_name?.split(" ")[0]}
                        last={assignment.employee_name?.split(" ")[1]}
                        seed={assignment.employee_code}
                        size={24}
                      />
                      {assignment.employee_name}
                    </span>
                    <span>{assignment.completion_percentage}%</span>
                  </div>
                </article>
              ))}

              {items.length === 0 ? <p className="board-empty">Drop here</p> : null}
            </div>
          );
        })}
      </div>
    </>
  );
}

/* ------------------------------- Task table -------------------------------- */

function TaskTable({
  tasks,
  assignments,
  onEdit,
  onAssign,
  onNew,
}: {
  tasks: Task[];
  assignments: Assignment[];
  onEdit: (task: Task) => void;
  onAssign: (task: Task) => void;
  onNew: () => void;
}) {
  const { can } = useAuth();
  const deleteTask = useDeleteTask();
  const confirm = useConfirm();
  const toast = useToast();
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({
    key: "updated_at",
    asc: false,
  });

  const assigneesByTask = useMemo(() => {
    const map = new Map<number, { name?: string | null; seed?: string | null }[]>();
    for (const assignment of assignments) {
      const list = map.get(assignment.task_id) ?? [];
      list.push({ name: assignment.employee_name, seed: assignment.employee_code });
      map.set(assignment.task_id, list);
    }
    return map;
  }, [assignments]);

  const sorted = useMemo(() => {
    const copy = [...tasks];
    copy.sort((a, b) => {
      let result = 0;
      if (sort.key === "title") result = a.title.localeCompare(b.title);
      else if (sort.key === "priority")
        result = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
      else result = a.updated_at.localeCompare(b.updated_at);
      return sort.asc ? result : -result;
    });
    return copy;
  }, [tasks, sort]);

  function toggleSort(key: SortKey) {
    setSort((current) => ({ key, asc: current.key === key ? !current.asc : true }));
  }

  function ariaSort(key: SortKey) {
    if (sort.key !== key) return "none" as const;
    return sort.asc ? ("ascending" as const) : ("descending" as const);
  }

  async function remove(task: Task) {
    const confirmed = await confirm({
      title: "Delete this task?",
      message: `“${task.title}” and its assignments will be removed from the board. The audit log keeps a record.`,
      confirmLabel: "Delete",
    });
    if (!confirmed) return;

    deleteTask.mutate(task.id, {
      onSuccess: () => toast("Task deleted", "success"),
      onError: (error) =>
        toast(error instanceof ApiError ? error.message : "Could not delete that task", "error"),
    });
  }

  if (tasks.length === 0) {
    return (
      <Empty
        icon={<ListTodo />}
        title="No tasks match"
        message="Try clearing the search or the priority filter."
        action={
          <button type="button" className="btn btn-ghost" onClick={onNew}>
            <Plus />
            New task
          </button>
        }
      />
    );
  }

  return (
    <div className="table-wrap task-table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">
              <button type="button" className="th-sort" onClick={() => toggleSort("title")} aria-sort={ariaSort("title")}>
                Task <ArrowUpDown />
              </button>
            </th>
            <th scope="col">
              <button
                type="button"
                className="th-sort"
                onClick={() => toggleSort("priority")}
                aria-sort={ariaSort("priority")}
              >
                Priority <ArrowUpDown />
              </button>
            </th>
            <th scope="col">Assignees</th>
            <th scope="col">Estimate</th>
            <th scope="col">
              <button
                type="button"
                className="th-sort"
                onClick={() => toggleSort("updated_at")}
                aria-sort={ariaSort("updated_at")}
              >
                Updated <ArrowUpDown />
              </button>
            </th>
            <th scope="col">
              <span>Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((task) => (
            <tr key={task.id}>
              <td className="task-title-cell">
                <div className="cell-primary">{task.title}</div>
                {task.description ? <div className="cell-secondary">{task.description}</div> : null}
              </td>
              <td>
                <PriorityBadge priority={task.priority} />
              </td>
              <td>
                <AvatarStack people={assigneesByTask.get(task.id) ?? []} />
              </td>
              <td className="cell-numeric">{task.estimated_hours ? `${task.estimated_hours}h` : "—"}</td>
              <td className="cell-numeric">{relativeTime(task.updated_at)}</td>
              <td>
                <div className="row-actions">
                  <button
                    type="button"
                    className="btn btn-subtle btn-sm"
                    onClick={() => onAssign(task)}
                  >
                    <UserPlus />
                    Assign
                  </button>
                  <button
                    type="button"
                    className="btn btn-subtle btn-sm"
                    onClick={() => onEdit(task)}
                  >
                    Edit
                  </button>
                  {can("tasks.delete") ? (
                    <button
                      type="button"
                      className="btn btn-subtle btn-sm btn-icon"
                      onClick={() => remove(task)}
                      aria-label={`Delete ${task.title}`}
                    >
                      <Trash2 />
                    </button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------- Task dialog ------------------------------- */

function TaskDialog({ task, onClose }: { task: Partial<Task> | null; onClose: () => void }) {
  const saveTask = useSaveTask();
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);

  if (!task) return null;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const form = new FormData(event.currentTarget);
    const estimate = String(form.get("estimated_hours") ?? "").trim();

    saveTask.mutate(
      {
        id: task!.id,
        title: String(form.get("title") ?? "").trim(),
        description: String(form.get("description") ?? ""),
        notes: String(form.get("notes") ?? ""),
        priority: form.get("priority") as Priority,
        estimated_hours: estimate === "" ? null : Number(estimate),
      },
      {
        onSuccess: () => {
          toast(task!.id ? "Task updated" : "Task created", "success");
          onClose();
        },
        onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save"),
      },
    );
  }

  return (
    <Modal open title={task.id ? "Edit task" : "New task"} onClose={onClose} className="task-dialog">
      <form onSubmit={onSubmit}>
        <div className="dialog-body">
          <FormError message={error} />

          <Field label="Title" htmlFor="task-title">
            <input id="task-title" name="title" defaultValue={task.title ?? ""} required autoFocus />
          </Field>

          <Field label="Description" htmlFor="task-description">
            <textarea
              id="task-description"
              name="description"
              defaultValue={task.description ?? ""}
              placeholder="What needs doing?"
            />
          </Field>

          <div className="form-row">
            <Field label="Priority" htmlFor="task-priority">
              <select id="task-priority" name="priority" defaultValue={task.priority ?? "Medium"}>
                {PRIORITIES.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Estimated hours" htmlFor="task-hours" hint="Optional.">
              <input
                id="task-hours"
                name="estimated_hours"
                type="number"
                min="0.5"
                step="0.5"
                defaultValue={task.estimated_hours ?? ""}
              />
            </Field>
          </div>

          <Field label="Notes" htmlFor="task-notes">
            <textarea id="task-notes" name="notes" defaultValue={task.notes ?? ""} />
          </Field>
        </div>

        <div className="dialog-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saveTask.isPending}>
            {saveTask.isPending ? "Saving…" : "Save task"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/* ------------------------------ Assign dialog ------------------------------ */

function AssignDialog({ task, onClose }: { task: Task | null; onClose: () => void }) {
  const employees = useEmployees(task !== null);
  const assignments = useAssignments();
  const assignTask = useAssignTask();
  const removeAssignment = useRemoveAssignment();
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);

  if (!task) return null;

  const current = (assignments.data ?? []).filter((item) => item.task_id === task.id);
  const assignedIds = new Set(current.map((item) => item.employee_id));
  const available = (employees.data ?? []).filter((employee) => !assignedIds.has(employee.id));

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const form = event.currentTarget;
    const employeeId = Number(new FormData(form).get("employee_id"));
    if (!employeeId) {
      setError("Pick someone to assign this to.");
      return;
    }

    assignTask.mutate(
      { task_id: task!.id, employee_id: employeeId },
      {
        onSuccess: () => {
          toast("Task assigned", "success");
          form.reset();
        },
        onError: (err) => setError(err instanceof ApiError ? err.message : "Could not assign"),
      },
    );
  }

  return (
    <Modal open title="Assign task" subtitle={task.title} onClose={onClose} width={460} className="task-dialog">
      <div className="dialog-body">
        <FormError message={error} />

        {current.length > 0 ? (
          <ul className="assignee-list">
            {current.map((assignment) => (
              <li key={assignment.id}>
                <Avatar
                  first={assignment.employee_name?.split(" ")[0]}
                  last={assignment.employee_name?.split(" ")[1]}
                  seed={assignment.employee_code}
                />
                <div>
                  <div className="cell-primary">{assignment.employee_name}</div>
                  <div className="cell-secondary">{assignment.completion_percentage}% complete</div>
                </div>
                <div className="spacer" />
                <StatusBadge status={assignment.status} />
                <button
                  type="button"
                  className="btn btn-subtle btn-sm btn-icon"
                  onClick={() =>
                    removeAssignment.mutate(assignment.id, {
                      onSuccess: () => toast("Assignment removed", "success"),
                    })
                  }
                  aria-label={`Unassign ${assignment.employee_name}`}
                >
                  <Trash2 />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm muted" style={{ marginBottom: "var(--space-4)" }}>
            Nobody is working on this yet.
          </p>
        )}

        <form onSubmit={onSubmit} id="assign-form">
          <Field label="Add an assignee" htmlFor="assignee">
            <select id="assignee" name="employee_id" defaultValue="">
              <option value="">Choose someone…</option>
              {available.map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {employee.first_name} {employee.last_name} — {employee.department_name}
                </option>
              ))}
            </select>
          </Field>
        </form>
      </div>

      <div className="dialog-footer">
        <button type="button" className="btn btn-ghost" onClick={onClose}>
          Done
        </button>
        <button
          type="submit"
          form="assign-form"
          className="btn btn-primary"
          disabled={assignTask.isPending}
        >
          <UserPlus />
          Assign
        </button>
      </div>
    </Modal>
  );
}
