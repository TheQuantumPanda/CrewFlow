"""Policy tests use synthetic evidence; never contact Docker, a database or the network."""
import copy
import datetime as dt
import hashlib
import io
import json
import pathlib
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import postgres_smoke as pg  # noqa: E402
import release_checks as checks  # noqa: E402

NOW = dt.datetime(2026, 11, 5, 12, tzinfo=dt.UTC)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.source = {'security_scope_sha256': 'scope'}
        self.pkg = {'name': 'libexample', 'version': '1.0', 'type': 'debian', 'class': 'os-pkgs'}
        self.record = {'id': 'CVE-test', 'severity': 'HIGH', 'packages': [self.pkg],
                       'owner_decision': {'status': 'pending'}}
        self.register = {'security_scope_sha256': 'scope', 'decisions': [self.record], 'manual_issues': []}
        self.scan = {'Metadata': {'ImageID': 'config', 'DiffIDs': ['layer']}, 'Results': [{
            'Type': 'debian', 'Class': 'os-pkgs', 'Vulnerabilities': [{
                'VulnerabilityID': 'CVE-test', 'Severity': 'HIGH',
                'PkgName': 'libexample', 'InstalledVersion': '1.0'}]}]}
        self.evidence = {'loaded_image_id': 'docker-index', 'image': {
            'security_scope_sha256': 'scope', 'config_id': 'config',
            'diff_ids': ['layer'], 'archive_sha256': 'archive'}}
        self.meta = {'Version': 2, 'UpdatedAt': '2026-11-05T07:00:00Z',
                     'DownloadedAt': '2026-11-05T08:00:00Z', 'NextUpdate': '2026-11-06T07:00:00Z'}

    def evaluate(self, release=False):
        return checks.evaluate(self.scan, self.register, self.source, release, NOW)

    def test_known_pending_is_only_regression_pass(self):
        self.assertEqual(self.evaluate(), [])
        self.assertTrue(self.evaluate(True))

    def test_new_high_fails(self):
        self.scan['Results'][0]['Vulnerabilities'][0]['VulnerabilityID'] = 'CVE-new'
        self.assertTrue(self.evaluate())

    def test_critical_always_blocks_even_with_record(self):
        self.record['severity'] = 'CRITICAL'
        self.scan['Results'][0]['Vulnerabilities'][0]['Severity'] = 'CRITICAL'
        self.assertTrue(self.evaluate())

    def test_severity_escalation_fails(self):
        self.record['severity'] = 'UNKNOWN'
        self.assertTrue(self.evaluate())

    def test_material_unknown_not_ignored(self):
        self.scan['Results'][0]['Vulnerabilities'][0]['Severity'] = 'UNKNOWN'
        self.assertTrue(self.evaluate())

    def test_package_change_requires_review(self):
        self.scan['Results'][0]['Vulnerabilities'][0]['PkgName'] = 'other'
        self.assertTrue(self.evaluate())

    def test_version_change_requires_review(self):
        self.scan['Results'][0]['Vulnerabilities'][0]['InstalledVersion'] = '1.1'
        self.assertTrue(self.evaluate())

    def test_security_source_change_requires_review(self):
        self.source['security_scope_sha256'] = 'other'
        self.assertTrue(self.evaluate())

    def accepted(self):
        self.record['owner_decision'] = {'status': 'accepted', 'owner': 'test-owner',
            'review_reference': 'fictional-test-only', 'reviewed_at': '2026-11-05T10:00:00+00:00',
            'expires_at': '2026-11-12T10:00:00+00:00'}

    def test_valid_bounded_decision(self):
        self.accepted()
        self.assertEqual(self.evaluate(True), [])

    def test_expired_decision_blocks(self):
        self.accepted()
        self.record['owner_decision']['expires_at'] = '2026-11-05T11:00:00+00:00'
        self.assertTrue(self.evaluate(True))

    def test_overlong_decision_blocks(self):
        self.accepted()
        self.record['owner_decision']['expires_at'] = '2027-01-01T00:00:00+00:00'
        self.assertTrue(self.evaluate(True))

    def test_missing_review_reference_blocks(self):
        self.accepted()
        self.record['owner_decision']['review_reference'] = ''
        self.assertTrue(self.evaluate(True))

    def test_manual_inactive_archive_blocks(self):
        self.accepted()
        self.register['manual_issues'] = [{'id': 'inactive-pip', 'owner_decision': {'status': 'pending'}}]
        self.assertTrue(self.evaluate(True))

    def test_clean_binding_distinguishes_docker_and_config_id(self):
        checks.verify_binding(self.scan, self.evidence, self.source)

    def test_wrong_config_fails(self):
        self.scan['Metadata']['ImageID'] = 'different'
        with self.assertRaises(ValueError):
            checks.verify_binding(self.scan, self.evidence, self.source)

    def test_wrong_layers_fail(self):
        self.scan['Metadata']['DiffIDs'] = ['other']
        with self.assertRaises(ValueError):
            checks.verify_binding(self.scan, self.evidence, self.source)

    def test_wrong_source_binding_fails(self):
        self.source['security_scope_sha256'] = 'different'
        with self.assertRaises(ValueError):
            checks.verify_binding(self.scan, self.evidence, self.source)

    def test_fresh_database(self):
        self.assertTrue(checks.fresh_db(self.meta, NOW))

    def test_missing_database_rejected(self):
        with self.assertRaises(ValueError):
            checks.fresh_db({}, NOW)

    def test_stale_database_rejected(self):
        self.meta['UpdatedAt'] = '2026-11-03T07:00:00Z'
        with self.assertRaises(ValueError):
            checks.fresh_db(self.meta, NOW)

    def test_expired_database_rejected(self):
        self.meta['NextUpdate'] = '2026-11-05T11:00:00Z'
        with self.assertRaises(ValueError):
            checks.fresh_db(self.meta, NOW)

    def test_future_database_rejected(self):
        self.meta['DownloadedAt'] = '2026-11-06T11:00:00Z'
        with self.assertRaises(ValueError):
            checks.fresh_db(self.meta, NOW)

    def test_protected_databases_rejected(self):
        for database in ['crewflow_test', 'crewflow_lp_2e4a_20261105',
                         'crewflow_verify_2e2_20261105', 'crewflow_verify_2e2b_20261105']:
            with self.subTest(database=database), self.assertRaises(ValueError):
                pg.guard_target(database, 'crewflow-ci-pg-2e4e-20261105')

    def test_external_host_rejected(self):
        with self.assertRaises(ValueError):
            pg.guard_target('crewflow_ci_2e4e_20261105', 'production.example')

    def test_only_owned_ci_targets_allowed(self):
        pg.guard_target('crewflow_ci_2e4e_20261105', 'crewflow-ci-pg-2e4e-20261105')
        pg.guard_target('crewflow_ci_123_1', 'crewflow-ci-pg-123-1')

    def test_classic_archive_hash_and_config(self):
        config = {'architecture': 'amd64', 'os': 'linux', 'rootfs': {'diff_ids': ['layer']}}
        blob = json.dumps(config).encode()
        with tempfile.TemporaryDirectory() as directory:
            archive = pathlib.Path(directory) / 'image.tar'
            with tarfile.open(archive, 'w') as tar:
                for name, data in [('config.json', blob), ('manifest.json', b'[{"Config":"config.json"}]')]:
                    item = tarfile.TarInfo(name)
                    item.size = len(data)
                    tar.addfile(item, io.BytesIO(data))
            identity = checks.archive_identity(archive)
            self.assertEqual(identity['config_id'], 'sha256:' + hashlib.sha256(blob).hexdigest())
            self.assertEqual(identity['diff_ids'], ['layer'])

    def test_distribution_change_blocks(self):
        self.scan['Metadata']['OS'] = {'Family': 'alpine', 'Name': '3.22'}
        self.assertTrue(self.evaluate())

    def test_platform_change_blocks(self):
        self.register['platform'] = 'linux/arm64'
        self.assertTrue(self.evaluate())

    def test_missing_archive_identity_blocks(self):
        del self.evidence['image']['archive_sha256']
        with self.assertRaises(ValueError):
            checks.verify_binding(self.scan, self.evidence, self.source)

    def test_naive_owner_timestamp_blocks(self):
        self.accepted()
        self.record['owner_decision']['reviewed_at'] = '2026-11-05T10:00:00'
        self.assertTrue(self.evaluate(True))

    def test_future_owner_timestamp_blocks(self):
        self.accepted()
        self.record['owner_decision']['reviewed_at'] = '2026-11-06T10:00:00+00:00'
        self.assertTrue(self.evaluate(True))

    def test_installed_inventory_includes_pip_without_direct_url(self):
        self.assertEqual(checks.normalized_inventory([{'name': 'pip', 'version': '26.3'}]), {'pip': '26.3'})

    def test_skipped_audit_is_not_zero_clearance(self):
        with self.assertRaises(ValueError):
            checks.audit_complete([{'name': 'pip', 'version': '26.3'}], {
                'dependencies': [{'name': 'pip', 'skip_reason': 'URL requirement'}]})

    def test_missing_audit_package_fails(self):
        with self.assertRaises(ValueError):
            checks.audit_complete([{'name': 'pip', 'version': '26.3'}], {'dependencies': []})

    def test_complete_audit_passes(self):
        checks.audit_complete([{'name': 'pip', 'version': '26.3'}], {
            'dependencies': [{'name': 'pip', 'version': '26.3', 'vulns': []}]})

    def test_dirty_source_is_not_release_ready(self):
        self.accepted()
        self.source['dirty_paths'] = [' M Dockerfile']
        self.assertTrue(self.evaluate(True))

    def test_same_layers_with_different_runtime_config_rejected(self):
        with self.assertRaises(ValueError):
            checks.verify_runtime_config({'Env': ['APP_ENV=production']}, {'Env': ['APP_ENV=development']})

    def test_exported_runtime_config_matches(self):
        checks.verify_runtime_config({'User': '10001', 'Env': ['AUTO_BOOTSTRAP=0']},
                                     {'User': '10001', 'Env': ['AUTO_BOOTSTRAP=0']})

    def test_evaluation_does_not_mutate_evidence(self):
        before = copy.deepcopy(self.scan)
        self.evaluate(True)
        self.assertEqual(self.scan, before)


if __name__ == '__main__':
    unittest.main()
