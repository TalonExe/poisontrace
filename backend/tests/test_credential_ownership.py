from job_helpers import complete_application_group
from job_helpers import complete_group
"""Analyst credential isolation through application and HTTP contracts."""
import pytest
from cryptography.fernet import Fernet

from poisontrace.adapters.secrets.storage import EncryptedSqliteSecrets, ManagedSecretsAdapter
from poisontrace.application.credentials import CredentialApplicationService


@pytest.mark.parametrize('managed', [False, True])
def test_only_owning_analyst_can_discover_or_operate_credentials(tmp_path, managed):
    from poisontrace.application.principals import Principal, principal_scope

    values = {}
    storage = ManagedSecretsAdapter(
        put=lambda i, p, l, s: values.__setitem__(i, s),
        get=lambda i: values[i], delete=lambda i: values.pop(i),
    ) if managed else EncryptedSqliteSecrets(tmp_path/'keys.db', Fernet.generate_key())
    service = CredentialApplicationService(storage)
    alice, bob = Principal(101, 'analyst'), Principal(102, 'analyst')
    key = Fernet.generate_key().decode()
    with principal_scope(alice):
        saved = service.save(dict(provider='openai', secret=key, label='private label'))
    identifier = saved['credential_id']
    for principal in (bob, Principal(101, 'superadmin'), None):
        with principal_scope(principal):
            assert service.list() == []
            if principal != bob:
                with pytest.raises(KeyError, match='credential not found'):
                    service.save(dict(provider='openai', secret='generated-denied-key'))
            for reference in (identifier, 'unknown'):
                for operation in (
                    lambda: storage.reference(reference), lambda: storage.retrieve(reference),
                    lambda: service.test(reference), lambda: service.revoke(reference),
                    lambda: service.replace(reference, dict(provider='gemini', secret='replacement')),
                ):
                    with pytest.raises(KeyError, match='credential not found'):
                        operation()
    with principal_scope(alice):
        assert service.list() == [saved]
        assert service.test(identifier)['ok']
        assert storage.retrieve(identifier) == key
        service.revoke(identifier)
        assert service.list() == []


