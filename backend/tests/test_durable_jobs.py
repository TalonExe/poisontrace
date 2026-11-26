from uuid import uuid4

import pytest

from poisontrace.application.principals import Principal, principal_scope
from poisontrace.bootstrap import build_backend
from poisontrace.config import WebConfig


def test_accepted_intent_is_durable_private_and_never_admitted_twice(tmp_path):
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    payload = dict(case_id='soc-auth-001', mode='clean', provider='scripted')
    intent = uuid4().hex
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit(intent, payload)
        assert job['status'] == 'queued'
        assert job['run_id'] is None
        assert backend.jobs.submit(intent, payload) == job
        with pytest.raises(ValueError, match='intent'):
            backend.jobs.submit(intent, {**payload, 'mode': 'defended', 'attack_family': 'description-poisoning'})
        with pytest.raises(RuntimeError, match='busy'):
            backend.jobs.submit(uuid4().hex, payload)
    reopened = build_backend(WebConfig(database=tmp_path/'runs.db'))
    with principal_scope(Principal(12, 'analyst')):
        assert reopened.jobs.list() == []
        with pytest.raises(KeyError):
            reopened.jobs.get(job['job_id'])
        with pytest.raises(RuntimeError, match='busy'):
            reopened.jobs.submit(intent, payload)
    with principal_scope(Principal(11, 'analyst')):
        assert reopened.jobs.get(job['job_id']) == job


def test_claim_completion_links_actual_run_and_restart_never_replays_active(tmp_path):
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit(uuid4().hex, dict(case_id='soc-auth-001', mode='clean', provider='scripted'))
    claim = backend.jobs.store.claim()
    assert claim is not None
    assert backend.jobs.store.claim() is None

    result = backend.jobs.execute_claim(claim)
    with pytest.raises(RuntimeError, match='already dispatched'):
        backend.jobs.execute_claim(claim)
    with principal_scope(Principal(11, 'analyst')):
        finished = backend.jobs.get(job['job_id'])
        assert finished['status'] == 'completed'
        assert finished['run_id'] == result.run_id
        assert backend.runs.get(result.run_id)['investigation']['scores']['decision_correctness'] is True
        next_job = backend.jobs.submit(uuid4().hex, dict(case_id='soc-auth-001', mode='clean', provider='scripted'))
    backend.jobs.store.claim()
    backend.jobs.store.reconcile()
    with principal_scope(Principal(11, 'analyst')):
        interrupted = backend.jobs.get(next_job['job_id'])
        assert interrupted['status'] == 'interrupted'
        assert interrupted['error_category'] == 'provider_outcome_uncertain'
        assert interrupted['run_id'] is None
        assert len(backend.runs.list()) == 1
    assert backend.jobs.store.claim() is None


def test_supervised_executor_completes_offline_mcp_without_request_connection(tmp_path):
    import time
    from poisontrace.adapters.execution.jobs import JobExecutor
    config = WebConfig(database=tmp_path/'runs.db')
    backend = build_backend(config)
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit(uuid4().hex, dict(case_id='soc-auth-001', mode='clean', provider='scripted'))
    with JobExecutor(config), JobExecutor(config):
        deadline = time.monotonic()+35
        while time.monotonic() < deadline:
            with principal_scope(Principal(11, 'analyst')):
                current = backend.jobs.get(job['job_id'])
            if current['status'] in ('completed', 'failed', 'interrupted'):
                break
            time.sleep(0.1)
        assert current['status'] == 'completed'
    with principal_scope(Principal(11, 'analyst')):
        assert backend.runs.get(current['run_id'])['status'] == 'completed'
        assert len(backend.runs.list()) == 1
    assert (tmp_path/'runs.db.executor.lock').stat().st_size == 1


def test_concurrent_admission_and_sqlite_contention_are_bounded(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import sqlite3
    import time
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    payload = dict(case_id='soc-auth-001', mode='clean', provider='scripted')
    intent = uuid4().hex
    def submit(key):
        with principal_scope(Principal(11, 'analyst')):
            try:
                return backend.jobs.submit(key, payload)
            except RuntimeError:
                return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        duplicates = list(pool.map(submit, [intent]*8))
    assert len({job['job_id'] for job in duplicates if job}) == 1
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(submit, [uuid4().hex for _ in range(8)])) == [None]*8
    backend.jobs.store.claim()
    backend.jobs.store.reconcile()
    connection = sqlite3.connect(backend.store.database)
    try:
        connection.execute('BEGIN IMMEDIATE')
        started = time.monotonic()
        assert submit(uuid4().hex) is None
        assert time.monotonic()-started < 2
    finally:
        connection.rollback()
        connection.close()
    assert submit(uuid4().hex)['status'] == 'queued'


