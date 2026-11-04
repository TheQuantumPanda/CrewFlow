<div align="center">

# 🏛 Architecture

**[← Back to README](../README.md)** · [Security](SECURITY.md) · [API](API.md) · [Development](DEVELOPMENT.md) · [Screenshots](SCREENSHOTS.md) · [Deployment](../DEPLOYMENT.md)

</div>

---

## The shape of it

One repository, two halves, one deployed container.

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#fff4ee','primaryTextColor':'#1c1917','primaryBorderColor':'#e8572a','lineColor':'#a8a29e','fontFamily':'ui-sans-serif, system-ui, sans-serif','fontSize':'14px'}}}%%
flowchart TB
    subgraph web["📦  web/ — React SPA"]
        direction TB
        PAGES["<b>pages/</b><br/>one file per screen"]
        LAYOUT["<b>layout/</b><br/>app shell · nav"]
        AUTHC["<b>auth/</b><br/>session context<br/>route guards"]
        APIC["<b>api/</b><br/>typed client<br/>TanStack Query hooks"]
        COMP["<b>components/</b><br/>Modal · Toast · Palette"]
        TOK["<b>styles/tokens.css</b><br/>colour · type · space"]
        PAGES --> COMP --> TOK
        PAGES --> APIC
        LAYOUT --> AUTHC --> APIC
    end

    subgraph api["🐍  backend/ — Flask API"]
        direction TB
        SEC["<b>security.py</b><br/>CSRF · CSP · request id"]
        DEC["<b>auth_decorators.py</b><br/>login_required<br/>permission_required"]
        ROUTES["<b>routes/</b><br/>8 blueprints under /api"]
        SVC["<b>services/</b><br/>business rules"]
        PERM["<b>permissions.py</b><br/>role → permission"]
        MOD["<b>models/</b><br/>5 tables + audit log"]
        SEC --> DEC --> ROUTES --> SVC --> MOD
        DEC -.-> PERM
        SVC -.-> PERM
    end

    DB[("PostgreSQL · MySQL · SQLite")]

    APIC ==>|"/api/* · cookie + CSRF header"| SEC
    MOD --> DB

    classDef front fill:#fff4ee,stroke:#e8572a,stroke-width:2px,color:#1c1917
    classDef back fill:#eef6ff,stroke:#3b82f6,stroke-width:2px,color:#1c1917
    classDef guard fill:#fef6e7,stroke:#f59e0b,stroke-width:2px,color:#1c1917
    classDef data fill:#ecfdf5,stroke:#14b8a6,stroke-width:2px,color:#1c1917

    class PAGES,LAYOUT,AUTHC,APIC,COMP,TOK front
    class SEC,ROUTES,SVC,MOD back
    class DEC,PERM guard
    class DB data
```

### Why one origin

In production Flask serves the compiled Vite bundle itself, with an
`index.html` fallback so client-side routes survive a hard refresh or a shared
deep link. The SPA and the API therefore share an origin, which buys three
things:

- the session cookie is **first-party**, so no CORS configuration exists to get wrong,
- there is **no access token in `localStorage`** for an injected script to read,
- dev matches prod — Vite proxies `/api` to port 5000 rather than pointing at a
  different host.

---

## Layering rule

> A route handler parses the request, calls a service, and shapes the response.
> Nothing else.

Every business rule lives in `services/`. That is why the same validation
applies whether a task arrives through the API, the seed script, or the Flask
CLI — there is exactly one code path that can create one.

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#fff4ee','primaryTextColor':'#1c1917','primaryBorderColor':'#e8572a','lineColor':'#a8a29e','fontFamily':'ui-sans-serif, system-ui, sans-serif'}}}%%
flowchart LR
    A["<b>routes/</b><br/><br/>parse JSON<br/>call one service<br/>jsonify the result"]
    B["<b>services/</b><br/><br/>validate<br/>authorize the object<br/>mutate<br/>write the audit row"]
    C["<b>models/</b><br/><br/>columns<br/>relationships<br/>serialisers"]

    A -->|"typed args"| B
    B -->|"ORM"| C
    C -.->|"domain object"| B
    B -.->|"dict"| A

    classDef r fill:#eef6ff,stroke:#3b82f6,stroke-width:2px,color:#1c1917
    classDef s fill:#fff4ee,stroke:#e8572a,stroke-width:2px,color:#1c1917
    classDef m fill:#ecfdf5,stroke:#14b8a6,stroke-width:2px,color:#1c1917
    class A r
    class B s
    class C m
```

`services/errors.py` defines the domain errors. A service raises one; the error
handler turns it into a status code. No route builds an error response by hand,
so the API answers consistently no matter which endpoint failed.

