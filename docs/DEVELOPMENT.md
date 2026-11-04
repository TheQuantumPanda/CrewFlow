# CrewFlow development

[Project introduction and canonical setup](../README.md) · [API reference](API.md) · [Security architecture](SECURITY.md) · [Screenshots](SCREENSHOTS.md)

Use Python 3.11 or 3.12 and Node.js 20+. Pass 5 used Python 3.11; the existing CI targets 3.12. This project retains the original Flask/SQLAlchemy backend and React/Vite frontend. Internal package names, cookie names, environment variables and module paths intentionally retain TaskForge identifiers.

## Local startup

Follow the [README setup instructions](../README.md#local-setup) to create a backend virtual environment, install the existing `requirements-dev.txt`, configure `backend/.env` and install frontend packages with `npm ci`.

From `backend/`, with its environment activated:

```bash
python run.py
```

From `web/`, in another terminal:

```bash
npm run dev
```

The browser uses port 5173; Vite proxies `/api` to port 5000 unless `VITE_API_TARGET` is set. No database server is required for a deliberately chosen fresh local SQLite environment. Existing PostgreSQL/MySQL support is configured through `DATABASE_URL` or the original `DB_*` variables; those engines were not live-tested in the customization sprint.

## Database safety

Inspect configuration before starting the backend. With `AUTO_BOOTSTRAP` enabled by default, application startup invokes Alembic upgrades and creates baseline departments/an initial admin when needed. Disable it with `AUTO_BOOTSTRAP=0` when automatic writes are not authorized. Do not point this flow at production data.

The `seed` command **drops and recreates tables** before loading demonstration records. The previous guide incorrectly described it as idempotent. It is not part of the ordinary quick start and must not be run against data that needs to be preserved. Initialization, migration and reseeding were not performed during Pass 5.

Use authorized local accounts. Initial-account credentials, session keys and connection values must remain private; no actual values are included in this guide. Sign-in pages only show the optional original demonstration-account presentation when explicitly enabled with `VITE_DEMO_MODE`.

## Existing checks

Run from `web/`:

```bash
npm run typecheck
npm run test
npm run build
```

Run from `backend/`, after installing its development requirements:

```bash
ruff check .
pytest -q --cov=task_management --cov-report=term-missing
```

The backend's `pytest.ini` selects `tests/`. Fixtures create and remove fresh in-memory SQLite schemas per test and use Flask test clients. This deliberately isolated test suite does not require an existing database and is distinct from verifying an actual running backend with persistent development data.

On 2026-11-04, the existing suites passed: 27 frontend tests, 89 backend tests, 77% backend coverage, typecheck/build and Ruff. Backend dependencies were installed at their existing pinned versions in a temporary Python 3.11 environment; project requirement files were not changed. Final browser checks used temporary fictional API responses. Live authenticated workflows remained blocked by the absence of an authorized development database/configuration and test accounts.

Existing dependency audit commands, run from `web/`:

```bash
npm audit
npm audit --omit=dev
```

They reported 9 affected package entries overall and 2 moderate runtime entries during this pass. No automatic audit fixes or dependency upgrades were applied. See the [public verification summary](VERIFICATION.md) for the dated check results, current blockers and limitations. Detailed diagnostic logs remain local and are excluded from publication.

## Structure and conventions

| Location | Responsibility |
| --- | --- |
| `backend/task_management/routes/` | HTTP parsing, permission checks and service delegation |
| `backend/task_management/services/` | Existing validation and business rules |
| `backend/task_management/models/` | SQLAlchemy models |
| `backend/task_management/permissions.py` | Canonical role, rank and permission map |
| `backend/task_management/auth_decorators.py` | Session, console and department restrictions |
| `backend/migrations/` | Existing Alembic migrations; unchanged by the UI customization |
| `web/src/api/` | Typed API requests and TanStack Query hooks |
| `web/src/auth/`, `web/src/layout/` | Route presentation guards and shared navigation |
| `web/src/pages/`, `web/src/components/` | Screens and existing shared UI primitives |
| `web/src/styles/` | Shared semantic tokens and scoped CrewFlow presentation |
| `web/public/brand/` | Original CrewFlow SVG mark and monochrome variant |

Keep backend authorization authoritative. Preserve field names, query contracts and role/department boundaries when working on presentation. Use existing semantic CSS tokens and bundled fonts rather than new frameworks or external font services. The original brand asset generator is documented in [web/public/brand/README.md](../web/public/brand/README.md).

The shared modal's inherited return-focus issue remains deferred; do not treat the visual sprint as authorization to rewrite focus behavior. Runtime library and font license texts accompany build assets in [third-party-notices.txt](../web/public/third-party-notices.txt).
