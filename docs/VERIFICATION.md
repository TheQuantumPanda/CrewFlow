# CrewFlow verification and readiness

Updated **2026-11-05**. This sanitized public summary separates local automated checks, live isolated integration campaigns, mocked presentation evidence and unexecuted hosted checks. Private diagnostics, machine paths, credentials and database contents are excluded from publication.

## Current source and CI-equivalent checks

| Check | Actual local result | Environment |
| --- | --- | --- |
| Frontend TypeScript | PASS | Existing frontend environment |
| Frontend Vitest | **82 passed**, eight files | Existing fixtures/jsdom; not live backend |
| Frontend production build | PASS | Vite 6.4.5; no source maps, 15 standalone WOFF2 fonts |
| Full backend pytest/coverage | **136 passed**, **82%** | Network-disabled accepted-image container; Flask test clients/in-memory SQLite |
| Backend Ruff | PASS | Existing Ruff 0.6.9, no source edits |
| Release-helper unit tests | **39 passed** | Synthetic policy evidence, stdlib unittest; no database/network |
| Workflow syntax | PASS | Checksum-verified actionlint 1.7.12; local ShellCheck unavailable |
| PostgreSQL CI smoke | PASS after correcting helper grant order | Fresh isolated PostgreSQL 17.11, non-superuser migrations and runtime; Flask test clients, not real network HTTPS |
| npm full/runtime audit | **0 reported findings** | Current installed/locked frontend; official registry audit responses |
| Installed runtime/development Python audits | **0 reported findings, no skipped packages** | Exact 22-package runtime and 30-package test environment inventories; isolated pip-audit 2.10.1 |

The local PostgreSQL smoke executed 20 requests, three synthetic sign-ins and ten safe privilege denials. It reached migration head `b7c1e2d4a9f0`, used Psycopg-C/libpq 17.11, committed a task/assignment progress update, recorded audits and preserved the corrected dashboard policy. A setup-owned schema must have runtime USAGE granted by the setup role, not by the table-owning migrator. The helper was corrected after that initial failure; migrations were not repeated. All smoke resources are test-only; tmpfs data is not a durable recovery test.

The complete GitHub Actions workflow has **not run on GitHub** for the accepted source. Native runner prerequisites, Actions integrations, fresh feed download and future Docker build must be verified in hosted CI after the user's review/commit/push. The local stage reused the accepted image and current scanner DB; it did not rebuild an application image or download another local DB snapshot.

## Accepted real integration evidence

Separate earlier local campaigns used actual Docker applications, PostgreSQL persistence and authenticated HTTP/HTTPS, not mocked responses:

- Stage 2E.2 verified PostgreSQL migrations, relationships, persistence, controlled restart and private backup/isolated restore. The audit-disclosure defect was discovered, corrected, then independently tested in a patched image.
- Stage 2E.2b passed **52 real HTTP/PostgreSQL security checks** across all seven synthetic roles, including denial of raw dashboard audit snapshots for HR/Manager/Team Lead.
- Stage 2E.4A passed separate non-superuser migrator and restricted-runtime grants/denials. Local setup superuser credentials are not a production runtime pattern.
- Stage 2E.4B.2 passed **67 real Chromium assertions** and **290 real HTTPS assertions**, verifying fonts under unchanged CSP, Admin/Super Admin logout to `/admin/login`, employee logout to `/login`, authentication clearing, production cookies, CSRF and explicit proxy trust.
- Stage 2E.4D accepted image `crewflow:stage2e4d`, ID `sha256:9ac32692050df355acf426999511a5e5e9aaf393279997a37c7f4ed8edd26cb6`, passed **83 HTTPS requests / 338 assertions**, **66 Chromium assertions**, PostgreSQL TLS/native-driver and restricted-role checks. The complete backend suite passed 136 tests at 82% coverage.

These are dated local campaign results, not fresh Stage 2E.4E browser tests or hosted-ingress evidence. User-reported manual tests and independently automated checks remain distinct. The original existing employee's separately credentialed real-HTTP test was not substituted by synthetic-account results; it remains a disclosed pre-public-launch check where needed.

## Security status and release gates

**CONDITIONAL — not public-deployment approval.** The accepted runtime includes Gunicorn 26.2.0, private explicit first-admin password provisioning without disclosure, sanitized unexpected registration errors, patched Python packages, Router 7.18.5, Vite 6.4.5, Vitest 4.1.12, modal focus restoration, audit permission enforcement, same-origin fonts and corrected logout routing. Native remediation uses APT/libapt 3.0.4 and Psycopg-C 3.3.8 linked to system libraries.

The same-day offline **Trivy 0.76.1** scan of the exact accepted image with a recorded schema-2 DB reports **307 package/advisory entries / 149 distinct advisory IDs**: **0 Critical, 51 High, 104 Medium, 146 Low and six Unknown entries**. High entries cover **13 distinct IDs**. OS findings are separate from the zero installed Python/npm audit results. No claim of zero image vulnerabilities is made.

The [canonical register](security-decisions.json) retains all 13 High IDs, six Unknown IDs, supported-vendor status, applicability uncertainty and owner-pending decisions. An inactive ensurepip pip 25.0.1 archive retains six disclosed advisories even though installed pip is 26.3. It has not been removed or accepted. Builder-only setuptools 83.0.0 has a disclosed Windows legacy-wheel advisory; its narrow approved Linux source-build use does not clear unrelated risks.

[Release assurance](release-assurance.md) documents a fail-closed regression gate and a separate release-readiness gate. The latter deliberately fails until owner decisions/corrections are supplied. Remaining gates include hosted CI on the reviewed committed source, hosted least-privilege PostgreSQL/TLS and pool limits, actual ingress/proxy/HTTPS tests, backup retention/restore/rollback and release smoke verification. Local HTTPS does not certify a future hosting provider.

## Presentation evidence and inherited limits

The [selected ten-image gallery](SCREENSHOTS.md) remains actual browser renders using **temporary fictional API fixtures** from the UI sprint, not live database screenshots. That sprint inspected light/dark themes and representative 390/768/1440px layouts. Historical Pass 5 results (27 frontend, 89 backend, 77% coverage, mocked workflows and then-missing backend configuration) have been superseded by the separately identified local security campaigns, not relabeled as live tests.

The previously reproduced modal return-focus defect was corrected in Stage 2D and regression-tested. No complete accessibility certification is claimed. Current inherited product limits remain:

- Board filtering is independent of task-list filtering.
- Some screens lack pagination controls; task-list requests cap at 200 records.
- Audit UI presents connected summaries, not a full expandable before/after viewer.
- Native drag-and-drop has no separate touch/keyboard implementation.
- Dense tables and Kanban columns intentionally scroll inside containers on small screens.

Management load failures have explicit error presentation. Backend authorization remains authoritative. CrewFlow customizes TaskForge; [original MIT attribution](../LICENSE) and [complete library/font notices](../web/public/third-party-notices.txt) remain intact.