def test_http_account_switching_uses_authenticated_owner(tmp_path):
    from pathlib import Path
    from fastapi.testclient import TestClient
    from poisontrace.bootstrap import build_backend, build_accounts, create_app
    from poisontrace.config import WebConfig

    database = tmp_path/'runs.db'
    accounts = build_accounts(database, seeds=())
    accounts.create_analyst('generated-alice', 'Alice', 'synthetic-password-a')
    accounts.create_analyst('generated-bob', 'Bob', 'synthetic-password-b')
    from poisontrace.adapters.models.fake import FakeModel
    from poisontrace.adapters.models.scripted_investigation import ScriptedInvestigationModel
    scenarios = tmp_path/'scenarios'
    scenarios.mkdir()
    (scenarios/'one-poisoned.yaml').write_bytes(Path('backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml').read_bytes())
    backend = build_backend(WebConfig(scenario_dir=scenarios, database=database),
                            EncryptedSqliteSecrets(tmp_path/'keys.db', Fernet.generate_key()),
                            model_factory=lambda *args: FakeModel(),
                            investigation_model_factory=lambda *args: ScriptedInvestigationModel())
    client = TestClient(create_app(backend))
    def login(name, suffix):
        assert client.post('/api/auth/login', json=dict(username='generated-'+name, passcode='synthetic-password-'+suffix)).status_code == 200
    login('alice', 'a')
    key = Fernet.generate_key().decode()
    saved = client.post('/api/credentials', json=dict(provider='openai', secret=key, label='alice-only', owner_id=2)).json()
    identifier = saved['credential_id']
    campaign = client.post('/api/campaigns', json=dict(provider='openai', model='offline-model', credential_id=identifier)).json()
    group_request = dict(provider='openai', model='offline-model', credential_id=identifier, case_id='soc-auth-001', case_version='1', conditions=['clean'], repeats=1)
    group_response = complete_group(client, backend, json=group_request)
    assert group_response.status_code == 200, group_response.text
    group = group_response.json()
    login('bob', 'b')
    assert client.get('/api/credentials').json() == []
    for reference in (identifier, 'unknown'):
        for method, path, payload in (
            ('POST', f'/api/credentials/{reference}/test', None),
            ('DELETE', f'/api/credentials/{reference}', None),
            ('PUT', f'/api/credentials/{reference}', dict(provider='openai', secret='generated-replacement')),
            ('POST', '/api/campaigns', dict(provider='openai', model='offline-model', credential_id=reference)),
        ):
            response = client.request(method, path, json=payload)
            assert response.status_code == 404, response.text
            assert response.json() == {'detail':'credential not found'}
            assert key not in response.text and 'alice-only' not in response.text
        for path, payload in (
            ('/api/investigation-jobs', dict(provider='openai', model='offline-model', workflow='metadata-v1', mode='clean', scenario_id='002', credential_id=reference)),
            ('/api/investigation-jobs', dict(provider='openai', model='offline-model', workflow='mcp-investigation-v1', mode='clean', case_id='soc-auth-001', credential_id=reference)),
            ('/api/run-groups', dict(group_request, credential_id=reference)),
            (f"/api/run-groups/{group['group_id']}/execute", dict(credential_id=reference)),
        ):
            response = client.post(path, json=payload, headers={'Idempotency-Key': 'synthetic-credential-denial'})
            assert response.status_code == 404, response.text
            assert response.json() == {'detail':'group or case not found' if '/execute' in path else 'credential not found'}
    for path in (f"/api/campaigns/{campaign['campaign_id']}/execute", f"/api/campaigns/{campaign['campaign_id']}/scenarios/0/rerun"):
        response = client.post(path)
        assert response.status_code == 404
        assert response.json() == {'detail':'campaign scenario not found' if '/rerun' in path else 'campaign not found'}
    bob_saved = client.post('/api/credentials', json=dict(provider='openai', secret=Fernet.generate_key().decode(), label='bob-only')).json()
    assert client.get('/api/credentials').json() == [bob_saved]
    login('alice', 'a')
    assert client.get('/api/credentials').json() == [saved]
    assert client.post(f'/api/credentials/{identifier}/test').status_code == 200
    assert client.delete(f'/api/credentials/{identifier}').status_code == 200
    assert client.post('/api/campaigns/'+campaign['campaign_id']+'/execute', headers={'Idempotency-Key': 'synthetic-revocation-check'}).status_code == 404
    assert complete_group(client, backend, '/api/run-groups/'+group['group_id']+'/execute', json=dict(credential_id=identifier)).status_code == 404


def test_legacy_ownerless_records_are_quarantined_without_decryption(tmp_path):
    import sqlite3
    from poisontrace.application.principals import Principal, principal_scope
    path = tmp_path/'legacy.db'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE credentials (credential_id TEXT PRIMARY KEY, provider TEXT NOT NULL, label TEXT NOT NULL, encrypted_secret BLOB NOT NULL)')
        # Deliberately undecryptable synthetic legacy ciphertext proves denial precedes decryption.
        connection.execute('INSERT INTO credentials VALUES (?, ?, ?, ?)', ('legacy', 'openai', 'hidden legacy label', b'opaque-legacy'))
    for _ in range(2):
        storage = EncryptedSqliteSecrets(path, Fernet.generate_key())
        for principal in (Principal(1, 'analyst'), Principal(2, 'analyst'), Principal(1, 'superadmin'), None):
            with principal_scope(principal):
                assert storage.list() == []
                for operation in (storage.reference, storage.retrieve, storage.revoke):
                    with pytest.raises(KeyError, match='credential not found'):
                        operation('legacy')
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT owner_id, encrypted_secret FROM credentials').fetchall() == [(None, b'opaque-legacy')]


