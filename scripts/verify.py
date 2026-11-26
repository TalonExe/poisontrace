import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import socket
import ssl
import signal
import shutil
import sys
import threading
import time
import urllib.request
import urllib.parse
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verification_process import OwnedProcess
from verification_state import DebugLogs, build_identity, git, run_lock, source_identity
from verification_static import annotation_snapshot


CHECKS = ('tool-tests', 'static', 'pip', 'frontend-unit', 'build', 'backend', 'mocked',
          'connected', 'production-local', 'production-hosted', 'whitespace')
GAPS = ['Linux container execution', 'Actual-host proxy, capacity, backup/restore and release gates',
        'Live-provider effectiveness']
BROWSERS = ('mocked', 'connected', 'production-local', 'production-hosted')


def select_checks(mode, changed, *, overrides=()):
    reasons = {}

    def add(names, reason):
        for name in names:
            reasons.setdefault(name, []).append(reason)

    if overrides:
        add(overrides, 'Explicit focused override')
        if any(name in BROWSERS for name in overrides):
            add(['build'], 'Browser checks require a fresh intended build')
    elif mode == 'complete':
        add(CHECKS, 'Complete verification always runs fresh')
    else:
        add(['whitespace'], 'Every development run checks the whole tracked diff')
        for name in changed:
            if name in ('debug.log', 'frontend/debug.log') or name.startswith(('docs/', '.agents/', '.claude/', '.codex/', '.cursor/', '.pi/')) or name.endswith('.md'):
                continue
            if name in ('scripts/verify.py', 'scripts/verify_ui.py', 'backend/tests/test_verification_tool.py', 'backend/tests/test_visual_capture.py') or name.startswith('scripts/verification_'):
                add(['tool-tests', 'static'], name + ' changes verification orchestration')
            elif name.startswith('frontend/src/tests/'):
                add(['frontend-unit'], name)
            elif name.startswith('frontend/e2e/'):
                family = 'connected' if '/connected/' in name else 'production' if '/production/' in name else 'mocked'
                add(['build', 'static', *(['production-local', 'production-hosted'] if family == 'production' else [family])], name)
            elif name.startswith('frontend/'):
                add(['static', 'frontend-unit', 'build', *BROWSERS], name + ' can affect shared browser behavior')
            elif name.startswith('backend/tests/test_') and name != 'backend/tests/test_verification_tool.py':
                add(['backend', 'static'], name + ' requires the complete backend contract')
            elif name.startswith('backend/'):
                add(['static', 'backend', 'build', 'connected', 'production-local', 'production-hosted'], name + ' can affect HTTP/MCP/production composition')
            else:
                add(CHECKS, name + ' has broad or unknown dependencies')
    return {'selected': [name for name in CHECKS if name in reasons], 'reasons': reasons}


def require_free_ports(ports):
    for port in ports:
        with socket.socket() as probe:
            if os.name == 'nt':
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                probe.bind(('127.0.0.1', port))
            except OSError as error:
                raise RuntimeError(f'Port {port} occupied; existing process left untouched') from error


def save_summary(artifact, summary):
    temporary = artifact / 'summary.pending'
    temporary.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    temporary.replace(artifact / 'summary.json')


def http_request(url, *, method='GET'):
    context = ssl._create_unverified_context() if url.startswith('https://127.0.0.1:') else None
    request = urllib.request.Request(url, method=method, headers={'Origin': url.rsplit('/', 1)[0]})
    with urllib.request.urlopen(request, timeout=1, context=context) as response:
        return response.status


def wait_ready(owned, url, cancelled, timeout=30):
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        if cancelled():
            raise KeyboardInterrupt
        if owned.process.poll() is not None:
            raise RuntimeError('Owned server exited before readiness')
        try:
            if http_request(url) == 200:
                return
        except (OSError, ValueError):
            pass
        time.sleep(0.1)
    raise RuntimeError('Owned server readiness timed out')


