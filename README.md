# CrewFlow

**Keep teams and work in sync.**

CrewFlow is a workforce and task-management platform with role-based workspaces, department-scoped management, task ownership and progress tracking. It has an original connected-path identity, a navy and indigo interface, and consistent light and dark themes.

## Screenshots

These are actual browser captures of the finished interface using **temporary fictional API fixtures**. They demonstrate presentation, not live database contents, backend authorization or persistence. Desktop captures use a 1440 × 1000 viewport; the mobile capture uses 390 × 844. No credentials are shown.

<table>
<tr><td width="50%"><img src="docs/screenshots/crewflow/mock-overview-light.png" alt="CrewFlow overview in light theme, fictional data"><br>Overview · light</td><td width="50%"><img src="docs/screenshots/crewflow/mock-overview-dark.png" alt="CrewFlow overview in dark theme, fictional data"><br>Overview · dark</td></tr>
<tr><td><img src="docs/screenshots/crewflow/mock-kanban-light.png" alt="CrewFlow populated Kanban board in light theme, fictional data"><br>Kanban · light</td><td><img src="docs/screenshots/crewflow/mock-kanban-dark.png" alt="CrewFlow populated Kanban board in dark theme, fictional data"><br>Kanban · dark</td></tr>
<tr><td><img src="docs/screenshots/crewflow/mock-task-list.png" alt="CrewFlow task list, fictional data"><br>Task list</td><td><img src="docs/screenshots/crewflow/mock-people.png" alt="CrewFlow people directory, fictional data"><br>People</td></tr>
<tr><td><img src="docs/screenshots/crewflow/mock-departments.png" alt="CrewFlow departments and members, fictional data"><br>Departments</td><td><img src="docs/screenshots/crewflow/mock-audit.png" alt="CrewFlow connected audit history, fictional data"><br>Audit history</td></tr>
<tr><td><img src="docs/screenshots/crewflow/mock-roles.png" alt="CrewFlow role hierarchy and permission matrix, fictional data"><br>Roles and permissions</td><td align="center"><img src="docs/screenshots/crewflow/mock-mobile-my-tasks.png" alt="CrewFlow My Tasks on mobile, fictional data" width="300"><br>My Tasks · mobile</td></tr>
</table>

[More screen captures](docs/SCREENSHOTS.md) · [Final verification and readiness report](docs/VERIFICATION.md)

## Features

- Seven existing roles: super admin, admin, HR, manager, team lead, employee and auditor. Capabilities follow the server's permission map.
- Department-scoped people and assignment management for managers and team leads; employees view and update their own assignments.
- Task creation and editing, eligible employee assignment, priority, descriptions, notes, optional estimated hours, and assignment status/progress updates.
- Five-column assignment Kanban with native desktop drag-and-drop, plus a task list with search, priority filtering and sorting by title, priority or update time.
- Overview and My Tasks summaries calculated from the existing API data.
- People and department management, account deactivation/unlocking, confirmed role changes and a read-only permission matrix where permitted.
- Activity history with existing action filters, actor/timestamp information and a connected timeline. Backend audit records contain before/after data; the UI displays existing summaries and selected titles/names, **not a full snapshot viewer**.
- Command palette at **Ctrl/Cmd + K**, existing `g`-then-key navigation shortcuts, theme switching, account details and password updates.
- Separate administrative sign-in with the existing console access restrictions and idle-session policy.

Board filtering is independent of task-list filtering. There is no calendar, due-date management, messaging, advanced analytics, or separate touch/keyboard drag implementation. The task API supports paging, but the current task-list request fetches at most 200 records and the UI has no page controls.

## Technology and architecture

| Layer | Implementation |
| --- | --- |
| Frontend | React 18, TypeScript, Vite 6.4.5, React Router 7.18.5, TanStack Query 5, Lucide icons |
| Styling | Existing CSS token system; locally bundled Manrope, Bricolage Grotesque and JetBrains Mono |
| Backend | Flask 3.1.3, Gunicorn 26.2.0, Flask-SQLAlchemy, SQLAlchemy 2, Flask-Migrate/Alembic, Werkzeug password hashing |
| Database | SQLite for unit tests/local use; PostgreSQL 17 verified with Psycopg-C 3.3.8; existing MySQL support |
| Verification | Vitest, Testing Library, pytest, pytest-cov, Ruff and local Playwright browser inspection |

`web/src/pages` contains route presentations; `layout` and `components` provide navigation, dialogs and shared controls. Typed requests and server state remain in `web/src/api`. Flask routes under `backend/task_management/routes` delegate to services and SQLAlchemy models. Server-side permissions and department predicates enforce access; browser guards only control navigation presentation. Session cookies and the existing CSRF mechanism are retained. Flask can serve the compiled SPA from `web/dist`; development uses Vite's API proxy.

## Local setup

Use **Python 3.12** (reviewed 3.12.16), **Node.js 24.21.0** and npm with the existing lockfile. Psycopg-C requires a C compiler, matching Python development headers, libpq development headers and `pg_config`. On Debian/Ubuntu these normally come from `build-essential`, `python3-dev` and `libpq-dev`; installing system packages requires your own approved environment. Other operating systems must provide equivalent native prerequisites. The reviewed production container targets linux/amd64; other platforms are not verified.

Create an isolated backend environment from the project root using verified pip 26.3, without the older ensurepip bootstrap archive:

```bash
python3.12 tools/ci/python_env.py backend/.venv --wheel output/tools/pip-26.3-py3-none-any.whl --download
source backend/.venv/bin/activate
python -m pip install --build-constraint tools/ci/build-constraints.txt -r backend/requirements-dev.txt
cp backend/.env.example backend/.env
cd backend
```

