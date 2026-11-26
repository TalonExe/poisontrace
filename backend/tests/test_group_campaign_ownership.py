from job_helpers import complete_application_group
from job_helpers import complete_campaign, complete_group
"""Private plans and retained child attempts through public application interfaces."""
import pytest

from poisontrace.application.principals import Principal, principal_scope
from test_run_ownership import backend_at


def test_private_plans_execute_rerun_and_reopen(tmp_path):
    backend = backend_at(tmp_path)
    alice, bob = Principal(101, 'analyst'), Principal(102, 'analyst')
    with principal_scope(alice):
        campaign = backend.campaign_service.create(dict(provider='fake'))
        cid = campaign['campaign_id']
        group = complete_application_group(backend, dict(case_id='soc-auth-001', case_version='1', provider='scripted', conditions=['clean'], repeats=1))
        gid = group['group_id']
    for principal in (bob, Principal(101, 'superadmin'), None):
        with principal_scope(principal):
            assert backend.groups.list() == []
            assert backend.campaign_service.list() == []
            for identifier in (gid, 'unknown'):
                for action in (lambda: backend.groups.get(identifier), lambda: complete_application_group(backend, {}, identifier)):
                    with pytest.raises(KeyError):
                        action()
            for identifier in (cid, 'unknown'):
                for action in (lambda: backend.campaign_service.get(identifier), lambda: backend.campaign_service.execute(identifier), lambda: backend.campaign_service.rerun(identifier, 0)):
                    with pytest.raises(KeyError):
                        action()
            assert backend.runs.list() == []
            assert backend.runs.metrics()['attempted'] == 0
    with principal_scope(alice):
        assert backend.campaign_service.get(cid) == campaign
        completed = backend.campaign_service.execute(cid)
        child = completed['scenarios'][0]['child_run_id']
        rerun = backend.campaign_service.rerun(cid, 0)
        assert rerun['scenarios'][0]['child_run_id'] != child
        assert rerun['metrics']['attempted'] == 2
        assert backend.runs.get(child)['run_configuration']['campaign_id'] == cid
        retained = complete_application_group(backend, {}, gid)
        assert retained['plan'] == group['plan']
        assert retained['attempts'][0] == group['attempts'][0]
        assert retained['comparison']['attempted'] == 2
        assert backend.runs.metrics()['attempted'] == 4
    reopened = backend_at(tmp_path)
    with principal_scope(alice):
        assert reopened.groups.get(gid) == retained
        assert reopened.campaign_service.get(cid) == rerun
    with principal_scope(bob):
        assert reopened.groups.list() == []
        assert reopened.campaign_service.list() == []


def test_persistence_rejects_known_foreign_children_and_mutation(tmp_path):
    from uuid import uuid4

    backend = backend_at(tmp_path)
    with principal_scope(Principal(101, 'analyst')):
        campaign = backend.campaign_service.create(dict(provider='fake'))
        group = complete_application_group(backend, dict(case_id='soc-auth-001', case_version='1', provider='scripted', conditions=['clean'], repeats=1))
        owner_jobs = backend.jobs.list()
    with principal_scope(Principal(102, 'analyst')):
        foreign = backend.runs.create(dict(scenario_id='002', mode='poisoned'))['run_id']
        for action in (
            lambda: backend.campaigns.associate_child_run(campaign['campaign_id'], 0, child_run_id=foreign),
            lambda: backend.jobs.submit_group(uuid4().hex, {}, group['group_id']),
            lambda: backend.campaigns.set_status(campaign['campaign_id'], 'running'),
        ):
            with pytest.raises(KeyError):
                action()
        assert backend.jobs.list() == []
    with principal_scope(Principal(101, 'analyst')):
        with pytest.raises(KeyError):
            backend.campaigns.associate_child_run(campaign['campaign_id'], 0, child_run_id=foreign)
        assert backend.groups.get(group['group_id']) == group
        assert backend.jobs.list() == owner_jobs
        assert backend.campaign_service.get(campaign['campaign_id']) == campaign


