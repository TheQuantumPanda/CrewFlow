# CrewFlow development

[Setup](../README.md#local-setup) · [API](API.md) · [Security architecture](SECURITY.md) · [Release assurance](release-assurance.md)

Use Python 3.12 (reviewed 3.12.16) and Node 24.21.0. Keep the existing React 18, Flask/SQLAlchemy architecture, API contracts, TaskForge internal cookie/module names and seven-role permission map. No external font service is required.

## Native prerequisites and isolated installation

Psycopg-C 3.3.8 needs a compiler, Python development headers, libpq headers and `pg_config`. Verify `gcc --version`, `pg_config --version`, `libpq-fe.h` under `pg_config --includedir`, and `Python.h` in Python's include path. The reviewed production target is linux/amd64. Development against another OS/architecture needs its own native compatibility check.

The README uses `tools/ci/python_env.py` to create a new venv without ensurepip, install only checksum-verified pip 26.3, then use `--build-constraint tools/ci/build-constraints.txt` for the unchanged dev requirements. The source build requires setuptools 83.0.0; wheel 0.48.0 and packaging 26.3 are reviewed builder pins. Do not replace the driver with a binary wheel to avoid native prerequisites. The builder-only Windows advisory is disclosed in [release assurance](release-assurance.md); these tools do not enter the final image. [Runtime details](production-runtime.md) explain system libpq/OpenSSL and the APT bootstrap order.

## Local startup and database safety

Configure `backend/.env` privately before `cd backend && python run.py`. In another terminal, use `cd web && npm ci && npm run dev`. Vite uses localhost:5173 and proxies `/api` to port 5000 unless `VITE_API_TARGET` is set. `web/dist` is the production frontend build, served by Flask on the same origin as the API.

**Startup may write.** The development default `AUTO_BOOTSTRAP` applies migrations and baseline provisioning. Choose a fresh authorized database deliberately; set `AUTO_BOOTSTRAP=0` whenever startup writes are not approved. First-admin creation now requires an explicit private `BOOTSTRAP_ADMIN_PASSWORD`; no password is generated or logged. Ordinary production workers must not carry that password or migrator credentials. See the controlled sequence in [production runtime](production-runtime.md#controlled-database-preparation).

The existing `seed` command drops and recreates tables and publishes demo credentials; never use it against preserved or public data. Do not run `init-db`, downgrade, reset or repeat first-admin provisioning merely to test connectivity. Public test helpers and an optional `VITE_DEMO_MODE` presentation do not authorize any database writes.

## Checks and evidence

```bash
cd web
npm run typecheck
npm run test
npm run build
npm audit --json
npm audit --omit=dev --json
```

From `backend/` with the isolated development environment:

```bash
ruff check --no-cache .
pytest -q --cov=task_management --cov-report=term-missing
```

From the root:

```bash
python -m unittest discover -s tools/ci/tests -v
```

Ordinary pytest uses fresh in-memory SQLite and Flask test clients. Never point it at a persistent PostgreSQL target. The CI PostgreSQL smoke helper creates its own isolated instance, migrator/runtime roles and bounded fictional records; it rejects external connection URLs. Local use requires separate approval and retains resources. It is real PostgreSQL with Flask test clients, not an HTTPS test. [Verification](VERIFICATION.md) records actual environments and historical/local results.

The modal return-focus problem was corrected with focused tests. Board/list filters remain independent; native drag-and-drop has no separate touch/keyboard implementation. Preserve these actual feature boundaries in documentation. No complete accessibility certification is claimed.

## Structure

| Location | Responsibility |
| --- | --- |
| `backend/task_management/routes`, `services`, `models` | Existing HTTP, business rules and persistence |
| `backend/task_management/permissions.py` | Authoritative seven-role permission map |
| `backend/migrations` | Existing Alembic revisions |
| `web/src/api`, `auth`, `layout`, `pages`, `components` | Typed requests, navigation and presentation |
| `web/src/styles`, `web/public/brand` | Semantic tokens and original CrewFlow SVG identity |
| `tools/ci` | Isolated release checks; no application runtime imports except the approved PG smoke |
| `docs/security-decisions.json` | Owner-pending residual vulnerability register |

Keep private `.env`, backups, keys, cookies, scanner caches and archives outside publication. Output diagnostics are ignored. Preserve [MIT](../LICENSE), [complete font/library notices](../web/public/third-party-notices.txt) and [brand source documentation](../web/public/brand/README.md). CrewFlow customizes TaskForge; it does not claim original authorship of its backend.
