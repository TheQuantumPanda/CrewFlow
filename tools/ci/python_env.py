"""Create a private venv with verified pip, without invoking ensurepip's old wheel."""
import argparse
import hashlib
import os
import pathlib
import subprocess
import urllib.request
import venv

PIP_URL = ('https://files.pythonhosted.org/packages/07/25/ee8c38ae72d66b844ce8eb9711ba905dba21ca1a8a0c960057c41cd23337/'
           'pip-26.3-py3-none-any.whl')
PIP_SHA = 'f3b60b20ffaadd4415ed7957212a38ac63fa4c5fa375bd0f4a797777940fad13'


def create(target, wheel):
    target, wheel = pathlib.Path(target), pathlib.Path(wheel)
    if target.exists():
        raise ValueError('Refusing to overwrite an environment')
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != PIP_SHA:
        raise ValueError('pip wheel checksum mismatch')
    venv.EnvBuilder(with_pip=False).create(target)
    subprocess.run([str(target / 'bin/python'), '-c',
                    'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module("pip",run_name="__main__")',
                    str(wheel.resolve()), '--isolated', 'install', '--no-index', '--no-deps',
                    '--disable-pip-version-check', str(wheel.resolve())], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target')
    parser.add_argument('--wheel', required=True)
    parser.add_argument('--download', action='store_true', help='Explicitly permit official PyPI download')
    args = parser.parse_args()
    wheel = pathlib.Path(args.wheel)
    if not wheel.exists() and args.download:
        wheel.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(PIP_URL, timeout=60) as response:
            blob = response.read()
        if hashlib.sha256(blob).hexdigest() != PIP_SHA:
            raise ValueError('Downloaded pip integrity mismatch')
        fd = os.open(wheel, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(blob)
    create(args.target, wheel)
