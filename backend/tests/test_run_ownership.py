from job_helpers import complete_application_group
"""Run privacy through trusted application and authenticated HTTP interfaces."""
from job_helpers import complete_investigation
from pathlib import Path

import pytest

from poisontrace.application.principals import Principal, principal_scope
from poisontrace.bootstrap import build_backend
from poisontrace.config import WebConfig
from poisontrace.adapters.models.fake import FakeModel


def backend_at(tmp_path, factory=lambda *args: FakeModel()):
    directory = tmp_path / 'scenarios'
    directory.mkdir(exist_ok=True)
    (directory / 'one-poisoned.yaml').write_bytes(Path('backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml').read_bytes())
    return build_backend(WebConfig(scenario_dir=directory, database=tmp_path/'runs.db'), model_factory=factory)


def test_application_completed_and_failed_ids_remain_private_after_reopen(tmp_path):
    calls = []
    def factory(*args):
        calls.append(args)
        if len(calls) == 2:
            raise RuntimeError('synthetic private diagnostic')
        return FakeModel()
    backend = backend_at(tmp_path, factory)
    alice, bob = Principal(101, 'analyst'), Principal(102, 'analyst')
    with principal_scope(alice):
        completed = backend.runs.create(dict(scenario_id='002', mode='poisoned', owner_id=102))
        failed = backend.runs.create(dict(scenario_id='002', mode='clean', owner_id=102))
        assert completed['status'] == 'completed'
        assert failed['status'] == 'failed'
        details = [backend.runs.get(r['run_id']) for r in (completed, failed)]
        assert details[1]['recommendation_correctness'] is None
        assert 'synthetic private diagnostic' not in str(details)
        assert backend.runs.metrics()['attempted'] == 2
    for principal in (bob, Principal(101, 'superadmin'), None):
        with principal_scope(principal):
            assert backend.runs.list() == []
            assert backend.runs.metrics()['attempted'] == 0
            for identifier in (completed['run_id'], failed['run_id'], 99999):
                with pytest.raises(KeyError, match='run not found'):
                    backend.runs.get(identifier)
                with pytest.raises(KeyError, match='run not found'):
                    backend.runs.summary(identifier, backend.store.result_for(completed['run_id']))
            if principal != bob:
                with pytest.raises(KeyError):
                    backend.runs.create(dict(scenario_id='002', mode='clean'))
    with principal_scope(bob):
        own = backend.runs.create(dict(scenario_id='002', mode='clean'))
        assert [r['run_id'] for r in backend.runs.list()] == [own['run_id']]
    reopened = backend_at(tmp_path)
    with principal_scope(alice):
        assert [reopened.runs.get(r['run_id']) for r in (completed, failed)] == details
        assert [r['run_id'] for r in reopened.runs.list()] == [failed['run_id'], completed['run_id']]


def test_ownerless_history_is_quarantined_without_rewriting_saved_meanings(tmp_path):
    import sqlite3
    from poisontrace.domain import ExperimentMode, ExperimentResult
    # A genuine pre-ownership schema with an existing synthetic record and trace.
    with sqlite3.connect(tmp_path/'runs.db') as connection:
        connection.execute('CREATE TABLE runs (id INTEGER PRIMARY KEY, scenario_id TEXT, mode TEXT, recommendation TEXT, benign_task_success INTEGER, attack_success INTEGER, execution_time_ms REAL, system_error INTEGER, unauthorised_tool_call INTEGER)')
        connection.execute("INSERT INTO runs VALUES (1, 'old', 'defended', 'original historical answer', 0, 1, 12.5, 0, 0)")
    backend = backend_at(tmp_path)
    legacy = backend.store.save_result(ExperimentResult('historical', ExperimentMode.DEFENDED, 'saved recommendation', False, True), 'legacy')
    original = backend.store.result_for(legacy)
    for _ in range(2):
        backend = backend_at(tmp_path)
        for principal in (Principal(1, 'analyst'), Principal(2, 'analyst'), Principal(1, 'superadmin'), None):
            with principal_scope(principal):
                assert backend.runs.list() == []
                assert backend.runs.metrics()['attempted'] == 0
                with pytest.raises(KeyError, match='run not found'):
                    backend.runs.get(legacy)
        assert backend.store.result_for(legacy) == original
        assert backend.store.result_for(1).recommendation == 'original historical answer'
        assert backend.store.result_for(1).scoring_version == 'legacy'
        assert backend.store.result_for(1).attack_success is True


