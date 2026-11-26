import secrets

import pytest

from poisontrace.adapters.persistence.accounts import SqliteAccountStore
from poisontrace.application.accounts import AuthenticationError, UserSessionService
from fastapi.testclient import TestClient
from poisontrace.production import RuntimeConfig, build_application, initialize_admin
from test_production import environment


def test_hosted_https_origin_cookie_docs_and_login_limits(tmp_path):
    config = RuntimeConfig.from_environment(environment(tmp_path, POISONTRACE_PROFILE='hosted', POISONTRACE_PUBLIC_ORIGIN='https://testserver'))
    initialize_admin(config, 'operator', 'synthetic-passcode')
    with TestClient(build_application(config), base_url='https://testserver') as client:
        payload = dict(username='operator', passcode='synthetic-passcode')
        assert client.post('/api/auth/login', json=payload).status_code == 403
        for origin in ['null', 'https://evil.invalid', 'https://testserver.evil.invalid', 'http://testserver']:
            assert client.post('/api/auth/login', json=payload, headers={'Origin': origin}).status_code == 403
        client.headers['Origin'] = 'https://testserver'
        response = client.post('/api/auth/login', json=payload)
        assert response.status_code == 200
        cookie = response.headers['set-cookie']
        for flag in ['Secure', 'HttpOnly', 'SameSite=lax', 'Max-Age=28800', 'Path=/']:
            assert flag in cookie
        assert 'Domain=' not in cookie
        assert response.headers['cache-control'] == 'no-store'
        assert client.get('/api/runs').status_code == 403
        for method, path in [('POST','/api/admin/users'), ('PATCH','/api/admin/users/1'),
                             ('POST','/api/scenarios'), ('PUT','/api/scenarios/001'), ('DELETE','/api/scenarios/001'),
                             ('PUT','/api/runs/investigation-cases/soc-auth-001'), ('POST','/api/credentials'),
                             ('POST','/api/runs'), ('POST','/api/investigation-jobs'), ('POST','/api/run-groups'), ('POST','/api/campaigns')]:
            assert client.request(method, path, json={}, headers={'Origin':'https://evil.invalid'}).status_code == 403
        for path in ['/docs', '/docs/', '/docs/oauth2-redirect', '/redoc', '/openapi.json']:
            assert client.get(path).status_code == 404
        assert client.post('/api/auth/logout', headers={'Origin': 'https://evil.invalid'}).status_code == 403
        assert client.get('/api/auth/session').status_code == 200
        assert client.post('/api/auth/logout').status_code == 204
        assert client.get('/api/auth/session').status_code == 401
        payload['passcode'] = 'wrong'
        for _ in range(9):
            assert client.post('/api/auth/login', json=payload).status_code == 401
        response = client.post('/api/auth/login', json=payload)
        assert response.status_code == 429
        assert int(response.headers['retry-after']) > 0
    with TestClient(build_application(config), base_url='https://testserver', headers={'Origin': 'https://testserver'}) as client:
        assert client.post('/api/auth/login', json=dict(username='operator', passcode='synthetic-passcode')).status_code == 429
    with TestClient(build_application(config)) as client:
        assert client.post('/api/auth/login', json=payload, headers={'Origin': 'https://testserver', 'X-Forwarded-Proto': 'https'}).status_code == 400


def test_hosted_rejects_duplicate_proxy_headers_and_never_echoes_passcodes(tmp_path):
    config = RuntimeConfig.from_environment(environment(tmp_path, POISONTRACE_PROFILE='hosted',
        POISONTRACE_TRUSTED_PROXIES='192.0.2.10/32'))
    with TestClient(build_application(config), client=('192.0.2.10', 1234), headers={'Origin':'https://testserver',
        'X-Forwarded-Proto':'https', 'X-Forwarded-For':'198.51.100.1'}) as client:
        passcode = secrets.token_urlsafe(1000)
        response = client.post('/api/auth/login', json={'username':'synthetic', 'passcode':passcode})
        assert response.status_code == 422
        assert passcode not in response.text
        assert response.json() == {'detail':'Invalid sign-in request'}
        for headers in [[('X-Forwarded-Proto','https'),('X-Forwarded-Proto','http')],
                        [('X-Forwarded-For','198.51.100.1'),('X-Forwarded-For','198.51.100.2')],
                        [('Host','testserver'),('Host','evil.invalid')]]:
            assert client.get('/api/auth/session', headers=headers).status_code == 400


def test_sessions_expire_at_fixed_deadline_across_restart_and_reenable(tmp_path):
    now = [1000.0]
    database = tmp_path / 'accounts.db'
    service = UserSessionService(SqliteAccountStore(database), clock=lambda: now[0], session_seconds=60)
    passcode = secrets.token_urlsafe(24)
    user = service.create_analyst('synthetic', 'Synthetic', passcode)
    _, token = service.authenticate(user.username, passcode)
    now[0] = 1059
    reopened = UserSessionService(SqliteAccountStore(database), clock=lambda: now[0], session_seconds=60)
    assert reopened.current_user(token).id == user.id
    now[0] = 1060
    with pytest.raises(AuthenticationError):
        reopened.current_user(token)
    now[0] = 1000
    with pytest.raises(AuthenticationError):
        reopened.current_user(token)
    _, token = service.authenticate(user.username, passcode)
    reopened.update_user(user.id, status='disabled')
    reopened.update_user(user.id, status='active')
    with pytest.raises(AuthenticationError):
        service.current_user(token)
    _, fresh = service.authenticate(user.username, passcode)
    reopened.update_user(user.id, role='superadmin')
    with pytest.raises(AuthenticationError):
        service.current_user(fresh)
    _, fresh = service.authenticate(user.username, passcode)
    assert service.current_user(fresh).role == 'superadmin'
    service.logout(fresh)
    with pytest.raises(AuthenticationError):
        reopened.current_user(fresh)


