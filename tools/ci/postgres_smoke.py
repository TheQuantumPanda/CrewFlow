"""Fresh, helper-owned PostgreSQL only. Never accepts an external DATABASE_URL.

Local mode requires separately approved exact names and retains every resource.
GitHub mode removes only IDs created by this invocation, on its ephemeral runner.
Flask test client + actual PostgreSQL: this is not real HTTP/HTTPS evidence.
"""
import argparse
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

PG_IMAGE = 'postgres@sha256:3b0cda93be7c8dba2ed484d19393d93845dc3dafb88973e248ba8e6d99d784e1'
HEAD = 'b7c1e2d4a9f0'
TABLES = {'users': 'SELECT,INSERT,UPDATE', 'employees': 'SELECT,INSERT,UPDATE',
          'tasks': 'SELECT,INSERT,UPDATE', 'departments': 'SELECT,INSERT',
          'task_assignments': 'SELECT,INSERT,UPDATE,DELETE', 'activity_logs': 'SELECT,INSERT'}


def guard_target(database, host):
    if not re.fullmatch(r'crewflow_ci_(?:2e4e_20261105|[0-9]+_[0-9]+)', database):
        raise ValueError('Protected or non-CI database target rejected')
    if not re.fullmatch(r'crewflow-ci-pg-(?:2e4e-20261105|[0-9]+-[0-9]+)', host):
        raise ValueError('External/non-owned PostgreSQL host rejected')
    if database.removeprefix('crewflow_ci_').replace('_', '-') != host.removeprefix('crewflow-ci-pg-'):
        raise ValueError('Database/container identifier mismatch')


