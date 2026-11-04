"""Role-based access control.

These are the regression tests for the permission holes the original build
shipped with: every logged-in user could create and delete tasks, assign work
to anybody, and edit other people's progress.
"""
from task_management.extensions import db
from task_management.models import Task, TaskAssignment


def make_task(creator, title="Ship the thing"):
    task = Task(title=title, description="", priority="High", created_by=creator.id)
    db.session.add(task)
    db.session.commit()
    return task


def assign(task, employee):
    assignment = TaskAssignment(task_id=task.id, employee_id=employee.id)
    db.session.add(assignment)
    db.session.commit()
    return assignment


# --- Tasks ---------------------------------------------------------------

def test_employee_cannot_create_a_task(as_employee):
    response = as_employee.post("/api/tasks", json={"title": "Sneaky task"})
    assert response.status_code == 403


def test_employee_cannot_delete_a_task(as_employee, users):
    task = make_task(users["admin"])
    assert as_employee.delete(f"/api/tasks/{task.id}").status_code == 403


def test_employee_cannot_edit_a_task(as_employee, users):
    task = make_task(users["admin"])
    assert as_employee.put(f"/api/tasks/{task.id}", json={"title": "Hijacked"}).status_code == 403


def test_manager_can_create_a_task(as_manager):
    assert as_manager.post("/api/tasks", json={"title": "Real task"}).status_code == 201


def test_admin_can_delete_a_task(as_admin, users):
    task = make_task(users["admin"])
    assert as_admin.delete(f"/api/tasks/{task.id}").status_code == 200
    assert db.session.get(Task, task.id).is_deleted is True


def test_anonymous_requests_are_rejected(client, users):
    task = make_task(users["admin"])
    assert client.get("/api/tasks").status_code == 401
    assert client.delete(f"/api/tasks/{task.id}").status_code == 401


# --- Assignments ---------------------------------------------------------

def test_employee_cannot_assign_work(as_employee, users):
    task = make_task(users["admin"])
    response = as_employee.post(
        "/api/assignments",
        json={"task_id": task.id, "employee_id": users["employee"].employee.id},
    )
    assert response.status_code == 403


def test_employee_cannot_update_someone_elses_assignment(as_employee, users):
    task = make_task(users["admin"])
    theirs = assign(task, users["other"].employee)

    response = as_employee.put(f"/api/assignments/{theirs.id}/status", json={"status": "Completed"})
    assert response.status_code == 403
    assert db.session.get(TaskAssignment, theirs.id).status == "Pending"


def test_employee_can_update_their_own_assignment(as_employee, users):
    task = make_task(users["admin"])
    mine = assign(task, users["employee"].employee)

    response = as_employee.put(
        f"/api/assignments/{mine.id}/status",
        json={"status": "In Progress", "completion_percentage": 40},
    )
    assert response.status_code == 200
    assert response.get_json()["assignment"]["completion_percentage"] == 40


def test_completing_an_assignment_forces_100_percent(as_employee, users):
    task = make_task(users["admin"])
    mine = assign(task, users["employee"].employee)

    response = as_employee.put(
        f"/api/assignments/{mine.id}/status",
        json={"status": "Completed", "completion_percentage": 10},
    )
    assert response.get_json()["assignment"]["completion_percentage"] == 100


def test_employee_cannot_list_every_assignment(as_employee):
    assert as_employee.get("/api/assignments").status_code == 403


def test_employee_cannot_read_another_employees_assignments(as_employee, users):
    other_id = users["other"].employee.id
    assert as_employee.get(f"/api/assignments/employee/{other_id}").status_code == 403


def test_employee_can_read_their_own_assignments(as_employee, users):
    own_id = users["employee"].employee.id
    assert as_employee.get(f"/api/assignments/employee/{own_id}").status_code == 200
    assert as_employee.get("/api/assignments/mine").status_code == 200


def test_employee_cannot_delete_an_assignment(as_employee, users):
    task = make_task(users["admin"])
    mine = assign(task, users["employee"].employee)
    assert as_employee.delete(f"/api/assignments/{mine.id}").status_code == 403


# --- Staff directory and audit log ---------------------------------------

def test_employee_cannot_enumerate_the_staff_directory(as_employee):
    assert as_employee.get("/api/employees").status_code == 403


def test_employee_cannot_read_another_profile(as_employee, users):
    other_id = users["other"].employee.id
    assert as_employee.get(f"/api/employees/{other_id}").status_code == 403


def test_employee_can_read_their_own_profile(as_employee, users):
    own_id = users["employee"].employee.id
    assert as_employee.get(f"/api/employees/{own_id}").status_code == 200


def test_only_an_admin_reads_the_audit_log(as_manager, as_employee, as_admin):
    assert as_employee.get("/api/dashboard/activity").status_code == 403
    assert as_manager.get("/api/dashboard/activity").status_code == 403
    assert as_admin.get("/api/dashboard/activity").status_code == 200


def test_manager_cannot_create_an_admin_account(as_manager, department):
    response = as_manager.post(
        "/api/employees",
        json={
            "username": "sneaky.admin",
            "password": "Password123",
            "role": "admin",
            "department_id": department.id,
            "employee_code": "ENG-900",
            "first_name": "Sneaky",
            "last_name": "Admin",
            "email": "sneaky@example.com",
            "phone": "9876500999",
        },
    )
    assert response.status_code == 403


def test_role_change_takes_effect_without_re_login(as_employee, users):
    """A promotion or demotion mid-session must bind immediately rather than
    waiting for the role cached in the cookie to expire."""
    users["employee"].role = "manager"
    db.session.commit()
    assert as_employee.post("/api/tasks", json={"title": "Now allowed"}).status_code == 201
