"""Dashboard audit isolation using only the existing in-memory SQLite fixtures."""
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from conftest import _signed_in_client, make_user
from sqlalchemy import event

from task_management.extensions import db
from task_management.models import ActivityLog, Department, Task, TaskAssignment
from task_management.services import activity_service


@pytest.fixture
def dashboard_case(app, department, request):
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"
    assert app.config["AUTO_BOOTSTRAP"] is False
    role = request.param
    actor = make_user(f"dashboard.{role}", role, department)
    foreign = Department(name="Foreign department")
    db.session.add(foreign)
    db.session.commit()
    outsider = make_user("foreign.employee", "employee", foreign)
    client = _signed_in_client(app, actor.username)

    active = Task(title="Active", created_by=actor.id)
    other = Task(title="Other", created_by=actor.id)
    deleted = Task(title="Deleted", created_by=actor.id, is_deleted=True)
    db.session.add_all([active, other, deleted])
    db.session.flush()
    db.session.add_all([
        TaskAssignment(task_id=active.id, employee_id=outsider.employee.id,
                       status="Completed", completion_percentage=100),
        TaskAssignment(task_id=other.id, employee_id=actor.employee.id, status="Pending"),
        TaskAssignment(task_id=other.id, employee_id=outsider.employee.id,
                       status="In Progress", completion_percentage=25),
    ])
    audit = ActivityLog(
        user_id=outsider.id, action="UPDATE", entity_type="employee",
        entity_id=outsider.employee.id,
        before_state={"department_id": foreign.id, "email": "before@example.invalid"},
        after_state={"department_id": foreign.id, "email": "foreign@example.invalid"},
        created_at=datetime.utcnow() + timedelta(seconds=1),
    )
    db.session.add(audit)
    db.session.commit()
    expected_stats = {
        "total_tasks": 2, "total_employees": 2, "total_departments": 2,
        "total_assignments": 3, "completion_rate": 33,
        "by_status": {"Pending": 1, "In Progress": 1, "Completed": 1,
                      "On Hold": 0, "Cancelled": 0},
    }
    return client, audit.to_dict(), expected_stats


@pytest.mark.parametrize("dashboard_case", ["hr", "manager", "team_lead"], indirect=True)
def test_stats_without_audit_permission_retains_metrics_but_hides_snapshots(dashboard_case):
    client, _, expected = dashboard_case
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    assert response.get_json() == {"stats": expected, "recent_activity": []}


@pytest.mark.parametrize("dashboard_case", ["hr", "manager", "team_lead"], indirect=True)
def test_stats_without_audit_permission_never_fetches_or_serializes_audit(
    dashboard_case, monkeypatch,
):
    client, _, _ = dashboard_case
    fetch = Mock(wraps=activity_service.list_recent)
    monkeypatch.setattr(activity_service, "list_recent", fetch)
    serialized = []
    original = ActivityLog.to_dict

    def serialize(entry):
        serialized.append(entry.id)
        return original(entry)

    monkeypatch.setattr(ActivityLog, "to_dict", serialize)
    audit_queries = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if "activity_logs" in statement.lower():
            audit_queries.append(statement)

    engine = db.engine
    event.listen(engine, "before_cursor_execute", capture)
    try:
        response = client.get("/api/dashboard/stats")
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert response.status_code == 200
    fetch.assert_not_called()
    assert audit_queries == []
    assert serialized == []


@pytest.mark.parametrize("dashboard_case", ["super_admin", "admin", "auditor"], indirect=True)
def test_stats_with_audit_permission_preserves_raw_activity_and_metrics(dashboard_case):
    client, audit, expected = dashboard_case
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"stats", "recent_activity"}
    assert body["stats"] == expected
    assert audit in body["recent_activity"]


@pytest.mark.parametrize(
    "dashboard_case, allowed",
    [("super_admin", True), ("admin", True), ("auditor", True),
     ("hr", False), ("manager", False), ("team_lead", False), ("employee", False)],
    indirect=["dashboard_case"],
)
def test_dedicated_activity_endpoint_keeps_its_permission_boundary(
    dashboard_case, allowed, monkeypatch,
):
    client, audit, _ = dashboard_case
    fetch = Mock(wraps=activity_service.list_recent)
    monkeypatch.setattr(activity_service, "list_recent", fetch)
    response = client.get("/api/dashboard/activity")
    if allowed:
        assert response.status_code == 200
        assert audit in response.get_json()["activity"]
    else:
        assert response.status_code == 403
        assert set(response.get_json()) == {"error"}
        fetch.assert_not_called()


@pytest.mark.parametrize("signed_in, status", [(False, 401), (True, 403)])
def test_stats_still_denies_users_without_dashboard_access(
    app, department, signed_in, status, monkeypatch,
):
    client = app.test_client()
    if signed_in:
        user = make_user("dashboard.employee", "employee", department)
        client = _signed_in_client(app, user.username)
    fetch = Mock(wraps=activity_service.list_recent)
    monkeypatch.setattr(activity_service, "list_recent", fetch)
    response = client.get("/api/dashboard/stats")
    assert response.status_code == status
    assert set(response.get_json()) == {"error"}
    fetch.assert_not_called()
