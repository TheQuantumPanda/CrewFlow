"""Fail-closed release evidence. No signing, publishing, suppression or risk acceptance."""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
MATERIAL = {'CRITICAL', 'HIGH', 'UNKNOWN'}


def sha(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def command(args):
    return subprocess.check_output(args, text=True).rstrip('\n')


def source_identity(root=ROOT):
    root = pathlib.Path(root)
    patterns = ['Dockerfile', '.dockerignore', 'backend/requirements*.txt',
                'backend/task_management/**/*.py', 'backend/migrations/**/*',
                'backend/gunicorn.conf.py', 'web/package*.json', 'web/vite.config.ts',
                'web/tsconfig*.json', 'web/index.html', 'web/src/**/*', 'web/public/**/*']
    paths = sorted({p for pattern in patterns for p in root.glob(pattern)
                    if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'})
    inputs = {str(p.relative_to(root)): sha(p) for p in paths}
    scope = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    git = ['git', '--no-optional-locks', '-C', str(root)]
    publication = command(git + ['ls-files', '--cached', '--others', '--exclude-standard', '-z']).split('\0')
    release_inputs = {name: sha(root / name) for name in publication if name and (root / name).is_file()}
    return {'commit': command(git + ['rev-parse', 'HEAD']),
            'dirty_paths': command(git + ['status', '--porcelain=v1', '--untracked-files=all']).splitlines(),
            'security_scope_sha256': scope, 'inputs': inputs,
            'release_inputs': release_inputs}


def fresh_db(metadata, now=None):
    now = now or dt.datetime.now(dt.UTC)
    if metadata.get('Version') != 2:
        raise ValueError('Unsupported or absent vulnerability DB schema')
    def date(key):
        return dt.datetime.fromisoformat(metadata[key].replace('Z', '+00:00'))
    updated, downloaded, expiry = date('UpdatedAt'), date('DownloadedAt'), date('NextUpdate')
    if any(x.tzinfo is None for x in [updated, downloaded, expiry]):
        raise ValueError('Unqualified database timestamp')
    if updated > now or downloaded > now or expiry <= now or now - updated > dt.timedelta(hours=24):
        raise ValueError('Stale, expired or future-dated vulnerability DB')
    return True


def archive_identity(path):
    """Support OCI and classic Docker archives; verify config content hashes."""
    with tarfile.open(path) as tar:
        names = tar.getnames()
        if 'index.json' in names:
            index = json.load(tar.extractfile('index.json'))
            def blob(digest):
                algorithm, value = digest.split(':')
                if algorithm != 'sha256':
                    raise ValueError('Unsupported OCI hash')
                data = tar.extractfile('blobs/sha256/' + value).read()
                if hashlib.sha256(data).hexdigest() != value:
                    raise ValueError('OCI content mismatch')
                return json.loads(data)
            def descend(descriptor):
                value = blob(descriptor['digest'])
                if 'manifests' in value:
                    found = [d for d in value['manifests'] if d.get('platform', {}).get('architecture') == 'amd64']
                    if len(found) != 1:
                        raise ValueError('Expected exactly one linux/amd64 image')
                    return descend(found[0])
                return value
            manifest = descend(index['manifests'][0])
            config_id = manifest['config']['digest']
            config = blob(config_id)
        else:
            manifests = json.load(tar.extractfile('manifest.json'))
            if len(manifests) != 1:
                raise ValueError('Expected one exported image')
            data = tar.extractfile(manifests[0]['Config']).read()
            config_id = 'sha256:' + hashlib.sha256(data).hexdigest()
            config = json.loads(data)
    if config.get('architecture') != 'amd64' or config.get('os') != 'linux':
        raise ValueError('Unexpected target platform')
    return {'archive_sha256': sha(path), 'config_id': config_id,
            'diff_ids': config['rootfs']['diff_ids'], 'platform': 'linux/amd64',
            '_runtime_config': config.get('config', {})}


def verify_runtime_config(exported, inspected):
    for key in ['Env', 'User', 'WorkingDir', 'Entrypoint', 'Cmd', 'Labels', 'ExposedPorts',
                'Healthcheck', 'Volumes', 'StopSignal']:
        if exported.get(key) != inspected.get(key):
            raise ValueError('Exported runtime configuration differs from loaded image: ' + key)


def verify_binding(scan, evidence, source):
    image = evidence['image']
    if image['security_scope_sha256'] != source['security_scope_sha256']:
        raise ValueError('Source/image scope mismatch')
    if scan['Metadata']['ImageID'] != image['config_id']:
        raise ValueError('Scanned configuration is not the exported image')
    if scan['Metadata'].get('DiffIDs') != image['diff_ids']:
        raise ValueError('Scanned layers do not match the exported image')
    if not evidence.get('loaded_image_id') or not image.get('archive_sha256'):
        raise ValueError('Image/archive identity absent')


def evaluate(scan, register, source, release=False, now=None):
    now = now or dt.datetime.now(dt.UTC)
    errors = []
    if register['security_scope_sha256'] != source['security_scope_sha256']:
        errors.append('Security-relevant source changed: new applicability review required')
    if register.get('schema_version', 1) != 1:
        errors.append('Unsupported decision register schema')
    if register.get('platform', 'linux/amd64') != 'linux/amd64':
        errors.append('Unreviewed target platform')
    os_meta = scan.get('Metadata', {}).get('OS', {})
    if os_meta and (os_meta.get('Family') != 'debian' or not str(os_meta.get('Name', '')).startswith('13')):
        errors.append('Unreviewed runtime distribution')
    records = {r['id']: r for r in register['decisions']}
    for result in scan.get('Results', []):
        for finding in result.get('Vulnerabilities', []):
            severity = finding['Severity']
            if severity not in MATERIAL:
                continue
            issue = finding['VulnerabilityID']
            record = records.get(issue)
            observed = {'name': finding['PkgName'], 'version': finding['InstalledVersion'],
                        'type': result['Type'], 'class': result['Class']}
            if severity == 'CRITICAL' or record is None or record['severity'] != severity:
                errors.append(f'New/escalated material advisory: {issue} ({severity})')
            elif observed not in record['packages']:
                errors.append(f'Unreviewed package/version/scope: {issue}')
    if release:
        if source.get('dirty_paths'):
            errors.append('Release requires a clean reviewed source revision')
        for record in register['decisions'] + register['manual_issues']:
            decision = record['owner_decision']
            if decision['status'] != 'accepted':
                errors.append(f'Owner review pending: {record["id"]}')
                continue
            try:
                reviewed = dt.datetime.fromisoformat(decision['reviewed_at'])
                expiry = dt.datetime.fromisoformat(decision['expires_at'])
                if (not decision['owner'] or not decision['review_reference'] or reviewed > now
                        or expiry <= now or expiry - reviewed > dt.timedelta(days=30)):
                    raise ValueError('Invalid decision')
            except (KeyError, TypeError, ValueError):
                errors.append(f'Invalid/expired owner review: {record["id"]}')
    return sorted(set(errors))


def normalized_inventory(inventory):
    packages = {}
    for item in inventory:
        name, version = item['name'], item['version']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name) or not re.fullmatch(r'[A-Za-z0-9.!+_-]+', version):
            raise ValueError('Invalid installed package identity')
        canonical = re.sub(r'[-_.]+', '-', name).lower()
        if canonical in packages:
            raise ValueError('Duplicate installed package identity')
        packages[canonical] = version
    if not packages:
        raise ValueError('Empty installed inventory')
    return packages


def audit_complete(inventory, audit):
    expected = normalized_inventory(inventory)
    observed = {}
    for package in audit['dependencies']:
        if package.get('skip_reason') or package.get('vulns'):
            raise ValueError('Skipped or vulnerable installed package: ' + package['name'])
        observed[re.sub(r'[-_.]+', '-', package['name']).lower()] = package['version']
    if observed != expected:
        raise ValueError('Audit did not cover exact installed inventory')


def write(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inventory = sub.add_parser('requirements')
    inventory.add_argument('inventory')
    inventory.add_argument('output')
    audit = sub.add_parser('audit')
    audit.add_argument('inventory')
    audit.add_argument('audit')
    source = sub.add_parser('source')
    source.add_argument('output')
    source.add_argument('--require-clean', action='store_true')
    collect = sub.add_parser('image')
    collect.add_argument('tag')
    collect.add_argument('archive')
    collect.add_argument('source')
    collect.add_argument('output')
    collect.add_argument('--require-labels', action='store_true')
    db = sub.add_parser('db')
    db.add_argument('cache')
    db.add_argument('output')
    check = sub.add_parser('check')
    for name in ['scan', 'register', 'source', 'image', 'db', 'output']:
        check.add_argument(name)
    check.add_argument('--release', action='store_true')
    args = parser.parse_args()
    if args.command == 'requirements':
        inventory = normalized_inventory(json.loads(pathlib.Path(args.inventory).read_text()))
        pathlib.Path(args.output).write_text(''.join(name + '==' + version + '\n' for name, version in sorted(inventory.items())))
    elif args.command == 'audit':
        audit_complete(json.loads(pathlib.Path(args.inventory).read_text()),
                       json.loads(pathlib.Path(args.audit).read_text()))
    elif args.command == 'source':
        data = source_identity()
        write(args.output, data)
        if args.require_clean and data['dirty_paths']:
            raise ValueError('Release CI requires a clean reviewed checkout')
    elif args.command == 'image':
        inspected = json.loads(command(['docker', 'image', 'inspect', args.tag]))[0]
        source = json.loads(pathlib.Path(args.source).read_text())
        labels = inspected['Config'].get('Labels') or {}
        if args.require_labels and not all(k in labels for k in [
                'io.crewflow.security-scope', 'org.opencontainers.image.revision']):
            raise ValueError('Release image requires source/revision labels')
        # The accepted local baseline has six file labels. Future CI adds exact commit/scope.
        for key, expected in labels.items():
            if key.startswith('io.crewflow.input.') and key.endswith('.sha256'):
                file = key[len('io.crewflow.input.'):-len('.sha256')]
                if source['inputs'].get(file) != expected:
                    raise ValueError('Accepted image input mismatch: ' + file)
        if 'io.crewflow.security-scope' in labels and labels['io.crewflow.security-scope'] != source['security_scope_sha256']:
            raise ValueError('Build label scope mismatch')
        if 'org.opencontainers.image.revision' in labels and labels['org.opencontainers.image.revision'] != source['commit']:
            raise ValueError('Build commit mismatch')
        image = archive_identity(args.archive)
        verify_runtime_config(image.pop('_runtime_config'), inspected['Config'])
        if image['diff_ids'] != inspected['RootFS']['Layers']:
            raise ValueError('Exported archive differs from loaded image')
        image['security_scope_sha256'] = source['security_scope_sha256']
        write(args.output, {'loaded_image_id': inspected['Id'], 'image': image,
                            'labels': labels, 'user': inspected['Config']['User'],
                            'source_commit': source['commit'], 'dirty_paths': source['dirty_paths'],
                            'source_binding': ('CI revision/scope labels' if args.require_labels else
                                               'Local accepted baseline input labels; not clean-commit provenance')})
    elif args.command == 'db':
        cache = pathlib.Path(args.cache) / 'db'
        meta = json.loads((cache / 'metadata.json').read_text())
        fresh_db(meta)
        write(args.output, {'metadata': meta, 'sha256': sha(cache / 'trivy.db'),
                            'source': 'ghcr.io/aquasecurity/trivy-db:2',
                            'validated_at': dt.datetime.now(dt.UTC).isoformat()})
    else:
        scan, register, source, image, db = (json.loads(pathlib.Path(getattr(args, name)).read_text())
                                           for name in ['scan', 'register', 'source', 'image', 'db'])
        fresh_db(db['metadata'])
        verify_binding(scan, image, source)
        errors = evaluate(scan, register, source, args.release)
        if args.release and image.get('source_binding') != 'CI revision/scope labels':
            errors.append('Release requires a newly built revision/scope-bound candidate')
        write(args.output, {'mode': 'release' if args.release else 'regression', 'errors': errors,
                            'pass': not errors, 'raw_findings_preserved': True,
                            'scan_sha256': sha(args.scan), 'image_evidence_sha256': sha(args.image),
                            'database_evidence_sha256': sha(args.db),
                            'register_sha256': sha(args.register)})
        if errors:
            print('\n'.join(errors))
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