def execute_plan(root, artifact, checks, *, env=None, cancelled=lambda: False):
    root, artifact = Path(root).resolve(), Path(artifact).resolve()
    artifact.mkdir(parents=True, exist_ok=False)
    summary = {'status': 'running', 'checks': [], 'platform': sys.platform, 'evidence': 'fresh'}
    summary['started_at'] = datetime.now(timezone.utc).isoformat()
    debug = DebugLogs(root, artifact)
    started = time.monotonic()
    try:
        summary['source'] = source_identity(root)
        environment = dict(env) if env is not None else {
            key: value for key, value in os.environ.items() if not key.startswith('POISONTRACE_VERIFY_')}
        baseline = artifact / 'annotations-entry.json'
        baseline.write_text(json.dumps(annotation_snapshot(root)), encoding='utf-8')
        environment['POISONTRACE_VERIFY_BASELINE'] = str(baseline)
        if environment.get('POISONTRACE_VERIFY_NODE'):
            js_baseline = artifact / 'frontend-annotations-entry.json'
            subprocess.run([environment['POISONTRACE_VERIFY_NODE'], str(root/'scripts/verification_annotations.mjs'),
                            'snapshot', str(js_baseline)], cwd=root, env=environment, check=True, capture_output=True)
            environment['POISONTRACE_VERIFY_JS_BASELINE'] = str(js_baseline)
        save_summary(artifact, summary)
        execute_checks(root, artifact, checks, summary, environment, cancelled)
    except KeyboardInterrupt:
        summary['status'] = 'interrupted'
    except Exception as error:
        summary.update(status='failed', error=str(error))
    finally:
        recorded = {r['name'] for r in summary['checks']}
        for check in checks:
            if check['name'] not in recorded:
                summary['checks'].append(dict(name=check['name'], command=check['command'],
                    status='not run', exit_code=None, duration_seconds=0, reason='Run stopped before this check'))
        summary['debug_logs'] = debug.restore()
        if not all(record['restored'] for record in summary['debug_logs'].values()):
            summary['status'] = 'failed'
        try:
            summary['source_stable'] = source_identity(root)['sha256'] == summary['source']['sha256']
            if not summary['source_stable']:
                summary.update(status='failed', reason='Verification inputs changed during execution')
        except Exception as error:
            summary.update(status='failed', source_error=str(error))
        summary['duration_seconds'] = round(time.monotonic() - started, 3)
        summary['finished_at'] = datetime.now(timezone.utc).isoformat()
        save_summary(artifact, summary)
    return summary


def execute_checks(root, artifact, checks, summary, environment, cancelled):
    interrupted = False
    for check in checks:
        result = dict(name=check['name'], command=check['command'], exit_code=None,
                      cwd=str(check.get('cwd', root)), timeout_seconds=check.get('timeout', 120),
                      requires=check.get('requires', []), status='not run', duration_seconds=0,
                      log=str(artifact / (check['name'] + '.log')))
        summary['checks'].append(result)
        if not check.get('selected', True):
            result['reason'] = 'Not selected for focused verification'
            continue
        if interrupted:
            result['reason'] = 'Run interrupted'
            continue
        if any(not any(r['name'] == name and r['status'] == 'passed' for r in summary['checks'])
               for name in check.get('requires', [])):
            result['reason'] = 'Prerequisite did not pass'
            continue
        started = time.monotonic()
        owned = None
        servers = []
        check_env = {**environment, **check.get('env', {})}
        try:
            if cancelled():
                raise KeyboardInterrupt
            require_free_ports(check.get('ports', []))
            if check.get('verify_build'):
                if summary.get('build') != build_identity(root) or source_identity(root)['sha256'] != summary['source']['sha256']:
                    raise RuntimeError('Intended frontend build or source changed after build')
            if check_env.get('POISONTRACE_VERIFY_ARTIFACT'):
                Path(check_env['POISONTRACE_VERIFY_ARTIFACT']).mkdir(parents=True, exist_ok=True)
            with Path(result['log']).open('wb') as log:
                for server in check.get('servers', []):
                    stream = (artifact / (check['name'] + '-' + server['name'] + '.log')).open('wb')
                    try:
                        process = OwnedProcess(server['command'], cwd=server.get('cwd', root), env=check_env, log=stream)
                    except BaseException:
                        stream.close()
                        raise
                    servers.append((process, stream, server))
                    result.setdefault('servers', []).append(dict(name=server['name'], command=server['command'],
                        pid=process.process.pid, ready_url=server['url'], log=stream.name, listener_owned=False))
                    wait_ready(process, server['url'], cancelled,
                               timeout=min(30, max(0.1, check.get('timeout', 120) - (time.monotonic() - started))))
                    if not process.owns_port(urllib.parse.urlsplit(server['url']).port):
                        raise RuntimeError('Ready listener is not owned by this server tree')
                    result['servers'][-1]['listener_owned'] = True
                owned = OwnedProcess(check['command'], cwd=check.get('cwd', root), env=check_env, log=log)
                result['pid'] = owned.process.pid
                result['status'] = 'running'
                save_summary(artifact, summary)
                while owned.process.poll() is None:
                    if cancelled():
                        raise KeyboardInterrupt
                    if time.monotonic() - started > check.get('timeout', 120):
                        raise subprocess.TimeoutExpired(check['command'], check.get('timeout', 120))
                    time.sleep(0.05)
                result['exit_code'] = owned.process.returncode
                result['status'] = 'passed' if result['exit_code'] == 0 else 'failed'
                if check.get('record_build') and result['status'] == 'passed':
                    summary['build'] = build_identity(root)
        except subprocess.TimeoutExpired:
            result.update(status='failed', reason='Timeout')
        except KeyboardInterrupt:
            result.update(status='interrupted', reason='Interrupted')
            interrupted = True
        except Exception as error:
            result.update(status='failed', reason=str(error))
        finally:
            if owned:
                try:
                    owned.close()
                except Exception as error:
                    result.update(status='failed', cleanup_error=str(error))
            for process, stream, server in reversed(servers):
                try:
                    if process.process.poll() is None:
                        try:
                            if not process.owns_port(urllib.parse.urlsplit(server['url']).port):
                                raise ValueError('Owned server no longer owns its listener; shutdown request withheld')
                            http_request(server['shutdown'], method='POST')
                            process.process.wait(timeout=15)
                        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                            result.update(status='failed', graceful_cleanup_error=str(error))
                    process.close()
                    for record in result.get('servers', []):
                        if record['pid'] == process.process.pid:
                            record['exit_code'] = process.process.returncode
                except Exception as error:
                    result.update(status='failed', cleanup_error=str(error))
                finally:
                    stream.close()
            if servers:
                try:
                    require_free_ports(check.get('ports', []))
                    result['ports_closed'] = True
                except RuntimeError as error:
                    result.update(status='failed', cleanup_error=str(error), ports_closed=False)
            if check_env.get('POISONTRACE_VERIFY_STATE'):
                state = Path(check_env['POISONTRACE_VERIFY_STATE']).resolve()
                try:
                    if not state.is_relative_to(artifact) or state == artifact:
                        raise RuntimeError('Synthetic state cleanup must stay inside the run artifact')
                    if state.exists():
                        shutil.rmtree(state)
                    result['synthetic_state_removed'] = True
                except Exception as error:
                    result.update(status='failed', cleanup_error=str(error))
            result['duration_seconds'] = round(time.monotonic() - started, 3)
            print(f"{result['name']}: {result['status']} ({result['duration_seconds']:.1f}s)", flush=True)
            save_summary(artifact, summary)
    summary['status'] = 'interrupted' if interrupted else ('passed' if all(
        result['status'] == 'passed' for result, check in zip(summary['checks'], checks)
        if check.get('selected', True)) else 'failed')


