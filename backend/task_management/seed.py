"""Populates the database with sample departments, users, and tasks.

Run via `flask --app task_management seed` (see backend/run.py for the
FLASK_APP entrypoint), or `python -m task_management.seed` from backend/.
"""
import secrets
from datetime import date, datetime

from .extensions import db
from .models import ActivityLog, Department, Employee, Task, TaskAssignment, User
from .services.passwords import hash_password as _hash


def run():
    db.drop_all()
    db.create_all()

    # --- Users & the owner account ------------------------------------
    ayush = User(username="ayush.yadav", password_hash=_hash("Ayush@123"), role="super_admin")
    admin_user = User(username="meera.nair", password_hash=_hash("Admin@123"), role="admin")
    hr_user = User(username="neha.kapoor", password_hash=_hash("Hr@12345"), role="hr")
    manager_user = User(username="priya.mehta", password_hash=_hash("Manager@123"), role="manager")
    lead_user = User(username="vikram.rao", password_hash=_hash("Lead@1234"), role="team_lead")
    auditor_user = User(username="isha.menon", password_hash=_hash("Audit@123"), role="auditor")
    emp_users = [
        User(username=name, password_hash=_hash("Employee@123"), role="employee")
        for name in ["aarav.sharma", "rohan.patel", "ananya.iyer", "kabir.singh"]
    ]
    db.session.add_all([ayush, admin_user, hr_user, manager_user, lead_user, auditor_user, *emp_users])
    db.session.flush()

    # --- Departments -----------------------------------------------------
    dept_names = ["Engineering", "Design", "Sales", "Human Resources"]
    departments = [Department(name=name, description=f"{name} department") for name in dept_names]
    db.session.add_all(departments)
    db.session.flush()
    engineering, design, sales, hr = departments

    # --- Employees ---------------------------------------------------------
    employee_seed = [
        (emp_users[0], engineering, "ENG-001", "Aarav", "Sharma", "aarav.sharma@taskforge.dev", "9876500001", "Software Engineer"),
        (emp_users[1], sales, "SAL-001", "Rohan", "Patel", "rohan.patel@taskforge.dev", "9876500002", "Sales Executive"),
        (emp_users[2], design, "DES-001", "Ananya", "Iyer", "ananya.iyer@taskforge.dev", "9876500003", "UI/UX Designer"),
        (emp_users[3], engineering, "ENG-002", "Kabir", "Singh", "kabir.singh@taskforge.dev", "9876500004", "QA Engineer"),
    ]
    employees = []
    for user, dept, code, first, last, email, phone, position in employee_seed:
        employee = Employee(
            user_id=user.id,
            department_id=dept.id,
            employee_code=code,
            first_name=first,
            last_name=last,
            email=email,
            phone=phone,
            position=position,
            hire_date=date(2024, 1, 15),
        )
        db.session.add(employee)
        employees.append(employee)

    staff_seed = [
        (admin_user, engineering, "ENG-010", "Meera", "Nair", "9876500006", "IT Administrator"),
        (hr_user, hr, "HUM-001", "Neha", "Kapoor", "9876500007", "People Partner"),
        (manager_user, engineering, "ENG-020", "Priya", "Mehta", "9876500005", "Engineering Manager"),
        (lead_user, engineering, "ENG-030", "Vikram", "Rao", "9876500008", "Tech Lead"),
        (auditor_user, hr, "HUM-002", "Isha", "Menon", "9876500009", "Compliance Auditor"),
    ]
    for user, dept, code, first, last, phone, position in staff_seed:
        db.session.add(
            Employee(
                user_id=user.id,
                department_id=dept.id,
                employee_code=code,
                first_name=first,
                last_name=last,
                email=f"{user.username}@taskforge.dev",
                phone=phone,
                position=position,
                hire_date=date(2023, 6, 1),
            )
        )
    db.session.flush()

    # --- Tasks + assignments -----------------------------------------------
    task_seed = [
        ("Design new landing page", "Create a fresh landing page design for the product relaunch", "High", 12, [(employees[2], "In Progress", 60)]),
        ("Fix login session bug", "Users are randomly logged out after 5 minutes of inactivity", "Urgent", 4, [(employees[0], "Pending", 0)]),
        ("Prepare Q3 sales report", "Compile the quarterly sales figures for leadership review", "Medium", 6, [(employees[1], "Completed", 100)]),
        ("Write regression test suite", "Add automated regression coverage for the checkout flow", "Medium", 10, [(employees[3], "In Progress", 30)]),
        ("Onboard new hires", "Set up accounts, laptops, and orientation for this month's new hires", "Low", 5, [(employees[0], "On Hold", 10)]),
    ]

    for title, description, priority, hours, assignments in task_seed:
        task = Task(
            title=title,
            description=description,
            notes="",
            priority=priority,
            estimated_hours=hours,
            created_by=ayush.id,
        )
        db.session.add(task)
        db.session.flush()

        for employee, status, pct in assignments:
            db.session.add(
                TaskAssignment(task_id=task.id, employee_id=employee.id, status=status, completion_percentage=pct)
            )

    db.session.add(
        ActivityLog(
            user_id=ayush.id,
            action="SEED",
            entity_type="system",
            entity_id=None,
            after_state={"message": "Database seeded with sample data"},
            created_at=datetime.utcnow(),
        )
    )

    db.session.commit()

    print("Seed complete.")
    print("  Admin console:  ayush.yadav / Ayush@123 (super admin), meera.nair / Admin@123 (admin)")
    print("  Workspace:      neha.kapoor / Hr@12345 (HR), priya.mehta / Manager@123 (manager),")
    print("                  vikram.rao / Lead@1234 (team lead), isha.menon / Audit@123 (auditor)")
    print("  Employee login: aarav.sharma / Employee@123 (also rohan.patel, ananya.iyer, kabir.singh)")