def run_inside(config_path, output):
    import psycopg
    from psycopg import sql
    cfg = json.loads(pathlib.Path(config_path).read_text())
    guard_target(cfg['database'], cfg['pg'])
    setup, migrator, runtime = 'crewflow_ci_setup', 'crewflow_ci_migrator', 'crewflow_ci_runtime'
    def connect(role):
        return psycopg.connect(host=cfg['pg'], dbname=cfg['database'], user=role, password=cfg[role])
    def url(role):
        # Generated passwords contain only hex. Never output this URL.
        return f'postgresql+psycopg://{role}:{cfg[role]}@{cfg["pg"]}/{cfg["database"]}'
    if cfg.get("resume_prepared"):
        # Local interrupted preparation only: never rerun migrations or prior fixtures.
        with connect(migrator) as conn:
            assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == HEAD
            assert conn.execute("SELECT count(*) FROM users").fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM departments").fetchone()[0] == 0
            owners = conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner=%s", [migrator]).fetchone()[0]
            assert owners == 7
        env = dict(os.environ, APP_ENV="production", AUTO_BOOTSTRAP="0", SECRET_KEY=cfg["signing_key"])
    else:
        with connect(setup) as conn:
            assert conn.execute('SELECT current_database()').fetchone()[0] == cfg['database']
            # Fresh cluster guard: migrations and account fixtures cannot be rerun.
            assert conn.execute("SELECT to_regclass('public.users')").fetchone()[0] is None
            for role in [migrator, runtime]:
                conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE '
                                     'NOREPLICATION NOBYPASSRLS PASSWORD {}').format(
                                         sql.Identifier(role), sql.Literal(cfg[role])))
            conn.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(cfg['database'])))
            conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}, {}').format(
                sql.Identifier(cfg['database']), sql.Identifier(migrator), sql.Identifier(runtime)))
            conn.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
            conn.execute(sql.SQL('GRANT USAGE,CREATE ON SCHEMA public TO {}').format(sql.Identifier(migrator)))
            conn.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(runtime)))
        env = dict(os.environ, APP_ENV='production', AUTO_BOOTSTRAP='0', SECRET_KEY=cfg['signing_key'],
                   DATABASE_URL=url(migrator))
        result = subprocess.run([sys.executable, '-m', 'flask', '--app', 'task_management', 'db', 'upgrade'],
                                cwd='/app/backend', env=env, capture_output=True)
        if result.returncode:
            diagnostic = (result.stdout + result.stderr).decode(errors='replace')
            for value in cfg.values():
                if isinstance(value, str):
                    diagnostic = diagnostic.replace(value, '[REDACTED]')
            pathlib.Path(output).with_suffix('.failure.log').write_text(diagnostic)
            raise RuntimeError('Migration failed; sanitized diagnostic retained')
        with connect(migrator) as conn:
            assert conn.execute('SELECT version_num FROM alembic_version').fetchone()[0] == HEAD
            assert not conn.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()[0]
            for table, grants in TABLES.items():
                conn.execute(sql.SQL('GRANT ' + grants + ' ON TABLE public.{} TO {}').format(
                    sql.Identifier(table), sql.Identifier(runtime)))
            conn.execute(sql.SQL('GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {}').format(sql.Identifier(runtime)))
            for enum in ['user_role', 'task_priority', 'assignment_status']:
                conn.execute(sql.SQL('REVOKE ALL ON TYPE public.{} FROM PUBLIC').format(sql.Identifier(enum)))
                conn.execute(sql.SQL('GRANT USAGE ON TYPE public.{} TO {}').format(
                    sql.Identifier(enum), sql.Identifier(runtime)))
            owners = conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner=%s",
                                  [migrator]).fetchone()[0]
            assert owners == 7
    env['DATABASE_URL'] = url(runtime)
    env.update(BOOTSTRAP_ADMIN_USERNAME='ci.super', BOOTSTRAP_ADMIN_PASSWORD=cfg['account_password'])
    result = subprocess.run([sys.executable, '-m', 'flask', '--app', 'task_management', 'create-admin'],
                            cwd='/app/backend', env=env, capture_output=True)
    if result.returncode:
        diagnostic = (result.stdout + result.stderr).decode(errors='replace')
        for value in cfg.values():
            if isinstance(value, str):
                diagnostic = diagnostic.replace(value, '[REDACTED]')
        pathlib.Path(output).with_suffix('.failure.log').write_text(diagnostic)
        raise RuntimeError('Private initial provisioning failed')
    os.environ.update({k: env[k] for k in ['APP_ENV', 'AUTO_BOOTSTRAP', 'SECRET_KEY', 'DATABASE_URL']})
    sys.path.insert(0, '/app/backend')
    from task_management import create_app
    app = create_app()
    assert app.config['ENV_NAME'] == 'production' and not app.config['AUTO_BOOTSTRAP']
    assert urlsplit(app.config['SQLALCHEMY_DATABASE_URI']).path == '/' + cfg['database']
    clients, events = {}, []
    def request(role, method, path, status=200, body=None, csrf=True):
        client = clients[role]
        cookie = client.get_cookie('taskforge_csrf', domain='ci.test')
        headers = {'X-CSRF-Token': cookie.value} if cookie and csrf else {}
        response = client.open(path, method=method, json=body, headers=headers, base_url='https://ci.test')
        events.append({'role': role, 'method': method, 'path': path, 'expected': status,
                       'actual': response.status_code})
        assert response.status_code == status, f'{role} {method} {path} unexpected status'
        assert response.headers.get('Cache-Control') == 'no-store'
        return response.get_json()
    for role in ['super_admin', 'hr', 'employee']:
        clients[role] = app.test_client()
    request('super_admin', 'POST', '/api/auth/admin/login', body={
        'username': 'ci.super', 'password': cfg['account_password']})
    dept = request('super_admin', 'POST', '/api/departments', 201,
                   {'name': 'CI fictional team', 'description': 'Disposable CI record'})['department']['id']
    employee_id = None
    for role in ['hr', 'employee']:
        employee = request('super_admin', 'POST', '/api/employees', 201, {
            'username': 'ci.' + role, 'password': cfg['account_password'], 'role': role,
            'department_id': dept, 'employee_code': 'CI-' + role, 'first_name': 'Fictional',
            'last_name': role, 'email': role + '@example.invalid', 'phone': '0000000000',
            'position': 'CI test'})['employee']
        if role == 'employee':
            employee_id = employee['id']
        request(role, 'POST', '/api/auth/login', body={
            'username': 'ci.' + role, 'password': cfg['account_password']})
    task = request('super_admin', 'POST', '/api/tasks', 201,
                   {'title': 'CI native persistence', 'priority': 'High', 'estimated_hours': 2})['task']['id']
    assignment = request('super_admin', 'POST', '/api/assignments', 201,
                         {'task_id': task, 'employee_id': employee_id})['assignment']['id']
    request('employee', 'PUT', f'/api/assignments/{assignment}/status', 403,
            {'completion_percentage': 40}, csrf=False)
    request('employee', 'PUT', f'/api/assignments/{assignment}/status', body={
        'status': 'In Progress', 'completion_percentage': 40})
    assert request('hr', 'GET', '/api/dashboard/stats')['recent_activity'] == []
    request('hr', 'GET', '/api/dashboard/activity', 403)
    assert request('super_admin', 'GET', '/api/dashboard/stats')['recent_activity']
    request('employee', 'GET', '/api/dashboard/stats', 403)
    for role in clients:
        request(role, 'POST', '/api/auth/logout', body={})
        request(role, 'GET', '/api/auth/me', 401)
    denials = []
    with connect(runtime) as conn:
        assert conn.execute('SELECT current_user').fetchone()[0] == runtime
        assert not any(conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls '
                                    'FROM pg_roles WHERE rolname=current_user').fetchone())
        assert conn.execute('SELECT count(*) FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles '
                            'WHERE rolname=current_user)').fetchone()[0] == 0
        assert conn.execute('SELECT completion_percentage FROM task_assignments WHERE id=%s',
                            [assignment]).fetchone()[0] == 40
        assert conn.execute('SELECT count(*) FROM activity_logs').fetchone()[0] > 0
        conn.rollback()
        for statement in ['CREATE TABLE public.ci_forbidden(id integer)', 'ALTER TABLE public.users ADD COLUMN ci_forbidden integer',
                          'TRUNCATE public.users CASCADE', 'UPDATE public.activity_logs SET action=action',
                          'DELETE FROM public.activity_logs', 'SELECT * FROM public.alembic_version',
                          'SET ROLE crewflow_ci_migrator', 'ALTER ROLE crewflow_ci_runtime SUPERUSER',
                          'CREATE ROLE crewflow_ci_forbidden', 'DELETE FROM public.departments']:
            try:
                conn.execute(statement)
            except psycopg.errors.InsufficientPrivilege:
                denials.append({'statement': statement, 'sqlstate': '42501'})
            else:
                conn.rollback()
                raise RuntimeError('Unexpected privilege success; rolled back and stopped')
            conn.rollback()
    pathlib.Path(output).write_text(json.dumps({'pass': True, 'environment': 'Flask test client + real isolated PostgreSQL',
        'database': cfg['database'], 'revision': HEAD, 'migrator_owned_tables': owners,
        'runtime_role': runtime, 'psycopg_impl': psycopg.pq.__impl__, 'libpq_version': psycopg.pq.version(),
        'successful_signins': 3, 'http_network_or_tls_test': False, 'requests': events,
        'negative_privilege_tests': denials, 'committed_progress': 40}, indent=2) + '\n')