def application_checks(root, artifact, node, selection):
    python = str(root / ('.venv/Scripts/python.exe' if os.name == 'nt' else '.venv/bin/python'))
    frontend = root / 'frontend'
    commands = {
        'tool-tests': [python, '-m', 'pytest', '-q', 'backend/tests/test_verification_tool.py', 'backend/tests/test_visual_capture.py'],
        'static': [python, str(root/'scripts/verification_static.py')],
        'pip': [python, '-m', 'pip', 'check'],
        'frontend-unit': [node, '--test', 'src/tests/*.test.js'],
        'build': [node, 'node_modules/vite/bin/vite.js', 'build'],
        'backend': [python, '-m', 'pytest', '-q'],
        'whitespace': ['git', '-c', 'safe.directory=' + root.as_posix(), 'diff', '--check'],
    }
    result = []
    for name in CHECKS:
        check = dict(name=name, selected=name in selection['selected'], timeout=1200 if name == 'backend' else 300,
                     command=commands.get(name, [node, 'node_modules/@playwright/test/cli.js', 'test',
                                                '--config=playwright.verification.config.js']),
                     cwd=str(frontend if name in (*BROWSERS, 'frontend-unit', 'build') else root))
        if name == 'build':
            check['record_build'] = True
        if 'tool-tests' in selection['selected'] and name in ('frontend-unit', 'build', 'backend', *BROWSERS):
            check['requires'] = ['tool-tests']
        if name in BROWSERS:
            check['verify_build'] = True
            family = name if name in ('mocked', 'connected') else 'production'
            evidence = artifact / name
            state = artifact / (name + '-state')
            check.update(requires=[*check.get('requires', []), 'build'], env=dict(POISONTRACE_VERIFY_FAMILY=family,
                         POISONTRACE_VERIFY_ARTIFACT=str(evidence), POISONTRACE_VERIFY_STATE=str(state),
                         POISONTRACE_TEST_CONTENT_PROFILE='hosted' if name == 'production-hosted' else 'local',
                         POISONTRACE_TEST_PYTHON=python))
            servers = []
            if family in ('mocked', 'connected'):
                port = 4173 if family == 'mocked' else 4174
                origin = f'http://127.0.0.1:{port}'
                servers.append(dict(name='preview', command=[node, 'e2e/connected/preview.mjs', str(port)],
                                    cwd=str(frontend), url=origin, shutdown=origin + '/__test_shutdown'))
                check['ports'] = [port]
                if family == 'connected':
                    servers.insert(0, dict(name='api', command=[python, str(root/'backend/tests/mcp_browser_api.py')],
                                           url='http://127.0.0.1:4175/openapi.json',
                                           shutdown='http://127.0.0.1:4175/__test_shutdown'))
                    check['ports'].append(4175)
            else:
                origin = ('https' if name == 'production-hosted' else 'http') + '://127.0.0.1:4176'
                servers.append(dict(name='production', command=[python, str(root/'backend/tests/production_browser_api.py')],
                                    url=origin + '/health/ready', shutdown=origin + '/__test_shutdown'))
                check['ports'] = [4176]
            check['servers'] = servers
        result.append(check)
    return result