---

## Request lifecycle

What actually happens between a click and a row changing.

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#fff4ee','primaryTextColor':'#1c1917','primaryBorderColor':'#e8572a','lineColor':'#e8572a','actorBkg':'#fff4ee','actorBorder':'#e8572a','actorTextColor':'#1c1917','signalColor':'#57534e','signalTextColor':'#1c1917','labelBoxBkgColor':'#fef6e7','labelBoxBorderColor':'#f59e0b','noteBkgColor':'#ecfdf5','noteBorderColor':'#14b8a6','fontFamily':'ui-sans-serif, system-ui, sans-serif'}}}%%
sequenceDiagram
    autonumber
    participant U as 🖥 SPA
    participant S as 🛡 security.py
    participant G as 🔑 decorators
    participant R as 🔌 route
    participant V as ⚙️ service
    participant D as 🗄 database

    U->>S: PUT /api/tasks/7<br/>Cookie: session, csrf_token<br/>X-CSRF-Token: …
    S->>S: assign request id
    S->>S: compare_digest(header, cookie)
    alt token missing or mismatched
        S-->>U: 403 Invalid or missing CSRF token
    end
    S->>G: continue
    G->>D: SELECT user WHERE id = session.user_id
    D-->>G: user row
    G->>G: re-read role · check active · console door
    alt not permitted
        G-->>U: 401 / 403
    end
    G->>R: g.current_user is set
    R->>V: update_task(actor, 7, payload)
    V->>V: validate fields · check department scope
    V->>D: UPDATE tasks SET … · commit
    V->>D: INSERT activity_logs (before, after) · commit
    D-->>V: written
    V-->>R: task dict
    R-->>S: 200 + JSON
    S->>S: CSP · HSTS · X-Request-ID · refresh CSRF cookie
    S-->>U: response
    Note over U,D: TanStack Query invalidates the task list<br/>and the dashboard, both refetch
```

Two details worth calling out:

- **The role is re-read from the database on every request.** Caching it in the
  session means a demotion takes effect whenever the cookie happens to expire.
  One indexed lookup makes it bind immediately.
- **The audit row is written by the service, not the route.** `services/` owns
  the `log(actor, action, entity, before, after)` call, so a mutation reached
  through the seed script or the CLI is logged exactly like one that came over
  HTTP. The log is a straight append — nothing updates or deletes a row in
  `activity_logs`.

---

## Data model

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#fff4ee','primaryTextColor':'#1c1917','primaryBorderColor':'#e8572a','lineColor':'#e8572a','fontFamily':'ui-sans-serif, system-ui, sans-serif'}}}%%
erDiagram
    USERS ||--o| EMPLOYEES : "profile"
    DEPARTMENTS ||--o{ EMPLOYEES : "contains"
    USERS ||--o{ TASKS : "created_by"
    TASKS ||--o{ TASK_ASSIGNMENTS : "is assigned as"
    EMPLOYEES ||--o{ TASK_ASSIGNMENTS : "works on"
    USERS ||--o{ ACTIVITY_LOGS : "acted"

    USERS {
        int id PK
        string username UK "indexed"
        string password_hash "scrypt"
        enum role "7 roles"
        bool is_active
        int failed_login_count "lockout counter"
        datetime locked_until
        datetime last_login_at
        datetime created_at
    }

    EMPLOYEES {
        int id PK
        int user_id FK "unique, CASCADE"
        int department_id FK "RESTRICT"
        string employee_code UK
        string first_name
        string last_name
        string email UK
        string phone
        string position
        date hire_date
        bool is_active
    }

    DEPARTMENTS {
        int id PK
        string name UK
        string description
    }

    TASKS {
        int id PK
        string title
        text description
        text notes
        enum priority "Low Medium High Urgent"
        numeric estimated_hours
        int created_by FK
        bool is_deleted "soft delete"
        datetime created_at
        datetime updated_at
    }

    TASK_ASSIGNMENTS {
        int id PK
        int task_id FK "CASCADE"
        int employee_id FK "CASCADE"
        enum status "Pending InProgress Completed OnHold Cancelled"
        int completion_percentage "0-100"
        text remarks
        datetime assigned_at
        datetime updated_at
    }

    ACTIVITY_LOGS {
        int id PK
        int user_id FK "nullable - system actions"
        string action
        string entity_type
        int entity_id
        json before_state
        json after_state
        datetime created_at
    }
```

**Design choices in that diagram:**