Edit the private `.env` before startup: choose an explicitly authorized development database, private `SECRET_KEY`, `AUTO_BOOTSTRAP=0` unless initialization is approved, and an explicit private `BOOTSTRAP_ADMIN_PASSWORD` if creating the first administrator. Never commit this file. The bootstrap helper downloads only the checksum-pinned official pip wheel into the ignored output directory; it does not initialize a database. The reviewed native build constraints are build-only; see [native runtime details](docs/production-runtime.md).

**Startup can write to the database.** The existing `AUTO_BOOTSTRAP` default applies migrations and creates baseline departments/an initial admin on an empty database. Use that only for an explicitly authorized local database. Set `AUTO_BOOTSTRAP=0` when automatic initialization must be disabled. The `seed` CLI drops and recreates the demo database; it is deliberately excluded from this quick start. Existing accounts are not assumed to exist, and no credentials are published here.

Start the API in the backend terminal:

```bash
python run.py
```

In another terminal, from the project root:

```bash
cd web
npm ci
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://127.0.0.1:5000` by default. Use accounts authorized for your chosen development environment. New initial administrator provisioning requires the private configured password; passwords are not generated or printed by that command. Keep all credentials out of screenshots and reports.

To compile the frontend locally:

```bash
cd web
npm run build
```

This produces `web/dist`; it does not deploy the application. [Development details](docs/DEVELOPMENT.md).

## Environment configuration

`SECRET_KEY` is mandatory in production, and an explicit private `BOOTSTRAP_ADMIN_PASSWORD` is required for a new initial administrator. Production workers require reviewed `DATABASE_URL` and `AUTO_BOOTSTRAP=0`; inspect database selection before any startup. The application retains its established internal configuration names.

| Variables | Purpose |
| --- | --- |
| `APP_ENV`, `FLASK_ENV` | Configuration selection; development is the default. `FLASK_ENV` also affects the dev runner's debug behavior. |
| `SECRET_KEY` | Session-signing secret; keep private and stable. |
| `DATABASE_URL` | Explicit database URL; takes precedence over `DB_*`. Without it or MySQL settings, SQLite stores its file under `backend/instance/`. |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Existing alternative MySQL configuration. |
| `AUTO_BOOTSTRAP`, `BOOTSTRAP_ADMIN_USERNAME`, `BOOTSTRAP_ADMIN_PASSWORD` | Existing migration/baseline initialization and initial-account settings. |
| `MIN_PASSWORD_LENGTH`, `MAX_FAILED_LOGINS`, `LOCKOUT_MINUTES` | Existing password and lockout policy. |
| `ADMIN_IDLE_MINUTES`, `SESSION_LIFETIME_SECONDS` | Console idle timeout and session lifetime. |
| `PORT` | Flask development runner port. |
| `VITE_API_TARGET` | Vite development proxy target. |
| `VITE_DEMO_MODE` | Optional demonstration-account presentation; disabled unless explicitly enabled. |
| `WEB_CONCURRENCY`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`, `LOG_LEVEL` | Existing Gunicorn worker/log settings; no hosting changes were made. |

See [backend/.env.example](backend/.env.example) for the existing template. Do not copy private values into documentation.

## Tests and verification

From `web/`:

```bash
npm run typecheck
npm run test
npm run build
```

From `backend/`, with the development requirements installed:

```bash
ruff check .
pytest -q --cov=task_management --cov-report=term-missing
```

Accepted local security work on **2026-11-05** includes **136 backend tests (82% coverage)**, **82 frontend tests**, TypeScript/build/Ruff, real isolated PostgreSQL integration and least-privilege roles, and actual production HTTPS/browser verification. Ordinary backend tests use Flask test clients and in-memory SQLite; the PostgreSQL and HTTPS campaigns are separate evidence. The selected screenshot gallery remains mock-data captures.

The accepted image has zero reported installed Python and npm full/runtime audit findings at the recorded snapshot. Its OS/native scan still reports **51 High package entries across 13 High IDs**, plus six Unknown IDs and an inactive ensurepip pip archive with six disclosed advisories. These are not owner-approved residual risks. [Verification](docs/VERIFICATION.md), [release policy](docs/release-assurance.md) and the [decision register](docs/security-decisions.json) distinguish historical acceptance, local CI-equivalent checks and remaining release gates. Hosted GitHub Actions has **not** been verified.

## Limitations and readiness

**CONDITIONAL release readiness.** Security fixes and local integration evidence are available, but public deployment remains blocked on explicit residual-risk disposition, hosted CI on the reviewed source, and hosted ingress/database/recovery checks. Local acceptance is not public-deployment approval or security certification. The modal return-focus defect was corrected and regression-tested in Stage 2D.

- Native drag-and-drop has no separate touch or keyboard implementation.
- Dense tables and Kanban columns scroll inside their containers on smaller screens.
- Board and list filters are independent; some screens have no pagination controls.
- Audit details remain summaries rather than an expandable full before/after viewer.
- Management request failures now display load-error messages rather than misleading empty states. Missing department-member data is marked unavailable; existing request/retry behavior is unchanged.

[Final evidence, workflow status and remaining limitations](docs/VERIFICATION.md).

## License and attribution

The applicable MIT terms and copyright notice are preserved in [LICENSE](LICENSE), including the permission and warranty notices.

The CrewFlow three-path C mark is original SVG geometry. Runtime library and font notices are preserved in [web/public/third-party-notices.txt](web/public/third-party-notices.txt), which is copied into frontend build output. Fonts retain their SIL Open Font License texts; Lucide retains its ISC notice, including the upstream third-party material included in that package's license file.
