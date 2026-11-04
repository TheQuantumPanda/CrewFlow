"""Task and assignment behaviour: validation, filtering, soft delete, audit log."""
from task_management.extensions import db
from task_management.models import ActivityLog, Task


def create(client, **fields):
    payload = {"title": "A task", "priority": "High"}
    payload.update(fields)
    return client.post("/api/tasks", json=payload)


def test_create_requires_a_title(as_admin):
    response = create(as_admin, title="   ")
    assert response.status_code == 400


def test_create_rejects_an_unknown_priority(as_admin):
    assert create(as_admin, priority="Whenever").status_code == 400


def test_create_rejects_non_positive_estimated_hours(as_admin):
    assert create(as_admin, estimated_hours=0).status_code == 400
    assert create(as_admin, estimated_hours=-3).status_code == 400


def test_delete_is_a_soft_delete_and_hides_the_task(as_admin, users):
    task_id = create(as_admin).get_json()["task"]["id"]
    as_admin.delete(f"/api/tasks/{task_id}")

    assert db.session.get(Task, task_id) is not None  # row survives for the audit trail
    assert db.session.get(Task, task_id).is_deleted is True
    listed = [t["id"] for t in as_admin.get("/api/tasks").get_json()["tasks"]]
    assert task_id not in listed
    assert as_admin.get(f"/api/tasks/{task_id}").status_code == 404


def test_list_filters_by_priority(as_admin):
    create(as_admin, title="Urgent one", priority="Urgent")
    create(as_admin, title="Low one", priority="Low")

    tasks = as_admin.get("/api/tasks?priority=Urgent").get_json()["tasks"]
    assert [t["title"] for t in tasks] == ["Urgent one"]


def test_list_filters_by_search_term(as_admin):
    create(as_admin, title="Redesign the invoice page")
    create(as_admin, title="Fix the login bug")

    tasks = as_admin.get("/api/tasks?search=invoice").get_json()["tasks"]
    assert [t["title"] for t in tasks] == ["Redesign the invoice page"]


def test_list_is_paginated(as_admin):
    for index in range(5):
        create(as_admin, title=f"Task {index}")

    body = as_admin.get("/api/tasks?page=1&per_page=2").get_json()
    assert len(body["tasks"]) == 2
    assert body["total"] == 5


def test_list_reports_the_assignment_count(as_admin, users):
    task_id = create(as_admin).get_json()["task"]["id"]
    as_admin.post(
        "/api/assignments",
        json={"task_id": task_id, "employee_id": users["employee"].employee.id},
    )

    task = as_admin.get("/api/tasks").get_json()["tasks"][0]
    assert task["assignment_count"] == 1


def test_the_same_task_cannot_be_assigned_twice_to_one_person(as_admin, users):
    task_id = create(as_admin).get_json()["task"]["id"]
    payload = {"task_id": task_id, "employee_id": users["employee"].employee.id}

    assert as_admin.post("/api/assignments", json=payload).status_code == 201
    assert as_admin.post("/api/assignments", json=payload).status_code == 400


def test_assignment_rejects_an_out_of_range_percentage(as_admin, users):
    task_id = create(as_admin).get_json()["task"]["id"]
    assignment_id = as_admin.post(
        "/api/assignments",
        json={"task_id": task_id, "employee_id": users["employee"].employee.id},
    ).get_json()["assignment"]["id"]

    response = as_admin.put(
        f"/api/assignments/{assignment_id}/status", json={"completion_percentage": 140}
    )
    assert response.status_code == 400


def test_assignment_rejects_a_non_numeric_percentage(as_admin, users):
    task_id = create(as_admin).get_json()["task"]["id"]
    assignment_id = as_admin.post(
        "/api/assignments",
        json={"task_id": task_id, "employee_id": users["employee"].employee.id},
    ).get_json()["assignment"]["id"]

    response = as_admin.put(
        f"/api/assignments/{assignment_id}/status", json={"completion_percentage": "soon"}
    )
    assert response.status_code == 400


def test_assigning_a_missing_task_is_a_404(as_admin, users):
    response = as_admin.post(
        "/api/assignments",
        json={"task_id": 9999, "employee_id": users["employee"].employee.id},
    )
    assert response.status_code == 404


def test_every_write_lands_in_the_audit_log(as_admin):
    task_id = create(as_admin).get_json()["task"]["id"]
    as_admin.put(f"/api/tasks/{task_id}", json={"title": "Renamed"})
    as_admin.delete(f"/api/tasks/{task_id}")

    actions = [
        entry.action
        for entry in ActivityLog.query.filter_by(entity_type="task").order_by(ActivityLog.id).all()
    ]
    assert actions == ["CREATE", "UPDATE", "DELETE"]


def test_the_audit_log_captures_before_and_after_state(as_admin):
    task_id = create(as_admin, title="Original").get_json()["task"]["id"]
    as_admin.put(f"/api/tasks/{task_id}", json={"title": "Updated"})

    entry = ActivityLog.query.filter_by(entity_type="task", action="UPDATE").first()
    assert entry.before_state["title"] == "Original"
    assert entry.after_state["title"] == "Updated"