DEFAULT_DEPARTMENTS = [
    ("Engineering", "Builds and maintains the product"),
    ("Design", "Product design and user experience"),
    ("Sales", "Revenue, pipeline and customer accounts"),
    ("Human Resources", "Hiring, onboarding and people operations"),
    ("Operations", "Internal processes and support"),
]


def ensure_baseline(app, force=False):
    """Idempotent first-boot setup: departments plus one admin account.

    A fresh deploy otherwise has an empty department list, which leaves the
    signup form with nothing to pick and no way to create the first user.
    Returns a human-readable note when it creates the admin, else None.
    """
    created = []

    if not Department.query.first():
        db.session.add_all(
            Department(name=name, description=description)
            for name, description in DEFAULT_DEPARTMENTS
        )
        db.session.commit()
        created.append(f"{len(DEFAULT_DEPARTMENTS)} departments")

    existing_admin = User.query.filter(User.role.in_(("super_admin", "admin"))).first()
    if existing_admin and not force:
        if created:
            app.logger.info("Bootstrap created: %s", ", ".join(created))
        return None
    if existing_admin:
        return f"Admin account already exists: {existing_admin.username}"

    username = app.config["BOOTSTRAP_ADMIN_USERNAME"]
    password = app.config.get("BOOTSTRAP_ADMIN_PASSWORD")
    generated = password is None
    if generated:
        # Never ship a hard-coded production password. If the operator didn't
        # supply one, mint a random password and print it exactly once.
        password = secrets.token_urlsafe(12)

    admin = User(username=username, password_hash=_hash(password), role="super_admin")
    db.session.add(admin)
    db.session.commit()

    note = f"Created admin '{username}'"
    if generated:
        note += f" with generated password: {password}"
        app.logger.warning(
            "BOOTSTRAP ADMIN CREATED — username=%s password=%s "
            "(set BOOTSTRAP_ADMIN_PASSWORD to choose your own, then change it after first login)",
            username,
            password,
        )
    return note


if __name__ == "__main__":
    from . import create_app

    app = create_app()
    with app.app_context():
        run()
