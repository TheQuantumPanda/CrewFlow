# CrewFlow deployment preparation

**CONDITIONAL — not public-deployment approval.** No hosting provider, cloud resources, remote image publication or deployment is configured by the release-assurance stage. The user performs all GitHub operations personally.

CrewFlow supports the existing simple pattern: one linux/amd64 Flask/Gunicorn container serving the compiled React SPA and API behind HTTPS, with durable PostgreSQL. Keep the database-provider and application-hosting decisions separate. No free-tier, pricing, resource-limit or backup entitlement is assumed; verify official provider terms when choosing a host.

## Release prerequisites

Read [production runtime](docs/production-runtime.md) for exact native build/APT order, configuration, least-privilege roles and controlled migration commands. Read [release assurance](docs/release-assurance.md) for the source/image/scan evidence chain and CI policy.

The accepted local image is `crewflow:stage2e4d`, ID `sha256:9ac32692050df355acf426999511a5e5e9aaf393279997a37c7f4ed8edd26cb6`. It passed isolated PostgreSQL, HTTPS and browser checks. Its source includes uncommitted changes; an older Git checkout will not contain all fixes. This baseline is not proof of a future hosted build or bit-for-bit reproducibility.

Before public deployment:

- The user reviews and publishes all accepted source/test/build fixes and new CI helpers/docs, preserving MIT and complete third-party notices. Do not publish diagnostic archives, databases, private `.env` files, keys, browser cookies or backups.
- Hosted GitHub Actions must actually run on the reviewed commit. Local equivalent checks do not establish hosted success. Select the exact scanned image/config/layers and retain source/build/scan evidence beyond CI artifact expiry.
- Obtain explicit owner decisions or corrections for all material residual advisories. The [register](docs/security-decisions.json) has 13 High IDs and six Unknown IDs pending, plus the inactive pip archive. CI's release gate remains deliberately blocked; installed Python/npm zero findings do not clear OS packages.
- Review capacity, supported PostgreSQL/region/TLS, durable storage, connection budget, ingress topology, health probes, backups, retention, recovery and rollback with the selected host. Use no production credentials in pull-request CI.

## Controlled execution sequence for a later authorized stage

1. Establish the reviewed source revision and image identity. Build/scan that candidate using the existing Dockerfile; do not retag an old vulnerable image as a release.
2. Provision an explicitly approved durable PostgreSQL target. Use separate setup, non-superuser migrator and restricted runtime roles. Require verified database TLS and network restrictions. Confirm identity before writes.
3. Arrange backup/recovery and run existing migrations once as migrator with `AUTO_BOOTSTRAP=0`; confirm head `b7c1e2d4a9f0`. Apply narrowly scoped runtime object grants. Never run the destructive demo seed or reset preserved data.
4. Provision the initial Super Admin once using the existing `create-admin` command and private explicit bootstrap password. This is a separate bounded write operation, not an ordinary startup action. No passwords belong in logs/docs/screenshots.
5. Configure stable private session key, explicit production/runtime database settings and disabled automatic bootstrap. Do not provide workers with migrator/setup credentials or bootstrap passwords.
6. Start the non-root Gunicorn container behind HTTPS. Set exact trusted proxy peers for that real topology; never wildcard scheme trust. Secure/HttpOnly/SameSite cookies, CSRF, restrictive CSP and API no-store must remain active.
7. Verify actual hosted liveness/readiness, nested-route refresh, fonts/notices, protected/unauthenticated requests, role/department denials, login/logout and persisted task/audit behavior. Test Admin logout reaches `/admin/login` and employee logout `/login`.
8. Verify restore and rollback procedures. An application rollback must remain compatible with the migrated schema; do not automatically downgrade the database. Retain the prior image and approved backup, and define operator recovery actions before public access.

No command here grants permission to mutate a local or hosted database. Local test resources are separate from production, and their credentials must never be copied to a public service.