def test_legacy_plans_are_quarantined_and_corrupt_foreign_links_are_hidden(tmp_path):
    import json
    import sqlite3
    database = tmp_path / 'runs.db'
    # Genuine pre-ownership tables. Invalid opaque plans prove denial precedes decoding.
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE run_groups (group_id TEXT PRIMARY KEY, plan TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ready', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO run_groups VALUES ('legacy-group', 'opaque legacy plan', 'finished', 'old')")
        connection.execute('CREATE TABLE campaigns (campaign_id TEXT PRIMARY KEY, status TEXT, provider TEXT, model TEXT, credential_id TEXT, created_at TEXT)')
        connection.execute("INSERT INTO campaigns VALUES ('legacy-campaign', 'created', 'fake', 'historical-model', 'legacy-reference', 'old')")
    for _ in range(2):
        backend = backend_at(tmp_path)
        for principal in (Principal(101, 'analyst'), Principal(102, 'analyst'), Principal(101, 'superadmin'), None):
            with principal_scope(principal):
                assert backend.groups.list() == []
                assert backend.campaign_service.list() == []
                for action in (lambda: backend.groups.get('legacy-group'), lambda: complete_application_group(backend, {}, 'legacy-group'), lambda: backend.campaign_service.get('legacy-campaign'), lambda: backend.campaign_service.execute('legacy-campaign'), lambda: backend.campaign_service.rerun('legacy-campaign', 0)):
                    with pytest.raises(KeyError):
                        action()
        with sqlite3.connect(database) as connection:
            assert connection.execute('SELECT owner_id,plan FROM run_groups').fetchall() == [(None, 'opaque legacy plan')]
            assert connection.execute('SELECT owner_id,model,credential_id FROM campaigns').fetchall() == [(None, 'historical-model', 'legacy-reference')]
    with principal_scope(Principal(101, 'analyst')):
        campaign = backend.campaign_service.create(dict(provider='fake'))
        group = complete_application_group(backend, dict(case_id='soc-auth-001', case_version='1', provider='scripted', conditions=['clean'], repeats=1))
    with principal_scope(Principal(102, 'analyst')):
        foreign = backend.runs.create(dict(scenario_id='002', mode='poisoned'))['run_id']
    # Corrupt synthetic associations, including a not-yet-executed campaign.
    with sqlite3.connect(database) as connection:
        connection.execute('UPDATE run_group_attempts SET run_id=?', (foreign,))
        connection.execute('UPDATE campaign_scenarios SET child_run_id=?,error=?', (foreign, 'private-failure'))
    with principal_scope(Principal(101, 'analyst')):
        private = backend.groups.get(group['group_id'])
        assert private['attempts'][0]['run_id'] is None
        assert private['comparison']['attempted'] == 0
        private_campaign = backend.campaign_service.get(campaign['campaign_id'])
        assert private_campaign['scenarios'][0]['child_run_id'] is None
        assert 'private-failure' not in json.dumps(private_campaign)


def test_http_private_plans_attempts_credentials_metrics_and_account_switch(tmp_path):
    from fastapi.testclient import TestClient
    from cryptography.fernet import Fernet
    from uuid import uuid4
    from poisontrace.bootstrap import build_accounts, create_app
    from poisontrace.adapters.secrets.storage import EncryptedSqliteSecrets
    from poisontrace.adapters.models.fake import FakeModel
    from poisontrace.adapters.models.scripted_investigation import ScriptedInvestigationModel
    calls = []
    def metadata(*args):
        calls.append(args)
        if len(calls) == 1:
            raise RuntimeError('synthetic private failure')
        return FakeModel()
    backend = backend_at(tmp_path, metadata)
    # Build with owned encrypted references and an offline model substitute.
    from poisontrace.bootstrap import build_backend
    from poisontrace.config import AccountSeed, WebConfig
    backend = build_backend(WebConfig(scenario_dir=tmp_path/'scenarios', database=tmp_path/'runs.db'),
                            EncryptedSqliteSecrets(tmp_path/'keys.db', Fernet.generate_key()),
                            model_factory=metadata, investigation_model_factory=lambda *args: ScriptedInvestigationModel())
    suffix = uuid4().hex
    operator = ('operator-'+suffix, uuid4().hex)
    accounts = build_accounts(tmp_path/'runs.db', seeds=(AccountSeed(operator[0], 'superadmin', operator[1]),))
    names = [('alice-'+suffix, uuid4().hex), ('bob-'+suffix, uuid4().hex)]
    for name, password in names:
        accounts.create_analyst(name, name, password)
    client = TestClient(create_app(backend))
    def login(pair):
        response = client.post('/api/auth/login', json=dict(username=pair[0], passcode=pair[1]))
        assert response.status_code == 200
        return response.json()['user']
    alice = login(names[0])
    key = client.post('/api/credentials', json=dict(provider='openai', secret=Fernet.generate_key().decode())).json()['credential_id']
    campaign = client.post('/api/campaigns', json=dict(provider='openai', model='offline', credential_id=key, owner_id=alice['id']+1)).json()
    cid = campaign['campaign_id']
    executed = complete_campaign(client, backend, cid)
    failed = executed['scenarios'][0]['child_run_id']
    assert executed['metrics']['system_error_rate'] == 1.0
    assert client.get(f'/api/runs/{failed}').json()['recommendation_correctness'] is None
    request = dict(provider='scripted', case_id='soc-auth-001', case_version='1', conditions=['clean'], repeats=1)
    group = complete_group(client, backend, json=request).json()
    gid = group['group_id']
    child = group['attempts'][0]['run_id']
    assert client.get(f'/api/runs/{child}').json()['investigation']['evidence']
    login(names[1])
    bob_key = client.post('/api/credentials', json=dict(provider='openai', secret=Fernet.generate_key().decode())).json()['credential_id']
    assert client.get('/api/campaigns').json() == []
    assert client.get('/api/run-groups').json() == []
    assert client.get('/api/runs/summary').json()['attempted'] == 0
    for identifier in (gid, 'unknown'):
        assert client.get(f'/api/run-groups/{identifier}').json() == {'detail':'group or case not found'}
        response = client.post(f'/api/run-groups/{identifier}/execute', json=dict(credential_id=bob_key))
        assert response.status_code == 404
        assert response.json() == {'detail':'group or case not found'}
    for identifier in (cid, 'unknown'):
        for path, method, message in ((f'/api/campaigns/{identifier}', 'GET', 'campaign not found'),
                                      (f'/api/campaigns/{identifier}/execute', 'POST', 'campaign not found'),
                                      (f'/api/campaigns/{identifier}/scenarios/0/rerun', 'POST', 'campaign scenario not found')):
            response = client.request(method, path)
            assert response.status_code == 404
            assert response.json() == {'detail':message}
    for identifier in (child, failed):
        assert client.get(f'/api/runs/{identifier}').status_code == 404
    # Foreign keys cannot create a plan or start an attempt.
    assert client.post('/api/campaigns', json=dict(provider='openai', model='offline', credential_id=key)).status_code == 404
    assert complete_group(client, backend, json={**request, 'provider':'openai', 'model':'offline', 'credential_id':key}).status_code == 404
    assert len(calls) == 1
    own_group = complete_group(client, backend, json=request).json()
    own_campaign = client.post('/api/campaigns', json=dict(provider='fake')).json()
    login(names[0])
    assert [g['group_id'] for g in client.get('/api/run-groups').json()] == [gid]
    assert [c['campaign_id'] for c in client.get('/api/campaigns').json()] == [cid]
    assert client.get(f"/api/run-groups/{own_group['group_id']}").status_code == 404
    assert client.get(f"/api/campaigns/{own_campaign['campaign_id']}").status_code == 404
    rerun = complete_campaign(client, backend, cid, 0)
    assert rerun['metrics']['attempted'] == 2
    assert rerun['metrics']['system_error_rate'] == 0.5
    assert client.get(f'/api/runs/{failed}').json()['status'] == 'failed'
    retained = complete_group(client, backend, f'/api/run-groups/{gid}/execute', json={}).json()
    assert retained['attempts'][0] == group['attempts'][0]
    assert retained['plan'] == group['plan']
    assert retained['comparison']['attempted'] == 2
    assert client.get('/api/runs/summary').json()['attempted'] == 4
    # An owned plan with another analyst's reference fails before another child.
    assert client.post(f'/api/run-groups/{gid}/execute', json=dict(credential_id=bob_key)).status_code == 400
    client.post('/api/auth/logout')
    for path in ('/api/run-groups', '/api/campaigns', f'/api/run-groups/{gid}', f'/api/campaigns/{cid}'):
        assert client.get(path).status_code == 401
    login(operator)
    for path in ('/api/run-groups', '/api/campaigns', f'/api/run-groups/{gid}', f'/api/campaigns/{cid}'):
        assert client.get(path).status_code == 403
    assert client.post(f'/api/run-groups/{gid}/execute', json={}).status_code == 403
    assert client.post(f'/api/campaigns/{cid}/execute').status_code == 403
    assert client.post(f'/api/campaigns/{cid}/scenarios/0/rerun').status_code == 403