def test_http_two_issued_analysts_completed_failed_mcp_and_role_denial(tmp_path):
    from fastapi.testclient import TestClient
    from poisontrace.bootstrap import build_accounts, create_app
    from poisontrace.config import AccountSeed
    import uuid
    suffix = uuid.uuid4().hex
    calls = []
    def factory(*args):
        calls.append(args)
        if len(calls) > 1:
            raise RuntimeError('synthetic failure')
        return FakeModel()
    backend = backend_at(tmp_path, factory)
    accounts = build_accounts(backend.store.database, seeds=(AccountSeed('operator', 'superadmin', suffix),))
    names = [('alice-'+suffix, 'a-'+suffix), ('bob-'+suffix, 'b-'+suffix)]
    for name, password in names:
        accounts.create_analyst(name, name, password)
    client = TestClient(create_app(backend))
    def login(pair):
        response = client.post('/api/auth/login', json=dict(username=pair[0], passcode=pair[1]))
        assert response.status_code == 200, response.text
        return response.json()['user']
    alice = login(names[0])
    rejected = complete_investigation(client, backend, dict(workflow='metadata-v1', scenario_id='002', mode='poisoned', owner_id=str(alice['id']+1)))
    assert rejected.status_code == 400
    complete = complete_investigation(client, backend, dict(workflow='metadata-v1', scenario_id='002', mode='poisoned')).json()
    failed = complete_investigation(client, backend, dict(workflow='metadata-v1', scenario_id='002', mode='clean')).json()
    assert failed['status'] == 'failed'
    mcp = complete_investigation(client, backend, dict(workflow='mcp-investigation-v1', provider='scripted', case_id='soc-auth-001', mode='clean')).json()
    assert mcp['status'] == 'completed'
    identifiers = [r['run_id'] for r in (complete, failed, mcp)]
    details = [client.get(f'/api/runs/{i}').json() for i in identifiers]
    assert details[2]['investigation']['evidence']
    assert client.get('/api/runs/summary').json()['attempted'] == 3
    login(names[1])
    assert client.get('/api/runs').json() == []
    metrics = client.get('/api/runs/summary').json()
    assert metrics['attempted'] == 0 and metrics['system_error_rate'] is None
    for identifier in (*identifiers, 99999):
        response = client.get(f'/api/runs/{identifier}')
        assert response.status_code == 404
        assert response.json() == {'detail':'run not found'}
    own = complete_investigation(client, backend, dict(workflow='metadata-v1', scenario_id='002', mode='clean')).json()
    assert [r['run_id'] for r in client.get('/api/runs').json()] == [own['run_id']]
    login(names[0])
    assert [client.get(f'/api/runs/{i}').json() for i in identifiers] == details
    assert client.get(f"/api/runs/{own['run_id']}").status_code == 404
    login(('operator', suffix))
    for path in ('/api/runs', '/api/runs/summary', f'/api/runs/{identifiers[0]}'):
        assert client.get(path).status_code == 403
    assert client.post('/api/runs', json=dict(scenario_id='002', mode='clean')).status_code == 403
    client.post('/api/auth/logout')
    assert client.get('/api/runs').status_code == 401


def test_campaign_and_group_views_cannot_bypass_child_run_privacy(tmp_path):
    def failure(*args):
        raise RuntimeError('private synthetic diagnostic')
    backend = backend_at(tmp_path, failure)
    with principal_scope(Principal(10, 'analyst')):
        campaign = backend.campaign_service.create(dict(provider='fake'))
        campaign = backend.campaign_service.execute(campaign['campaign_id'])
        group = complete_application_group(backend, dict(case_id='soc-auth-001', case_version='1', provider='scripted', conditions=['clean'], repeats=1))
        assert campaign['metrics']['attempted'] == 1
        assert group['attempts'][0]['status'] == 'completed'
    with principal_scope(Principal(11, 'analyst')):
        with pytest.raises(KeyError, match='campaign not found'):
            backend.campaign_service.get(campaign['campaign_id'])
        with pytest.raises(KeyError, match='group not found'):
            backend.groups.get(group['group_id'])