def test_login_windows_cover_account_peer_global_expiry_and_concurrency(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from poisontrace.application.accounts import LoginThrottled
    now = [1000.0]
    service = UserSessionService(SqliteAccountStore(tmp_path/'accounts.db'), clock=lambda: now[0])
    user = service.create_analyst('synthetic', 'Synthetic', 'synthetic-passcode')
    def attempt(index):
        try:
            service.authenticate(user.username, 'wrong', client_address=str(index))
        except LoginThrottled as exc:
            return exc.retry_after
        except AuthenticationError:
            return 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, range(14)))
    assert results.count(0) == 10
    assert results.count(300) == 4
    now[0] = 1300
    assert service.authenticate(user.username, 'synthetic-passcode', client_address='fresh')[0].id == user.id
    for index in range(60):
        with pytest.raises(AuthenticationError):
            service.authenticate('missing'+str(index), 'wrong', client_address='shared')
    with pytest.raises(LoginThrottled):
        service.authenticate('other', 'wrong', client_address='shared')
    for index in range(139):
        with pytest.raises(AuthenticationError):
            service.authenticate('global'+str(index), 'wrong', client_address='peer'+str(index))
    with pytest.raises(LoginThrottled):
        service.authenticate('another', 'wrong', client_address='another')


def test_only_explicit_proxy_peers_can_supply_single_https_client_headers(tmp_path):
    config = RuntimeConfig.from_environment(environment(tmp_path, POISONTRACE_PROFILE='hosted',
        POISONTRACE_PUBLIC_ORIGIN='https://testserver', POISONTRACE_TRUSTED_PROXIES='192.0.2.10/32'))
    initialize_admin(config, 'operator', 'synthetic-passcode')
    headers = {'Origin': 'https://testserver', 'X-Forwarded-Proto': 'https', 'X-Forwarded-For': '198.51.100.3'}
    payload = dict(username='operator', passcode='synthetic-passcode')
    with TestClient(build_application(config), client=('192.0.2.10', 1234), headers=headers) as client:
        assert client.post('/api/auth/login', json=payload).status_code == 200
        assert client.get('/api/auth/session', headers={'Cookie':'poisontrace_session='+client.cookies.get('poisontrace_session')}).status_code == 200
        for value in ['198.51.100.3, 198.51.100.4', 'unknown', '']:
            assert client.post('/api/auth/login', json=payload, headers={'X-Forwarded-For': value}).status_code == 400
        assert client.post('/api/auth/login', json=payload, headers={'X-Forwarded-Proto': 'http'}).status_code == 400
        assert client.post('/api/auth/login', json=payload, headers={'Host': 'evil.invalid', 'X-Forwarded-Host': 'testserver'}).status_code == 400
    with TestClient(build_application(config), client=('192.0.2.11', 1234), headers=headers) as client:
        assert client.post('/api/auth/login', json=payload).status_code == 400


def test_legacy_unbounded_sessions_never_gain_a_new_deadline(tmp_path):
    import hashlib
    import sqlite3
    database = tmp_path/'legacy.db'
    service = UserSessionService(SqliteAccountStore(database))
    user = service.create_analyst('synthetic', 'Synthetic', 'synthetic-passcode')
    token = secrets.token_urlsafe(24)
    with sqlite3.connect(database) as connection:
        connection.execute('DROP TABLE auth_sessions')
        connection.execute('CREATE TABLE auth_sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        connection.execute('INSERT INTO auth_sessions (token_hash, user_id) VALUES (?, ?)',
                           (hashlib.sha256(token.encode()).hexdigest(), user.id))
    reopened = UserSessionService(SqliteAccountStore(database))
    with pytest.raises(AuthenticationError):
        reopened.current_user(token)
    assert reopened.authenticate(user.username, 'synthetic-passcode')[0].id == user.id


@pytest.mark.parametrize('changes', [
    {'POISONTRACE_PUBLIC_ORIGIN': ''}, {'POISONTRACE_PUBLIC_ORIGIN': 'http://testserver'},
    {'POISONTRACE_PUBLIC_ORIGIN': 'https://testserver/path'}, {'POISONTRACE_PUBLIC_ORIGIN': 'https://user@testserver'},
    {'POISONTRACE_PUBLIC_ORIGIN': 'https://testserver:443'}, {'POISONTRACE_PUBLIC_ORIGIN': 'https://testserver:'},
    {'POISONTRACE_TRUSTED_PROXIES': '0.0.0.0/0'}, {'POISONTRACE_TRUSTED_PROXIES': '::/0'},
])
def test_invalid_hosted_security_config_fails_before_storage(tmp_path, changes):
    with pytest.raises(ValueError):
        build_application(RuntimeConfig.from_environment(environment(tmp_path, POISONTRACE_PROFILE='hosted', **changes)))
    assert not (tmp_path/'state').exists()
