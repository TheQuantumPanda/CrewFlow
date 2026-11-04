# CrewFlow verification and readiness

This public summary records the completed UI sprint and the subsequent technical preflight on **2026-11-04**. Detailed local logs, browser fixtures, machine paths and diagnostic captures are intentionally excluded from the repository. The publication-preparation step did not rerun application tests or change application code.

## Recorded automated results

| Check | Final UI pass | Subsequent technical preflight |
| --- | --- | --- |
| `cd web` → `npm run typecheck` | Passed | Passed |
| `cd web` → `npm run test` | 27 tests across 3 files passed | 27 tests across 3 files passed |
| `cd web` → `npm run build` | Passed | Passed |
| `cd backend` → `pytest -q --cov=task_management --cov-report=term-missing` | 89 tests passed; 77% coverage | Blocked: pytest/backend environment unavailable |
| `cd backend` → `ruff check .` | Passed | Blocked: Ruff unavailable |

The backend suite executed Flask test clients with fresh **in-memory SQLite**, not a running development server or persistent development database. The later preflight could not repeat the backend checks because the temporary test environment was no longer available. Historical passes are not presented as fresh results or as PostgreSQL/MySQL verification.

## Browser and live-workflow scope

The final visual review covered twelve views in light/dark themes at **390, 768 and 1440px**, plus all seven role fixtures. The [selected gallery](SCREENSHOTS.md) contains actual browser renders using **temporary fictional API responses**. Earlier task and administration browser workflows also used mocks. No mock records were added to application source or database seeds.

Live sign-in/sign-out, administrative authentication, persistent task creation/editing, assignments, progress/status changes, Kanban persistence after refresh, department boundaries, audit persistence and administrative writes remain **unverified against a running development backend**. No authorized local database configuration or accounts were supplied. Mocked role visibility is not proof of backend authorization. No development database was initialized, migrated, reset or seeded during the final verification/preflight work.

Keyboard inspection reproduced the inherited modal return-focus defect in **20 of 20 cycles**: focus stayed in the open dialog but did not return to its opening control after closing. Shared focus-management code remains unchanged and needs a separately reviewed fix. Command-palette and existing navigation-chord checks passed in the simulated browser environment. No complete accessibility certification is claimed.

## Security and deployment status

**CONDITIONAL portfolio/publication readiness is not deployment approval.** The completed interface and documentation can be reviewed as portfolio work, subject to publication-content review. The subsequent technical preflight rates the current production configuration **NOT READY for public deployment** until its security/configuration findings and live verification gaps receive an approved disposition.

Recorded dependency findings:

- `npm audit --json`: **9 affected package entries**, comprising 2 critical, 2 high and 5 moderate; the preflight distinguished **17 underlying advisory identifiers** from parent-package propagation.
- `npm audit --omit=dev --json`: **2 moderate runtime entries**. Many other findings concern development/test tooling, not the Flask-served static application. This does not establish security clearance.
- The direct `gunicorn==21.2.0` requirement falls in the ranges of [GHSA-w3h3-4rj7-4ph4](https://github.com/advisories/GHSA-w3h3-4rj7-4ph4) and [GHSA-hc5x-x2vx-497g](https://github.com/advisories/GHSA-hc5x-x2vx-497g). A supported, patched production-server version requires an approved dependency change and regression testing.
- No comprehensive Python dependency-vulnerability scan was performed. The manual Gunicorn review is not a substitute for one.

The preflight also identified generated bootstrap-password logging and a registration exception path that can expose internal error text. These were source-inspection findings, not reproduced attacks. No source remediation, dependency upgrade, authentication change or deployment was performed.

Before public deployment: review the advisories and logging/error findings; use a strong private session key, exact production mode and HTTPS; configure durable database storage/backups; use controlled migrations and private initial-account provisioning; verify proxy trust, cookies/CSRF and authenticated operations through the actual ingress. Startup can migrate/create records; the demo seed is destructive. See [development safety instructions](DEVELOPMENT.md#database-safety). Demo/test helpers are not production account provisioning, and demonstration credentials must not be used on a public service.

## Existing product limitations

- Board filtering is independent of task-list filtering.
- Some screens have no pagination controls; the current task-list request is capped at 200 records.
- Audit presentation is a connected summary feed, not a full expandable before/after snapshot viewer.
- Native drag-and-drop has no separate touch or keyboard implementation.
- Dense tables and Kanban columns intentionally scroll inside their containers on smaller screens.

Management read failures now display load-error messages, and unavailable member/account counts are not shown as false zeros. These were presentation-only corrections; API hooks, requests, retries, business calculations and permission rules remain unchanged.

CrewFlow is a frontend customization of TaskForge. Original MIT copyright and permission notices remain in [LICENSE](../LICENSE), and reviewed frontend library/font texts are retained in [third-party notices](../web/public/third-party-notices.txt). No original authorship of the underlying backend or permission system is claimed.
