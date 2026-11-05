# CrewFlow release assurance

A local verification is evidence about one source/image/test environment. It is not a hosted CI result, signed provenance, public-deployment approval or a claim of bit-for-bit reproducibility.

The accepted local baseline is `crewflow:stage2e4d`, Docker image ID `sha256:9ac32692050df355acf426999511a5e5e9aaf393279997a37c7f4ed8edd26cb6` (linux/amd64). It includes the audit-disclosure fix, same-origin fonts, corrected logout navigation, APT 3.0.4 and Psycopg-C 3.3.8. It was built from an uncommitted working tree. The older Git HEAD alone does **not** identify that source. The user must review, commit and push the accepted changes personally.

## CI checks and interpretation

The workflow retains full backend pytest/Ruff and frontend typecheck/Vitest/build. It verifies native compiler, Python headers, `libpq-fe.h` and `pg_config`; builds the existing C driver with reviewed build-only constraints; audits actual installed application/development packages using a separate pinned audit environment; and runs both npm audits. A reported advisory or tool failure fails an audit. No audit-fix or application dependency upgrade is automatic.

The Docker job builds, probes, inventories, exports and scans **one candidate image**. A fresh PostgreSQL 17 instance exercises migrations, restricted runtime operations and privilege denials through Flask test clients. Those requests use real PostgreSQL but do not test a network HTTP or TLS ingress. Ordinary pytest remains isolated SQLite. No production credentials, hosted database or user-local database is used by CI.

The scanner is Trivy 0.76.1, downloaded from its official release and checked against a reviewed SHA-256. This verifies integrity against the pinned digest, not a separately verified signature. Each CI run obtains a fresh official `ghcr.io/aquasecurity/trivy-db:2` snapshot and records its schema, timestamps and content hash. Missing, future-dated, expired, older-than-24-hour or unsupported DB metadata fails closed. The subsequent archive scan disables feed/version/Java/VEX updates, uses vulnerability scanning only and preserves all raw OS/language findings. It does not filter out unfixed findings.

### Two separate vulnerability gates

1. **Regression gate:** any Critical, new/escalated High or Unknown advisory, changed affected package/version/component, or changed security-relevant application scope requires review. Known baseline findings remain in the raw report and decision register. Medium/Low remain visible; they are not a claim of zero risk.
2. **Release gate:** additionally fails on every pending/expired/unqualified owner decision, including the separate inactive ensurepip wheel. This job is intentionally expected to fail today. A passing regression job alone does not clear release.

[The canonical register](security-decisions.json) retains 13 High and six Unknown advisory IDs, exact installed packages, vulnerable features, vendor inconsistencies, applicability and recommendations. **No owner risk acceptance has been supplied.** Source-subset or unused-feature assessments are proposals for review, not suppressions. All 51 High package entries remain visible. The inactive pip 25.0.1 archive retains six disclosed advisories; installed pip 26.3 is a separate inventory item. The Linux-only builder pin of setuptools 83.0.0 has a disclosed Windows legacy-wheel-installation advisory; it is not in the final runtime.

Any future accepted decision must name an owner and review reference, use timezone-qualified review/expiry times with a maximum 30-day window, and apply only to the register's exact source scope, platform, component and versions. Re-evaluate on a new package/base/source, changed capabilities or deployment topology, new vulnerability information, or expiry. The helper validates format and bounds; it cannot authenticate a human reviewer. The user's review and repository governance must enforce ownership. Do not change pending to accepted simply to obtain green CI.

## Evidence chain

The source record captures actual commit, clean/dirty paths and hashes of application, migration, frontend-lock and Docker inputs. CI requires a clean checkout and matching `GITHUB_SHA`. Image labels bind revision and source scope. BuildKit metadata records resolved build inputs/base materials; it is retained as **unsigned metadata**, not a verified signed attestation. Base tags and Debian/Python transitive resolution can drift; record their resolved identities on every build.

The image evidence binds the loaded Docker image ID, exported archive SHA-256, OCI configuration digest and layer diff IDs. Trivy's `Metadata.ImageID` is a configuration digest; it can differ from Docker's index ID. Do not compare Trivy's `ArtifactID` to Docker's ID or call it an archive checksum. Policy checks compare configuration/layers and source scope; evidence hashes bind the scan, image record, DB record and register. Raw package inventories, scan and build metadata are retained with SHA256SUMS.

Only sanitized JSON/text evidence is uploaded for 14 days. Private environments, image archives, credential files, database dumps, browser profiles, tokens, signing keys and scanner databases are not uploaded. Build-record auto-upload is disabled. Treat any later rebuild as a new candidate requiring a corresponding scan; do not borrow an earlier image's clearance. No image is pushed, signed or deployed by this workflow.

## Review and release sequence

1. User reviews the complete working tree, legal notices and exclusions, then personally stages/commits/pushes. Preserve the complete MIT license and required notices.
2. Run hosted CI; inspect actual job results, native prerequisites, fresh feed identity, PostgreSQL smoke and evidence. Local checks do not prove hosted Actions succeeds.
3. Review remaining vulnerabilities explicitly. Remediate supported relevant fixes or record bounded owner decisions; preserve unresolved vendor contradictions. The inactive archive needs its own decision/correction.
4. Select the exact scanned candidate and retain source/build/image/scan identity beyond artifact expiry. Publishing/promotion/signing would require a separately authorized process.
5. Before public launch, verify real hosted HTTPS/proxy/cookies/CSRF, least-privilege hosted PostgreSQL with TLS/connection limits, backups/restore/rollback, and final smoke tests. These are separate from local acceptance.

## Local helper checks

```bash
python -m unittest discover -s tools/ci/tests -v
python tools/ci/release_checks.py source output/release/source.json
```

The PostgreSQL helper refuses arbitrary connection URLs and existing resource conflicts. Local execution requires explicit separate authorization; its `--local-approved` flag is an assertion of that authorization, not permission by itself. Local approved resources are retained. GitHub cleanup targets only IDs created in that ephemeral job. Its tmpfs storage is not durable across stop/reboot and is not a backup test.
