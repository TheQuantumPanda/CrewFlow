"""Role → permission map. The one place that decides who can do what.

Routes ask `can(role, "tasks.manage")` instead of listing role names, so adding
a role means editing this file and nothing else. The same map is sent to the
SPA on `/me`, which is how the UI hides what the server would refuse anyway.
"""

ROLES = ("super_admin", "admin", "hr", "manager", "team_lead", "employee", "auditor")

# Rank decides two things: which roles you may grant (strictly lower only) and
# whose account you may change (strictly lower only). Auditor sits beside HR:
# read-everything power is not something HR or a manager should hand out.
LEVEL = {
    "super_admin": 6,
    "admin": 5,
    "hr": 4,
    "auditor": 4,
    "manager": 3,
    "team_lead": 2,
    "employee": 1,
}

ROLE_LABELS = {
    "super_admin": "Super admin",
    "admin": "Admin",
    "hr": "HR",
    "manager": "Manager",
    "team_lead": "Team lead",
    "employee": "Employee",
    "auditor": "Auditor",
}

# Roles whose people/assignment reach stops at their own department.
DEPARTMENT_SCOPED = frozenset({"manager", "team_lead"})

# Roles that must come in through the admin console door.
CONSOLE_ROLES = frozenset({"super_admin", "admin"})

_ALL = set(ROLES)
_STAFF = {"super_admin", "admin"}

PERMISSIONS = {
    "dashboard.view": _ALL - {"employee"},
    "tasks.manage": _STAFF | {"manager", "team_lead"},
    "tasks.delete": _STAFF | {"manager"},
    "assignments.manage": _STAFF | {"manager", "team_lead"},
    "assignments.view_all": _STAFF | {"manager", "team_lead", "auditor"},
    "people.view": _ALL - {"employee"},
    "people.manage": _STAFF | {"hr", "manager"},
    "departments.manage": _STAFF | {"hr"},
    "audit.view": _STAFF | {"auditor"},
    "console.access": set(CONSOLE_ROLES),
}

PERMISSION_LABELS = {
    "dashboard.view": "See the workspace dashboard",
    "tasks.manage": "Create and edit tasks",
    "tasks.delete": "Delete tasks",
    "assignments.manage": "Assign and unassign work",
    "assignments.view_all": "See everyone's assignments",
    "people.view": "Browse the people directory",
    "people.manage": "Add, edit, deactivate and re-role people",
    "departments.manage": "Create departments",
    "audit.view": "Read the audit log",
    "console.access": "Sign in to the admin console",
}


def can(role, permission):
    return role in PERMISSIONS.get(permission, ())


def permissions_for(role):
    return sorted(p for p, roles in PERMISSIONS.items() if role in roles)


def outranks(actor_role, target_role):
    return LEVEL.get(actor_role, 0) > LEVEL.get(target_role, 0)


def grantable_roles(role):
    """Roles this role may hand out: people managers only, and strictly below
    their own rank, so nobody can mint a peer or a superior."""
    if not can(role, "people.manage"):
        return []
    return [r for r in ROLES if outranks(role, r)]


def is_department_scoped(role):
    return role in DEPARTMENT_SCOPED


def matrix():
    """The whole map, shaped for the roles screen."""
    return {
        "roles": [
            {"key": r, "label": ROLE_LABELS[r], "level": LEVEL[r], "scoped": r in DEPARTMENT_SCOPED}
            for r in ROLES
        ],
        "permissions": [
            {"key": p, "label": PERMISSION_LABELS[p], "roles": sorted(PERMISSIONS[p])}
            for p in PERMISSIONS
        ],
    }