def test_http_admission_is_prompt_bounded_private_and_reconnectable(tmp_path):
    import json
    import time
    from fastapi.testclient import TestClient
    from poisontrace.bootstrap import create_app, build_accounts
    from poisontrace.config import AccountSeed
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    password = uuid4().hex
    build_accounts(backend.store.database, seeds=(AccountSeed('alice', 'analyst', password), AccountSeed('bob', 'analyst', password), AccountSeed('admin', 'superadmin', password)))
    app = create_app(backend)
    client = TestClient(app)
    assert client.post('/api/auth/login', json=dict(username='alice', passcode=password)).status_code == 200
    payload = dict(case_id='soc-auth-001', mode='clean', provider='scripted')
    headers = {'Idempotency-Key': uuid4().hex}
    started = time.monotonic()
    accepted = client.post('/api/investigation-jobs', json=payload, headers=headers)
    assert accepted.status_code == 202
    assert time.monotonic()-started < 2
    assert client.post('/api/investigation-jobs', json=payload, headers=headers).json() == accepted.json()
    assert client.post('/api/investigation-jobs', json=payload, headers={'Idempotency-Key': uuid4().hex}).status_code == 409
    assert client.post('/api/runs', json={**payload, 'workflow': 'mcp-investigation-v1'}).status_code == 400
    for value in ({**payload, 'owner_id': 999}, {**payload, 'model': 'x'*201}, ['secret']):
        rejected = client.post('/api/investigation-jobs', json=value, headers={'Idempotency-Key': uuid4().hex})
        assert rejected.status_code in (400,422)
        assert 'secret' not in rejected.text
    assert client.post('/api/investigation-jobs', content=json.dumps({'data':'x'*4097}), headers=headers).status_code == 413
    client.close()
    claim = backend.jobs.store.claim()
    backend.jobs.execute_claim(claim)
    other = TestClient(app)
    assert other.post('/api/auth/login', json=dict(username='bob', passcode=password)).status_code == 200
    path = '/api/investigation-jobs/'+accepted.json()['job_id']
    assert other.get(path).status_code == 404
    assert other.get('/api/investigation-jobs').json() == []
    other.post('/api/auth/login', json=dict(username='admin', passcode=password))
    assert other.get(path).status_code == 403
    other.post('/api/auth/login', json=dict(username='alice', passcode=password))
    reopened = other.get(path).json()
    assert reopened['status'] == 'completed'
    assert other.get('/api/runs/'+str(reopened['run_id'])).json()['status'] == 'completed'


def test_executor_termination_and_hard_timeout_reconcile_without_replay(tmp_path):
    import time
    from poisontrace.adapters.execution.jobs import JobExecutor
    config = WebConfig(database=tmp_path/'runs.db')
    backend = build_backend(config)
    with principal_scope(Principal(11, 'analyst')):
        first = backend.jobs.submit(uuid4().hex, dict(case_id='soc-auth-001', mode='clean', provider='scripted'))
    with JobExecutor(config, deadline_seconds=0.001):
        deadline = time.monotonic()+25
        while time.monotonic() < deadline:
            with principal_scope(Principal(11, 'analyst')):
                status = backend.jobs.get(first['job_id'])
            if status['status'] == 'interrupted':
                break
            time.sleep(0.1)
        assert status['status'] == 'interrupted'
        assert status['run_id'] is None
        assert status['error_category'] == 'provider_outcome_uncertain'
    with principal_scope(Principal(11, 'analyst')):
        assert backend.runs.list() == []
        assert backend.jobs.submit(uuid4().hex, dict(case_id='soc-auth-001', mode='clean', provider='scripted'))['status'] == 'queued'


def test_killed_executor_cleans_real_mcp_children_before_reconciliation(tmp_path):
    import time
    from process_helpers import children_of, process_exists
    from poisontrace.adapters.execution.jobs import JobExecutor
    config = WebConfig(database=tmp_path/'runs.db')
    backend = build_backend(config)
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit(uuid4().hex, dict(case_id='soc-auth-001', mode='clean', provider='scripted'))
    with JobExecutor(config) as executor:
        children = []
        deadline = time.monotonic()+20
        while time.monotonic() < deadline:
            process = executor.process
            if process is not None and process.pid:
                children = children_of(process.pid)
                if len(children) >= 2:
                    process.kill()
                    break
            time.sleep(0.01)
        assert len(children) >= 2
        deadline = time.monotonic()+20
        while time.monotonic() < deadline:
            with principal_scope(Principal(11, 'analyst')):
                status = backend.jobs.get(job['job_id'])
            if status['status'] == 'interrupted' and all(not process_exists(pid) for pid in children):
                break
            time.sleep(0.05)
        assert status['status'] == 'interrupted'
        assert status['run_id'] is None
        assert all(not process_exists(pid) for pid in children)


@pytest.mark.parametrize('failure', ['timeout', 'provider'])
def test_job_failures_keep_safe_unscored_results_and_close_provider(tmp_path, failure):
    import asyncio
    from cryptography.fernet import Fernet
    from poisontrace.adapters.secrets.storage import EncryptedSqliteSecrets
    from poisontrace.adapters.models.scripted_investigation import ScriptedInvestigationModel
    closed = []
    class Model(ScriptedInvestigationModel):
        async def next_step(self, *args):
            if failure == 'timeout':
                await asyncio.sleep(10)
            raise RuntimeError('synthetic-provider-secret-must-not-escape')
        async def aclose(self):
            closed.append(True)
    config = WebConfig(database=tmp_path/'runs.db')
    secrets = EncryptedSqliteSecrets(tmp_path/'secrets.db', Fernet.generate_key())
    backend = build_backend(config, secrets, investigation_model_factory=lambda *args: Model())
    backend.runs.investigations.timeout_seconds = 5 if failure == 'timeout' else 20
    with principal_scope(Principal(11, 'analyst')):
        credential = backend.credentials.save(dict(provider='openai', secret=Fernet.generate_key().decode()))
        accepted = backend.jobs.submit(uuid4().hex, dict(case_id='soc-auth-001', mode='clean', provider='openai', model='offline-substitute', credential_id=credential['credential_id']))
    claim = backend.jobs.store.claim()
    backend.jobs.execute_claim(claim)
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.get(accepted['job_id'])
        assert job['status'] == 'failed'
        assert job['error_category'] == ('investigation_time_limit' if failure == 'timeout' else 'investigation_execution_error')
        detail = backend.runs.get(job['run_id'])
        assert detail['investigation']['scores']['decision_correctness'] is None
        assert 'synthetic-provider-secret-must-not-escape' not in str(detail)
    assert closed == [True]
