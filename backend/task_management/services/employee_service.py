from datetime import date

from ..extensions import db
from ..models import Department, Employee, User
from ..permissions import ROLE_LABELS, ROLES, is_department_scoped, outranks
from .activity_service import log as log_activity
from .errors import AuthError, EmployeeError
from .passwords import hash_password, validate_password

REQUIRED_FIELDS = ["department_id", "employee_code", "first_name", "last_name", "email", "phone"]


def authorize_people_change(actor, department_id=None, target=None, new_role=None):
    """The rank and scope rules for touching someone's account. Raises 403.

    * you may only act on people who rank strictly below you,
    * you may only grant roles that rank strictly below you,
    * a manager or team lead stays inside their own department.
    """
    if target is not None:
        target_role = target.user.role if target.user else "employee"
        if not outranks(actor.role, target_role):
            raise EmployeeError("You can only manage people below your own role", 403)
        department_id = department_id or target.department_id

    if new_role is not None:
        if new_role not in ROLES:
            raise EmployeeError(f"Role must be one of: {', '.join(ROLES)}")
        if not outranks(actor.role, new_role):
            raise EmployeeError(f"You cannot grant the {ROLE_LABELS[new_role]} role", 403)

    if is_department_scoped(actor.role):
        own = actor.employee.department_id if actor.employee else None
        departments = {department_id, target.department_id if target is not None else department_id}
        if own is None or any(_as_int(d) != own for d in departments):
            raise EmployeeError("You can only manage people in your own department", 403)


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _missing_fields(fields):
    return [f for f in REQUIRED_FIELDS if not fields.get(f)]


def generate_employee_code(department_id):
    """Builds the next free code for a department, e.g. Engineering -> ENG-003."""
    department = db.session.get(Department, department_id)
    raw = (department.name if department else "EMP") or "EMP"
    prefix = "".join(ch for ch in raw if ch.isalpha())[:3].upper() or "EMP"

    highest = 0
    for employee in Employee.query.filter(Employee.employee_code.like(f"{prefix}-%")).all():
        suffix = employee.employee_code[len(prefix) + 1 :]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{prefix}-{highest + 1:03d}"


def create_employee(fields, actor_id):
    missing = _missing_fields(fields)
    if missing:
        verb = "are" if len(missing) > 1 else "is"
        raise EmployeeError(f"{', '.join(missing)} {verb} required")

    department = db.session.get(Department, fields.get("department_id"))
    if not department:
        raise EmployeeError("department_id does not exist")
    if Employee.query.filter_by(employee_code=fields["employee_code"]).first():
        raise EmployeeError("employee_code already in use")
    if Employee.query.filter_by(email=fields["email"]).first():
        raise EmployeeError("email already in use")

    user_id = fields.get("user_id")

    if user_id:
        user = db.session.get(User, user_id)
        if not user:
            raise EmployeeError("user_id does not exist")
        if Employee.query.filter_by(user_id=user_id).first():
            raise EmployeeError("This user already has an employee profile")
    else:
        username = fields.get("username")
        password = fields.get("password")
        if not username or not password:
            raise EmployeeError("username and password are required to create the employee's login")
        try:
            validate_password(password)
        except AuthError as err:
            raise EmployeeError(err.message) from err
        if User.query.filter_by(username=username).first():
            raise EmployeeError("That username is already taken")

        role = fields.get("role") or "employee"
        if role not in ROLES:
            raise EmployeeError(f"Role must be one of: {', '.join(ROLES)}")
        user = User(username=username, password_hash=hash_password(password), role=role)
        db.session.add(user)
        db.session.flush()  # assigns user.id without a full commit
        user_id = user.id

    employee = Employee(
        user_id=user_id,
        department_id=fields["department_id"],
        employee_code=fields["employee_code"],
        first_name=fields["first_name"],
        last_name=fields["last_name"],
        email=fields["email"],
        phone=fields["phone"],
        position=fields.get("position") or fields.get("job_title") or "",
        hire_date=fields.get("hire_date") or date.today(),
    )
    db.session.add(employee)
    db.session.commit()

    log_activity(actor_id, "CREATE", "employee", employee.id, None, employee.to_dict())
    return employee


def get_employee(employee_id):
    employee = db.session.get(Employee, employee_id)
    if not employee:
        raise EmployeeError("Employee not found", 404)
    return employee


def update_employee(employee_id, fields, actor_id):
    employee = db.session.get(Employee, employee_id)
    if not employee:
        raise EmployeeError("Employee not found", 404)

    before = employee.to_dict()
    patch = dict(fields)
    if patch.get("job_title") and not patch.get("position"):
        patch["position"] = patch["job_title"]
    patch.pop("job_title", None)
    patch.pop("id", None)
    patch.pop("user_id", None)

    if patch.get("department_id") and not db.session.get(Department, patch["department_id"]):
        raise EmployeeError("department_id does not exist")

    for key in ["department_id", "employee_code", "first_name", "last_name", "email", "phone", "position", "hire_date"]:
        if key in patch and patch[key] is not None:
            setattr(employee, key, patch[key])

    db.session.commit()
    log_activity(actor_id, "UPDATE", "employee", employee.id, before, employee.to_dict())
    return employee


def delete_employee(employee_id, actor_id):
    employee = db.session.get(Employee, employee_id)
    if not employee:
        raise EmployeeError("Employee not found", 404)

    before = employee.to_dict()
    employee.is_active = False
    if employee.user:
        employee.user.is_active = False
    db.session.commit()
    log_activity(actor_id, "DELETE", "employee", employee_id, before, None)
    return True


def change_role(employee_id, new_role, actor_id):
    employee = get_employee(employee_id)
    if not employee.user:
        raise EmployeeError("This person has no login to re-role")
    old_role = employee.user.role
    if old_role == new_role:
        return employee

    employee.user.role = new_role
    db.session.commit()
    log_activity(actor_id, "ROLE_CHANGE", "user", employee.user.id, {"role": old_role}, {"role": new_role})
    return employee


def unlock(employee_id, actor_id):
    employee = get_employee(employee_id)
    if employee.user:
        employee.user.failed_login_count = 0
        employee.user.locked_until = None
        db.session.commit()
        log_activity(actor_id, "UNLOCK", "user", employee.user.id)
    return employee


def list_employees_by_department(department_id):
    employees = Employee.query.filter_by(department_id=department_id, is_active=True).all()
    return employees


def list_employees(department_id=None):
    query = Employee.query.filter_by(is_active=True)
    if department_id is not None:
        query = query.filter_by(department_id=department_id)
    return query.all()


def list_departments():
    return Department.query.all()


def create_department(fields, actor_id):
    name = (fields.get("name") or "").strip()
    if not name:
        raise EmployeeError("Department name is required")
    if Department.query.filter(db.func.lower(Department.name) == name.lower()).first():
        raise EmployeeError("A department with that name already exists")

    department = Department(name=name, description=fields.get("description") or "")
    db.session.add(department)
    db.session.commit()
    log_activity(actor_id, "CREATE", "department", department.id, None, department.to_dict())
    return department