def test_execution_and_reruns_check_current_analyst_and_revocation(tmp_path, caplog):
    from pathlib import Path
    from poisontrace.application.principals import Principal, principal_scope
    from poisontrace.bootstrap import build_backend
    from poisontrace.config import WebConfig
    from poisontrace.adapters.models.fake import FakeModel
    from poisontrace.adapters.models.scripted_investigation import ScriptedInvestigationModel

    scenarios = tmp_path/'scenarios'
    scenarios.mkdir()
    (scenarios/'one-poisoned.yaml').write_bytes(Path('backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml').read_bytes())
    keys = {}
    used = []
    def metadata(provider, model, key):
        used.append(key)
        return FakeModel()
    def investigation(provider, model, key):
        used.append(key)
        return ScriptedInvestigationModel()
    storage = EncryptedSqliteSecrets(tmp_path/'keys.db', Fernet.generate_key())
    backend = build_backend(WebConfig(scenario_dir=scenarios, database=tmp_path/'runs.db'), storage,
                            model_factory=metadata, investigation_model_factory=investigation)
    alice, bob = Principal(11, 'analyst'), Principal(12, 'analyst')
    for principal in (alice, bob):
        with principal_scope(principal):
            keys[principal] = backend.credentials.save(dict(provider='openai', secret=Fernet.generate_key().decode()))
    identifier = keys[alice]['credential_id']
    single = dict(provider='openai', model='offline-model', mode='clean', credential_id=identifier, scenario_id='002')
    mcp = dict(provider='openai', model='offline-model', mode='clean', credential_id=identifier, case_id='soc-auth-001')
    group = dict(provider='openai', model='offline-model', credential_id=identifier, case_id='soc-auth-001', case_version='1', conditions=['clean'], repeats=1)
    with principal_scope(alice):
        campaign = backend.campaign_service.create(single)
        backend.runs.create(single)
        accepted = backend.jobs.submit('synthetic-owned-investigation', mcp)
        backend.jobs.execute_claim(backend.jobs.store.claim())
        assert backend.jobs.get(accepted['job_id'])['status'] == 'completed'
        created_group = complete_application_group(backend, group)
    with principal_scope(bob):
        for operation in (
            lambda: backend.runs.create(single), lambda: backend.jobs.submit('synthetic-foreign-investigation', mcp),
            lambda: complete_application_group(backend, group),
            lambda: complete_application_group(backend, dict(credential_id=identifier), created_group['group_id']),
            lambda: backend.campaign_service.create(single),
            lambda: backend.campaign_service.execute(campaign['campaign_id']),
            lambda: backend.campaign_service.rerun(campaign['campaign_id'], 0),
        ):
            before = len(used)
            with pytest.raises(KeyError, match='not found'):
                operation()
            assert len(used) == before
        own = dict(single, credential_id=keys[bob]['credential_id'])
        backend.runs.create(own)
    with principal_scope(alice):
        assert backend.campaign_service.execute(campaign['campaign_id'])['completed'] == 1
        backend.campaign_service.rerun(campaign['campaign_id'], 0)
        backend.credentials.revoke(identifier)
        for operation in (lambda: backend.runs.create(single), lambda: backend.runs.create(mcp),
                          lambda: complete_application_group(backend, dict(credential_id=identifier), created_group['group_id']),
                          lambda: backend.campaign_service.rerun(campaign['campaign_id'], 0)):
            with pytest.raises(KeyError, match='credential not found'):
                operation()
    saved = str(created_group) + caplog.text
    for principal in (alice, bob):
        with principal_scope(principal):
            saved += str(backend.runs.list()) + str([backend.runs.get(r['run_id']) for r in backend.runs.list()])
    assert all(key not in saved for key in used)


