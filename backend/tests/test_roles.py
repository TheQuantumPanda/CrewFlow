"""The extended role model: the two sign-in doors, rank rules on granting and
re-roling, department scoping for managers and team leads, and read-only
auditors."""
from datetime import datetime, timedelta

from conftest import PASSWORD, _signed_in_client, make_user
from test_authorization import make_task

from task_management.extensions import db
from task_management.models import Department, User
from task_management.permissions import LEVEL, PERMISSIONS, ROLES, grantable_roles


def new_person(department, role="employee", username="new.person"):
    return {
        "username": username,
        "password": "Password123",
        "role": role,
        "department_id": department.id,
        "employee_code": f"X-{username[:6]}",
        "first_name": "New",
        "last_name": "Person",
        "email": f"{username}@example.com",
        "phone": "9876500123",
    }


def other_department():
    dept = Department(name="Sales", description="")
    db.session.add(dept)
    db.session.commit()
    return dept


def test_every_role_has_a_rank_and_every_permission_names_real_roles():
    assert set(LEVEL) == set(ROLES)
    for roles in PERMISSIONS.values():
        assert roles <= set(ROLES)


def test_nobody_can_grant_their_own_rank_or_higher():
    for role in ROLES:
        assert all(LEVEL[r] < LEVEL[role] for r in grantable_roles(role))
    assert "super_admin" not in grantable_roles("super_admin")
    assert grantable_roles("employee") == []


# --- The two doors --------------------------------------------------------

def test_admin_cannot_use_the_workspace_login(client, users):
    response = client.post("/api/auth/login", json={"username": "admin.user", "password": PASSWORD})
    assert response.status_code == 403


def test_employee_cannot_use_the_admin_console_login(client, users):
    response = client.post("/api/auth/admin/login", json={"username": "employee.one", "password": PASSWORD})
    assert response.status_code == 403
    assert client.get("/api/auth/me").status_code == 401


def test_admin_console_login_still_hides_bad_passwords(client, users):
    response = client.post("/api/auth/admin/login", json={"username": "admin.user", "password": "wrong1234"})
    assert response.status_code == 401


def test_promotion_to_admin_mid_session_does_not_carry_admin_power(as_employee, users):
    users["employee"].role = "admin"
    db.session.commit()
    assert as_employee.get("/api/employees").status_code == 401


def test_admin_session_times_out_when_idle(as_admin, app):
    with as_admin.session_transaction() as sess:
        sess["seen"] -= app.config["ADMIN_IDLE_MINUTES"] * 60 + 1
    assert as_admin.get("/api/auth/me").status_code == 401


def test_me_reports_permissions(as_admin):
    user = as_admin.get("/api/auth/me").get_json()["user"]
    assert "console.access" in user["permissions"]
    assert "admin" not in user["grantable_roles"]
    assert "hr" in user["grantable_roles"]


# --- Rank rules -----------------------------------------------------------

def test_admin_cannot_create_another_admin(as_admin, department):
    assert as_admin.post("/api/employees", json=new_person(department, "admin")).status_code == 403


def test_super_admin_can_create_an_admin(app, department):
    make_user("root.user", "super_admin", department)
    client = _signed_in_client(app, "root.user")
    assert client.post("/api/employees", json=new_person(department, "admin")).status_code == 201


def test_hr_can_create_an_employee_but_not_tasks(app, department):
    make_user("hr.user", "hr", department)
    client = _signed_in_client(app, "hr.user")
    assert client.post("/api/employees", json=new_person(department)).status_code == 201
    assert client.post("/api/tasks", json={"title": "Nope"}).status_code == 403


def test_admin_can_re_role_below_their_rank(as_admin, users):
    emp_id = users["employee"].employee.id
    response = as_admin.put(f"/api/employees/{emp_id}/role", json={"role": "team_lead"})
    assert response.status_code == 200
    assert db.session.get(User, users["employee"].id).role == "team_lead"


def test_manager_cannot_touch_a_peer(as_manager, department):
    peer = make_user("manager.two", "manager", department)
    response = as_manager.put(f"/api/employees/{peer.employee.id}/role", json={"role": "employee"})
    assert response.status_code == 403


def test_nobody_can_deactivate_themselves(as_manager, users):
    own_id = users["manager"].employee.id
    assert as_manager.delete(f"/api/employees/{own_id}").status_code == 403


def test_unlock_clears_a_lockout(as_admin, users):
    users["employee"].locked_until = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    emp_id = users["employee"].employee.id
    assert as_admin.post(f"/api/employees/{emp_id}/unlock").status_code == 200
    assert db.session.get(User, users["employee"].id).is_locked is False


# --- Department scoping ---------------------------------------------------

def test_manager_sees_only_their_department(as_manager):
    outsider = make_user("sales.person", "employee", other_department())
    names = {e["username"] for e in as_manager.get("/api/employees").get_json()["employees"]}
    assert "employee.one" in names
    assert outsider.username not in names
    assert as_manager.get(f"/api/employees/{outsider.employee.id}").status_code == 403


def test_manager_cannot_hire_into_another_department(as_manager):
    assert as_manager.post("/api/employees", json=new_person(other_department())).status_code == 403


def test_team_lead_cannot_assign_outside_their_department(app, users, department):
    make_user("lead.user", "team_lead", department)
    outsider = make_user("sales.person", "employee", other_department())
    client = _signed_in_client(app, "lead.user")
    task = make_task(users["manager"])
    body = {"task_id": task.id, "employee_id": users["employee"].employee.id}
    assert client.post("/api/assignments", json=body).status_code == 201
    body["employee_id"] = outsider.employee.id
    assert client.post("/api/assignments", json=body).status_code == 403


# --- Auditor --------------------------------------------------------------

def test_auditor_reads_but_never_writes(app, department, users):
    make_user("audit.user", "auditor", department)
    client = _signed_in_client(app, "audit.user")
    assert client.get("/api/dashboard/activity").status_code == 200
    assert client.get("/api/employees").status_code == 200
    assert client.post("/api/tasks", json={"title": "Nope"}).status_code == 403
    assert client.post("/api/employees", json=new_person(department)).status_code == 403


def test_roles_matrix_endpoint(as_manager):
    body = as_manager.get("/api/admin/roles").get_json()
    assert [r["key"] for r in body["roles"]] == list(ROLES)
