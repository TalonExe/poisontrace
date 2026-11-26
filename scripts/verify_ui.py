import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify import application_checks, clean_environment, execute_plan, save_summary
from verification_state import run_lock


def validate_route(route):
    if not re.fullmatch(r'/[A-Za-z0-9/_-]*', route) or route.startswith(('//', '/api', '/__test')):
        raise ValueError('route must be an application path without origin, query, fragment or control endpoints')
    return route


def capture_plan(root, artifact, node, *, routes, viewports, role, profile):
    for route in routes:
        validate_route(route)
    selected = 'production-' + profile
    existing = application_checks(root, artifact, node, {'selected': ['build', selected]})
    build = next(c for c in existing if c['name'] == 'build')
    capture = next(c for c in existing if c['name'] == selected)
    capture.update(name='capture', command=[node, str(root/'scripts/verification_capture.mjs'),
                   '--origin', ('https' if profile == 'hosted' else 'http') + '://127.0.0.1:4176',
                   '--output', str(artifact/'capture'), '--role', role])
    for route in routes:
        capture['command'].extend(['--route', route])
    for viewport in viewports:
        capture['command'].extend(['--viewport', viewport])
    capture['env']['POISONTRACE_VERIFY_ARTIFACT'] = str(artifact/'capture')
    return dict(checks=[build, capture], capture=dict(routes=routes, viewports=viewports, role=role, profile=profile))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Capture synthetic live PoisonTrace UI at desktop/mobile sizes')
    parser.add_argument('--route', action='append')
    parser.add_argument('--viewport', action='append', choices=('desktop', 'mobile'))
    parser.add_argument('--role', choices=('analyst', 'superadmin', 'anonymous'), default='analyst')
    parser.add_argument('--profile', choices=('local', 'hosted'), default='local')
    parser.add_argument('--node', default=os.environ.get('POISONTRACE_VERIFY_NODE',
        r'C:\Users\TalonExe\AppData\Local\OpenAI\Codex\runtimes\cua_node\989c7523a11c09b9\bin\node.exe'))
    parser.add_argument('--artifacts', type=Path)
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    artifact = (args.artifacts or root/'.scratch'/('ui-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:8])).resolve()
    routes = args.route or {'analyst': ['/sessions', '/dashboard/single', '/results/runs'],
                           'superadmin': ['/admin/users'], 'anonymous': ['/login']}[args.role]
    try:
        plan = capture_plan(root, artifact, args.node, routes=list(dict.fromkeys(routes)),
            viewports=list(dict.fromkeys(args.viewport or ['desktop', 'mobile'])), role=args.role, profile=args.profile)
    except ValueError as error:
        parser.error(str(error))
    if args.plan:
        print(json.dumps(plan, indent=2))
        return 0
    if os.name != 'nt':
        parser.error('Capture orchestration is verified only on Windows')
    if artifact.exists():
        parser.error('Artifact directory must be new')
    stopping = threading.Event()
    for name in ('SIGINT', 'SIGTERM', 'SIGBREAK'):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *unused: stopping.set())
    with run_lock(root):
        version = subprocess.check_output([args.node, '--version']).decode().strip()
        env = clean_environment(args.node)
        env['POISONTRACE_VERIFY_NODE'] = args.node
        summary = execute_plan(root, artifact, plan['checks'], env=env,
            cancelled=lambda: stopping.is_set() or (artifact/'cancel.request').exists())
        summary.update(mode='visual-capture', complete=False, capture=plan['capture'], node_version=version)
        save_summary(artifact, summary)
        print(f"{summary['status']}: {artifact/'summary.json'}", flush=True)
        return 130 if summary['status'] == 'interrupted' else 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
