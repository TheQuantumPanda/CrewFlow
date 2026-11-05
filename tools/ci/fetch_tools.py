"""Explicit, checksum-pinned official tools; feed acquisition is a separate operation."""
import argparse
import hashlib
import io
import json
import os
import pathlib
import subprocess
import tarfile
import urllib.request

TOOLS = {
    'actionlint': ('1.7.12', 'https://github.com/rhysd/actionlint/releases/download/v1.7.12/',
                   'actionlint_1.7.12_linux_amd64.tar.gz',
                   '8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8'),
    'trivy': ('0.76.1', 'https://github.com/aquasecurity/trivy/releases/download/v0.76.1/',
              'trivy_0.76.1_Linux-64bit.tar.gz',
              'c7cbe3137fb8a48a17574bede3dd6beb16742d1e9772929940fc90082c39d9c0'),
}


def fetch(name, destination):
    version, root, archive, expected = TOOLS[name]
    dest = pathlib.Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    if (dest / name).exists():
        raise ValueError('Refusing to replace a tool')
    with urllib.request.urlopen(root + archive, timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Official tool archive checksum mismatch')
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        member = tar.getmember(name)
        if not member.isfile():
            raise ValueError('Tool is not a regular archive member')
        executable = tar.extractfile(member).read()
    fd = os.open(dest / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(executable)
    (dest / (name + '-integrity.json')).write_text(json.dumps({
        'version': version, 'url': root + archive, 'archive_sha256': expected,
        'binary_sha256': hashlib.sha256(executable).hexdigest(),
        'verification': 'Pinned SHA-256; not a verified signature',
    }, indent=2))


def download_db(trivy, cache):
    """Future CI only: one fresh official snapshot, never an old fallback."""
    dest = pathlib.Path(cache)
    if dest.exists() and any(dest.iterdir()):
        raise ValueError('Fresh DB download requires an empty cache directory')
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run([trivy, 'image', '--cache-dir', str(dest), '--db-repository',
                    'ghcr.io/aquasecurity/trivy-db:2', '--download-db-only', '--no-progress',
                    '--skip-version-check'], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    tool = sub.add_parser('tool')
    tool.add_argument('name', choices=TOOLS)
    tool.add_argument('destination')
    db = sub.add_parser('db')
    db.add_argument('trivy')
    db.add_argument('cache')
    args = parser.parse_args()
    if args.command == 'tool':
        fetch(args.name, args.destination)
    else:
        download_db(args.trivy, args.cache)