| Choice | Why |
|---|---|
| `users` and `employees` are separate tables | A login is not a person. The seed's system actor and a bootstrap admin have no employee profile, and deactivating a login should not delete an HR record. |
| `department_id` is `RESTRICT`, not `CASCADE` | Deleting a department must not silently take its people with it. |
| `tasks.is_deleted` is a soft delete | The audit log references task ids. A hard delete would leave dangling history. |
| Status lives on the **assignment**, not the task | Two people on one task can be at different stages; the task's own progress is derived. |
| `before_state` / `after_state` are JSON | The log survives schema changes — it records what the row looked like, not a foreign key into a shape that may no longer exist. |

---

## Module map

```
backend/
  task_management/
    __init__.py          app factory, SPA handler, error handlers, first-boot bootstrap
    config.py            env-driven; normalises postgres:// and mysql:// URLs
    extensions.py        db, migrate — importable without circular imports
    permissions.py       ROLES, LEVEL, PERMISSIONS — the single source of truth
    auth_decorators.py   login_required, permission_required, department scoping
    security.py          CSRF, response headers, request id, request log
    seed.py              destructive demo reset; baseline bootstrap is separate
    models/              user · employee · department · task · task_assignment · activity_log
    routes/              health · auth · task · employee · department · assignment · dashboard · admin
    services/            auth · task · assignment · employee · activity · passwords · errors
  migrations/            Alembic — the source of truth for schema
  tests/                 auth · authorization · config · roles · security · tasks
  gunicorn.conf.py       worker count, timeouts, access log format

web/
  src/
    api/                 typed fetch client + TanStack Query hooks (and their tests)
    auth/                AuthContext, ProtectedRoute, PublicOnlyRoute
    components/          Modal, Toast, ConfirmDialog, CommandPalette, primitives
    layout/              AppShell — the single source of truth for navigation
    pages/               Overview, Tasks, MyTasks, Employees, Departments, Activity,
                         Profile, Login, AdminLogin, AdminPeople, AdminRoles, Signup
    styles/              tokens.css, base.css, components.css, lively.css
    lib/                 formatting helpers (and their tests)
    theme.tsx            light/dark, persisted, honours prefers-color-scheme

database/schema.sql      the original hand-written MySQL schema, kept for reference
Dockerfile               two-stage: Node builds, Python serves
render.yaml              one-click Render blueprint
railway.toml             Railway build + health check config
docker-compose.yml       local Postgres for development
```

---

## Front-end data flow

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#fff4ee','primaryTextColor':'#1c1917','primaryBorderColor':'#e8572a','lineColor':'#a8a29e','fontFamily':'ui-sans-serif, system-ui, sans-serif'}}}%%
flowchart LR
    P["<b>Page</b><br/>useTasks()"]
    H["<b>api/hooks</b><br/>useQuery / useMutation"]
    C["<b>api/client</b><br/>fetch + CSRF header<br/>401 → signed out"]
    Q[("<b>Query cache</b><br/>keyed by resource")]
    A["<b>AuthContext</b><br/>user · permissions"]
    G["<b>ProtectedRoute</b><br/>redirect if not allowed"]

    P --> H --> C
    H <--> Q
    C -->|"/api/auth/me"| A
    A --> G --> P
    H -.->|"on success: invalidate"| Q

    classDef f fill:#fff4ee,stroke:#e8572a,stroke-width:2px,color:#1c1917
    classDef s fill:#eef6ff,stroke:#3b82f6,stroke-width:2px,color:#1c1917
    classDef d fill:#ecfdf5,stroke:#14b8a6,stroke-width:2px,color:#1c1917
    class P,G f
    class H,C,A s
    class Q d
```

Server state lives in TanStack Query and nowhere else — there is no Redux store
mirroring rows the server already owns. A mutation invalidates the keys it
affected and the affected screens refetch.

**Signed-out is modelled as data.** `/api/auth/me` resolving to `null` is a
successful answer, not a missing one. Modelling it as *absent* is what made
logout race its own redirect: the guard read the last known user for one render
and bounced straight back to the dashboard.

**Permissions come from the server.** `/api/auth/me` returns the user's own
permission list, and the UI hides what the server would refuse anyway. The guards
are UX, not security — [Security](SECURITY.md) covers where the real check lives.

---

## Performance notes

| Problem | Fix |
|---|---|
| Task list ran one `COUNT` per task to show assignment counts | One `GROUP BY` joined into the list query |
| Dashboard loaded every assignment row into Python to tally statuses | One `GROUP BY status` aggregate |
| Session user re-queried by each decorator in the chain | `login_required` resolves it once and parks it on `g` |
| Font files fetched from a CDN on first paint | Self-hosted through `@fontsource-variable`, so the strict CSP needs no `font-src` exception and there is no third-party request |

---

<div align="center">

**[← README](../README.md)** · **[Security & RBAC →](SECURITY.md)**

</div>