def host(args):
    if os.environ.get('DATABASE_URL') or os.environ.get('PGHOST'):
        raise ValueError('Unset external database target variables before running this helper')
    if args.local_approved:
        pg, app, net = ('crewflow-ci-pg-2e4e-20261105', 'crewflow-ci-smoke-2e4e-20261105',
                        'crewflow-ci-smoke-2e4e-net')
        database = 'crewflow_ci_2e4e_20261105'
    else:
        if os.environ.get('GITHUB_ACTIONS') != 'true':
            raise ValueError('Local execution requires explicit separately approved --local-approved')
        suffix = os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT']
        if not re.fullmatch(r'[0-9]+-[0-9]+', suffix):
            raise ValueError('Unexpected CI identifier')
        pg, app, net = (prefix + suffix for prefix in ['crewflow-ci-pg-', 'crewflow-ci-smoke-', 'crewflow-ci-net-'])
        database = 'crewflow_ci_' + suffix.replace('-', '_')
    guard_target(database, pg)
    def call(argv, **kwargs):
        return subprocess.check_output(argv, text=True, **kwargs).strip()
    for name in [pg, app]:
        if subprocess.run(['docker', 'container', 'inspect', name], capture_output=True).returncode == 0:
            raise ValueError('Resource conflict: ' + name)
    if subprocess.run(['docker', 'network', 'inspect', net], capture_output=True).returncode == 0:
        raise ValueError('Network conflict')
    out = pathlib.Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    private = pathlib.Path(tempfile.mkdtemp(prefix='crewflow-ci-private-', dir=args.private_parent))
    private.chmod(0o700)
    cfg = {k: secrets.token_hex(32) for k in ['crewflow_ci_setup', 'crewflow_ci_migrator',
                                            'crewflow_ci_runtime', 'signing_key', 'account_password']}
    cfg.update(pg=pg, database=database)
    file = private / 'config.json'
    file.write_text(json.dumps(cfg))
    file.chmod(0o600)
    env = private / 'postgres.env'
    env.write_text(f'POSTGRES_DB={database}\nPOSTGRES_USER=crewflow_ci_setup\n'
                   f'POSTGRES_PASSWORD={cfg["crewflow_ci_setup"]}\n')
    env.chmod(0o600)
    created = {}
    try:
        created['network'] = call(['docker', 'network', 'create', '--internal', net])
        created['postgres'] = call(['docker', 'run', '-d', '--name', pg, '--network', net,
                                   '--tmpfs', '/var/lib/postgresql/data:rw,noexec,nosuid,size=512m',
                                   '--env-file', str(env), PG_IMAGE])
        for _ in range(40):
            if subprocess.run(['docker', 'exec', pg, 'pg_isready', '-U', 'crewflow_ci_setup', '-d', database],
                              capture_output=True).returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError('New PostgreSQL service readiness timeout')
        result = subprocess.run(['docker', 'run', '--name', app, '--network', net, '--no-healthcheck',
            '--user', f'{os.getuid()}:{os.getgid()}', '--workdir', '/app/backend',
            '--mount', f'type=bind,src={file},dst=/run/ci-config.json,readonly',
            '--mount', f'type=bind,src={script_path()},dst=/run/postgres_smoke.py,readonly',
            '--mount', f'type=bind,src={out},dst=/evidence',
            '--entrypoint', 'python', args.image, '/run/postgres_smoke.py', 'inside',
            '/run/ci-config.json', '/evidence/postgres-smoke.json'], capture_output=True, text=True)
        # Never retain raw SQL/DSN/credential exceptions in public evidence.
        created['application'] = call(['docker', 'inspect', '--format', '{{.Id}}', app])
        if result.returncode:
            (private / 'failure.log').write_text(result.stdout + result.stderr)
            (private / 'failure.log').chmod(0o600)
            raise RuntimeError('Smoke failed; restricted private diagnostic retained')
    finally:
        (out / 'postgres-resources.json').write_text(json.dumps({
            'created_ids': created, 'database': database, 'image': args.image,
            'retained_locally': args.local_approved, 'storage': 'tmpfs; not durable across stop/reboot'}, indent=2))
        if not args.local_approved:
            # CI-only cleanup, strictly IDs created by this invocation.
            for key in ['application', 'postgres']:
                if key in created:
                    subprocess.run(['docker', 'rm', '-f', created[key]], check=True)
            if 'network' in created:
                subprocess.run(['docker', 'network', 'rm', created['network']], check=True)


def script_path():
    return pathlib.Path(__file__).resolve()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inside = sub.add_parser('inside')
    inside.add_argument('config')
    inside.add_argument('output')
    run = sub.add_parser('run')
    run.add_argument('--image', required=True)
    run.add_argument('--output', required=True)
    run.add_argument('--private-parent', required=True)
    run.add_argument('--local-approved', action='store_true')
    args = parser.parse_args()
    if args.command == 'inside':
        try:
            run_inside(args.config, args.output)
        except Exception as exc:
            # Class only: SQLAlchemy exceptions can include connection information.
            print('PostgreSQL smoke failed: ' + type(exc).__name__, file=sys.stderr)
            raise SystemExit(1) from None
    else:
        host(args)