def test_revocation_between_campaign_children_prevents_further_key_use(tmp_path):
    from pathlib import Path
    from poisontrace.application.principals import Principal, principal_scope
    from poisontrace.bootstrap import build_backend
    from poisontrace.config import WebConfig
    from poisontrace.adapters.models.fake import FakeModel
    scenarios = tmp_path/'scenarios'
    scenarios.mkdir()
    for name in ('a-poisoned.yaml', 'b-poisoned.yaml'):
        (scenarios/name).write_bytes(Path('backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml').read_bytes())
    storage = EncryptedSqliteSecrets(tmp_path/'keys.db', Fernet.generate_key())
    calls = []
    def factory(provider, model, key):
        calls.append(key)
        storage.revoke(identifier)
        return FakeModel()
    backend = build_backend(WebConfig(scenario_dir=scenarios, database=tmp_path/'runs.db'), storage, model_factory=factory)
    with principal_scope(Principal(1, 'analyst')):
        identifier = backend.credentials.save(dict(provider='openai', secret=Fernet.generate_key().decode()))['credential_id']
        campaign = backend.campaign_service.create(dict(provider='openai', model='offline', credential_id=identifier))
        result = backend.campaign_service.execute(campaign['campaign_id'])
        assert len(calls) == 1
        assert result['completed'] == 1
        assert result['failed'] == 1


def test_managed_storage_errors_do_not_return_callback_secrets():
    from poisontrace.application.principals import Principal, principal_scope
    secret = Fernet.generate_key().decode()
    def fail(*args):
        raise ValueError(secret)
    storage = ManagedSecretsAdapter(put=fail, get=fail, delete=fail)
    with principal_scope(Principal(1, 'analyst')):
        with pytest.raises(ValueError, match='credential storage unavailable') as error:
            storage.save('openai', secret)
        assert secret not in str(error.value)


@pytest.mark.parametrize('provider', ['openai', 'gemini'])
def test_web_application_execution_cannot_fall_back_to_operator_environment_keys(tmp_path, monkeypatch, provider, application_analyst):
    from poisontrace.bootstrap import build_backend
    from poisontrace.config import WebConfig
    monkeypatch.setenv('OPENAI_API_KEY', 'generated-operator-key-never-use')
    monkeypatch.setenv('GEMINI_API_KEY', 'generated-operator-key-never-use')
    def forbidden(*args):
        pytest.fail('provider construction must not happen without an owned reference')
    backend = build_backend(WebConfig(scenario_dir=tmp_path/'scenarios', database=tmp_path/'runs.db'), model_factory=forbidden)
    for operation in (backend.runs.create, backend.campaign_service.create):
        with pytest.raises(ValueError, match='provider execution requires a credential reference'):
            operation(dict(provider=provider, model='offline', mode='clean'))
    assert backend.runs.list() == []
    assert backend.campaign_service.list() == []


def test_managed_revocation_during_replacement_cannot_resurrect_reference():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from poisontrace.application.principals import Principal, principal_scope
    principal = Principal(1, 'analyst')
    replacing, revoke_started, release = Event(), Event(), Event()
    values = {}
    def put(identifier, provider, label, secret):
        if secret == 'generated-replacement':
            replacing.set()
            assert release.wait(5)
        values[identifier] = secret
    storage = ManagedSecretsAdapter(put=put, get=lambda i: values[i], delete=lambda i: values.pop(i))
    with principal_scope(principal):
        identifier = storage.save('openai', 'generated-original').credential_id
    def replace():
        with principal_scope(principal):
            storage.replace(identifier, 'openai', 'generated-replacement')
    def revoke():
        with principal_scope(principal):
            revoke_started.set()
            storage.revoke(identifier)
    with ThreadPoolExecutor(max_workers=2) as executor:
        pending_replace = executor.submit(replace)
        assert replacing.wait(5)
        pending_revoke = executor.submit(revoke)
        assert revoke_started.wait(5)
        release.set()
        pending_replace.result(timeout=5)
        pending_revoke.result(timeout=5)
    with principal_scope(principal):
        assert storage.list() == []
        with pytest.raises(KeyError, match='credential not found'):
            storage.retrieve(identifier)