def clean_environment(node):
    prefixes = ('POISONTRACE_', 'OPENAI_', 'GOOGLE_', 'GEMINI_', 'ANTHROPIC_', 'AZURE_OPENAI_', 'PYTHON')
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith(prefixes)}
    env.update(PATH=str(Path(node).parent) + os.pathsep + os.environ.get('PATH', ''),
               PYTHONUTF8='1', PYTHONUNBUFFERED='1', NO_COLOR='1')
    return env


def main(argv=None):
    parser = argparse.ArgumentParser(description='Isolated offline PoisonTrace verification')
    parser.add_argument('mode', choices=('dev', 'complete', 'doctor'))
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--check', action='append', choices=CHECKS, default=[])
    parser.add_argument('--changed', action='append', default=[])
    parser.add_argument('--node', default=os.environ.get('POISONTRACE_VERIFY_NODE',
        r'C:\Users\TalonExe\AppData\Local\OpenAI\Codex\runtimes\cua_node\989c7523a11c09b9\bin\node.exe'))
    parser.add_argument('--artifacts', type=Path)
    args = parser.parse_args(argv)
    if args.mode == 'complete' and (args.check or args.changed):
        parser.error('Complete mode does not accept focused overrides')
    root = Path(__file__).resolve().parents[1]
    if args.mode == 'doctor':
        require_free_ports([4173, 4174, 4175, 4176])
        identity = source_identity(root)
        print(json.dumps(dict(platform=sys.platform, source_sha256=identity['sha256'], head=identity.get('head'),
                             branch=identity.get('branch'), source_files=len(identity['files']),
                             ports='closed', python=sys.version.split()[0],
                             node=subprocess.check_output([args.node, '--version']).decode().strip()), indent=2))
        return 0
    changed = args.changed or [line[3:] for line in git(root, 'status', '--porcelain=v1', '-uall').decode().splitlines()]
    selection = select_checks(args.mode, changed, overrides=args.check)
    if args.plan:
        print(json.dumps(dict(checks=[dict(name=name) for name in selection['selected']],
                              selection=selection, fresh=True, gaps=GAPS), indent=2))
        return 0
    if os.name != 'nt':
        parser.error('Execution is verified only on Windows; Linux container verification remains separate')
    artifact = (args.artifacts or root / '.scratch' / ('verify-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:8])).resolve()
    if artifact.exists():
        parser.error('Artifact directory must be new')
    with run_lock(root):
        node_version = subprocess.check_output([args.node, '--version']).decode().strip()
        env = clean_environment(args.node)
        env['POISONTRACE_VERIFY_NODE'] = args.node
        checks = application_checks(root, artifact, args.node, selection)
        stopping = threading.Event()
        for name in ('SIGINT', 'SIGTERM', 'SIGBREAK'):
            if hasattr(signal, name):
                signal.signal(getattr(signal, name), lambda *unused: stopping.set())
        summary = execute_plan(root, artifact, checks, env=env,
                               cancelled=lambda: stopping.is_set() or (artifact/'cancel.request').exists())
        summary.update(mode=args.mode, selection=selection, gaps=GAPS, node_version=node_version,
                       complete=args.mode == 'complete' and summary['status'] == 'passed')
        save_summary(artifact, summary)
        print(f"{summary['status']}: {artifact / 'summary.json'}", flush=True)
        return 130 if summary['status'] == 'interrupted' else 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
