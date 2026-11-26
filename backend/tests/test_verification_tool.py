import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import socket
import time


PROJECT = Path(__file__).resolve().parents[2]
TOOL = PROJECT / 'scripts/verify.py'


def verification():
    spec = importlib.util.spec_from_file_location('verification_tool', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_complete_plan_keeps_all_required_checks_and_one_build():
    result = subprocess.run([sys.executable, str(TOOL), 'complete', '--plan'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert [check['name'] for check in plan['checks']] == [
        'tool-tests', 'static', 'pip', 'frontend-unit', 'build', 'backend',
        'mocked', 'connected', 'production-local', 'production-hosted', 'whitespace',
    ]
    assert plan['fresh'] is True
    assert 'Linux container execution' in plan['gaps']


def test_source_identity_excludes_runtime_locks_but_includes_dependency_locks(tmp_path):
    runtime_lock = tmp_path / 'poisontrace.db.executor.lock'
    runtime_lock.write_bytes(b'synthetic runtime lock')
    dependency_lock = tmp_path / 'requirements-runtime.lock'
    dependency_lock.write_text('synthetic dependency lock')

    identity = verification().source_identity(tmp_path)

    assert set(identity['files']) == {'requirements-runtime.lock'}


def test_failed_check_blocks_only_dependents_and_preserves_full_logs(tmp_path, monkeypatch):
    monkeypatch.setenv('POISONTRACE_VERIFY_NODE', 'outer-run-node-must-not-enter-fixture')
    checks = [
        {'name': 'build', 'command': [sys.executable, '-c', "print('full synthetic diagnostic'); raise SystemExit(7)"]},
        {'name': 'browser', 'command': [sys.executable, '-c', "raise SystemExit(99)"], 'requires': ['build']},
        {'name': 'independent', 'command': [sys.executable, '-c', "print('still ran')"]},
    ]
    summary = verification().execute_plan(tmp_path, tmp_path/'artifacts', checks)
    assert [(r['name'], r['status'], r['exit_code']) for r in summary['checks']] == [
        ('build', 'failed', 7), ('browser', 'not run', None), ('independent', 'passed', 0),
    ]
    assert 'full synthetic diagnostic' in (tmp_path/'artifacts/build.log').read_text()
    saved = json.loads((tmp_path/'artifacts/summary.json').read_text())
    assert saved['status'] == 'failed'
    assert saved['checks'][0]['duration_seconds'] >= 0


def test_timeout_removes_descendants_but_keeps_unrelated_process(tmp_path):
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
    listener.close()
    code = f"import socket,time; s=socket.socket(); s.bind(('127.0.0.1',{port})); s.listen(); time.sleep(60)"
    parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{code!r}]); time.sleep(60)"
    sentinel = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    try:
        summary = verification().execute_plan(tmp_path, tmp_path/'artifacts', [
            {'name': 'timeout', 'command': [sys.executable, '-c', parent], 'timeout': 1},
        ])
        assert summary['checks'][0]['reason'] == 'Timeout'
        assert summary['checks'][0]['status'] == 'failed'
        assert sentinel.poll() is None
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    finally:
        sentinel.terminate()
        sentinel.wait(timeout=5)


def test_cancellation_records_interrupted_and_not_run(tmp_path):
    started = time.monotonic()
    summary = verification().execute_plan(tmp_path, tmp_path/'artifacts', [
        {'name': 'active', 'command': [sys.executable, '-c', 'import time; time.sleep(60)']},
        {'name': 'later', 'command': [sys.executable, '-c', 'raise SystemExit(99)']},
    ], cancelled=lambda: time.monotonic()-started > 0.3)
    assert summary['status'] == 'interrupted'
    assert [r['status'] for r in summary['checks']] == ['interrupted', 'not run']


def test_development_selection_is_explained_and_overrides_keep_build_dependency():
    tool = verification()
    plan = tool.select_checks('dev', ['frontend/src/utils/auth.js'])
    assert set(plan['selected']) == {'static', 'frontend-unit', 'build', 'mocked', 'connected', 'production-local', 'production-hosted', 'whitespace'}
    assert plan['reasons']['connected']
    assert tool.select_checks('dev', ['docs/STATUS.md'])['selected'] == ['whitespace']
    assert tool.select_checks('dev', ['unknown-input'])['selected'] == list(tool.CHECKS)
    assert tool.select_checks('dev', [], overrides=['connected'])['selected'] == ['build', 'connected']


def test_occupied_port_is_reported_without_touching_existing_server(tmp_path):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        port = listener.getsockname()[1]
        summary = verification().execute_plan(tmp_path, tmp_path/'artifacts', [
            {'name': 'browser', 'command': [sys.executable, '-c', 'raise SystemExit(99)'], 'ports': [port]},
            {'name': 'other', 'command': [sys.executable, '-c', 'pass']},
        ])
        assert summary['checks'][0]['status'] == 'failed'
        assert 'occupied' in summary['checks'][0]['reason']
        assert summary['checks'][1]['status'] == 'passed'
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            pass


def test_appended_debug_bytes_are_archived_completely_before_restoration(tmp_path):
    (tmp_path/'frontend').mkdir()
    (tmp_path/'debug.log').write_bytes(b'entry\x00\xff')
    (tmp_path/'frontend/debug.log').write_bytes(b'frontend-entry')
    tool = verification()
    summary = tool.execute_plan(tmp_path, tmp_path/'artifacts', [{
        'name': 'append', 'command': [sys.executable, '-c',
            "from pathlib import Path; p=Path('debug.log'); p.write_bytes(p.read_bytes()+b'\\x01appended\\xff')"],
    }])
    assert (tmp_path/'debug.log').read_bytes() == b'entry\x00\xff'
    record = summary['debug_logs']['debug.log']
    assert record['restored'] is True
    assert Path(record['archive']).read_bytes() == b'entry\x00\xff\x01appended\xff'
    assert (tmp_path/'frontend/debug.log').read_bytes() == b'frontend-entry'


def test_debug_rewrite_is_preserved_and_fails_the_run(tmp_path):
    (tmp_path/'debug.log').write_bytes(b'entry')
    summary = verification().execute_plan(tmp_path, tmp_path/'artifacts', [{
        'name': 'rewrite', 'command': [sys.executable, '-c', "from pathlib import Path; Path('debug.log').write_bytes(b'changed')"],
    }])
    assert summary['status'] == 'failed'
    assert (tmp_path/'debug.log').read_bytes() == b'changed'
    assert summary['debug_logs']['debug.log']['restored'] is False


def test_browser_rejects_a_build_replaced_after_success(tmp_path):
    dist = tmp_path/'frontend/dist'
    dist.mkdir(parents=True)
    (dist/'index.html').write_text('old')
    summary = verification().execute_plan(tmp_path, tmp_path/'artifacts', [
        {'name': 'build', 'command': [sys.executable, '-c', "from pathlib import Path; Path('frontend/dist/index.html').write_text('built')"], 'record_build': True},
        {'name': 'replace', 'command': [sys.executable, '-c', "from pathlib import Path; Path('frontend/dist/index.html').write_text('wrong')"]},
        {'name': 'browser', 'command': [sys.executable, '-c', 'pass'], 'requires': ['build'], 'verify_build': True},
    ])
    assert summary['checks'][2]['status'] == 'failed'
    assert 'build' in summary['checks'][2]['reason']


def test_startup_failure_does_not_run_browser_and_does_not_cascade(tmp_path):
    summary = verification().execute_plan(tmp_path, tmp_path/'artifacts', [
        {'name': 'browser', 'command': [sys.executable, '-c', 'raise SystemExit(99)'], 'servers': [
            {'name': 'dead', 'command': [sys.executable, '-c', 'raise SystemExit(8)'],
             'url': 'http://127.0.0.1:1/', 'shutdown': 'http://127.0.0.1:1/'}]},
        {'name': 'independent', 'command': [sys.executable, '-c', 'pass']},
    ])
    assert summary['checks'][0]['status'] == 'failed'
    assert 'readiness' in summary['checks'][0]['reason']
    assert summary['checks'][0]['exit_code'] is None
    assert summary['checks'][1]['status'] == 'passed'


def test_readiness_timeout_cleans_owned_server_then_next_check_runs(tmp_path):
    summary = verification().execute_plan(tmp_path, tmp_path/'artifacts', [
        {'name': 'unready', 'timeout': 0.3, 'command': [sys.executable, '-c', 'raise SystemExit(99)'], 'servers': [
            {'name': 'waiting', 'command': [sys.executable, '-c', 'import time; time.sleep(60)'],
             'url': 'http://127.0.0.1:1/', 'shutdown': 'http://127.0.0.1:1/'}]},
        {'name': 'next', 'command': [sys.executable, '-c', 'pass']},
    ])
    assert summary['checks'][0]['status'] == 'failed'
    assert summary['checks'][0]['duration_seconds'] < 5
    assert summary['checks'][1]['status'] == 'passed'


def test_ready_server_has_owned_listener_and_cleanup_closes_port(tmp_path):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    summary = verification().execute_plan(tmp_path, tmp_path/'artifacts', [{
        'name': 'drive', 'ports': [port], 'command': [sys.executable, '-c', 'pass'],
        'servers': [{'name': 'synthetic', 'command': [sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1'],
                     'url': origin, 'shutdown': origin + '/__test_shutdown'}],
    }])
    assert summary['checks'][0]['servers'][0]['listener_owned'] is True
    assert summary['checks'][0]['ports_closed'] is True
