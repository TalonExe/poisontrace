import secrets

import pytest
from fastapi.testclient import TestClient

from poisontrace.application.accounts import AuthenticationError
from poisontrace.bootstrap import build_accounts
from poisontrace.production import RuntimeConfig, build_application, initialize_admin, recover_admin
from test_production import environment


def test_operator_recovers_existing_admin_without_changing_identity_or_other_accounts(tmp_path):
    config = RuntimeConfig.from_environment(environment(tmp_path))
    original, replacement = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    initialize_admin(config, "Operator", original)
    service = build_accounts(config.web.database, seeds=())
    admin, token = service.authenticate("operator", original)
    analyst = service.create_analyst("analyst", "Analyst", secrets.token_urlsafe(24))
    recover_admin(config, " OPERATOR ", replacement)
    reopened = build_accounts(config.web.database, seeds=())
    recovered, fresh = reopened.authenticate("operator", replacement)
    assert (recovered.id, recovered.role, recovered.status) == (admin.id, "superadmin", "active")
    assert reopened.current_user(fresh).id == admin.id
    assert reopened.list_users("analyst") == [analyst]
    for username, passcode in (("operator", original),):
        with pytest.raises(AuthenticationError):
            reopened.authenticate(username, passcode)
    with pytest.raises(AuthenticationError):
        reopened.current_user(token)
    with pytest.raises(ValueError, match="superadmin"):
        recover_admin(config, "analyst", replacement)
    with pytest.raises(ValueError, match="superadmin"):
        recover_admin(config, "unknown", replacement)


def test_recovery_requires_deliberate_disabled_admin_enable_and_preserves_last_admin(tmp_path):
    config = RuntimeConfig.from_environment(environment(tmp_path))
    replacement = secrets.token_urlsafe(24)
    with pytest.raises(ValueError, match="fresh installation"):
        recover_admin(config, "operator", replacement)
    assert not config.data_root.exists()
    initialize_admin(config, "operator", secrets.token_urlsafe(24))
    service = build_accounts(config.web.database, seeds=())
    first = service.list_users()[0]
    second = service.create_analyst("second", "Second", replacement)
    service.update_user(second.id, role="superadmin")
    service.update_user(first.id, status="disabled")
    with pytest.raises(ValueError, match="enable-disabled"):
        recover_admin(config, "operator", replacement)
    with pytest.raises(AuthenticationError):
        service.authenticate("operator", replacement)
    recover_admin(config, "operator", replacement, enable_disabled=True)
    recovered, token = service.authenticate("operator", replacement)
    assert recovered.id == first.id
    service.update_user(second.id, status="disabled")
    for change in ({"status": "disabled"}, {"role": "analyst"}):
        with pytest.raises(ValueError, match="last active superadmin"):
            service.update_user(first.id, **change)
    assert service.current_user(token).role == "superadmin"


def test_operator_cli_recovery_uses_confirmed_hidden_input_and_safe_failures(tmp_path, monkeypatch, capsys):
    import getpass
    import sys
    from poisontrace import production

    config = RuntimeConfig.from_environment(environment(tmp_path))
    monkeypatch.setattr(production.RuntimeConfig, "from_environment", lambda: config)
    monkeypatch.setenv("POISONTRACE_ADMIN_USERNAME", "ignored-seed")
    monkeypatch.setenv("POISONTRACE_ADMIN_PASSCODE", "ignored-seed-passcode")
    passcode = secrets.token_urlsafe(24)
    initialize_admin(config, "operator", passcode)
    monkeypatch.setattr("builtins.input", lambda prompt: "operator")
    monkeypatch.setattr(sys, "argv", ["production", "recover-admin"])
    replacement = secrets.token_urlsafe(24)
    entries = iter([replacement, replacement + "mismatch"])
    monkeypatch.setattr(getpass, "getpass", lambda prompt: next(entries))
    with pytest.raises(SystemExit) as failure:
        production.main()
    assert failure.value.code == 1
    assert "match" in capsys.readouterr().err
    assert build_accounts(config.web.database, seeds=()).authenticate("operator", passcode)[0].role == "superadmin"
    entries = iter([replacement, replacement])
    production.main()
    output = capsys.readouterr()
    assert "recovered" in output.out
    assert all(value not in output.out + output.err for value in (passcode, replacement, "ignored-seed-passcode"))
    service = build_accounts(config.web.database, seeds=())
    assert service.authenticate("operator", replacement)[0].role == "superadmin"
    monkeypatch.setattr("builtins.input", lambda prompt: "missing")
    entries = iter([replacement, replacement])
    with pytest.raises(SystemExit) as failure:
        production.main()
    assert failure.value.code == 1
    assert "superadmin" in capsys.readouterr().err


@pytest.mark.parametrize("profile", ["local", "hosted"])
def test_account_management_reset_revokes_only_target_and_keeps_disabled_accounts_disabled(tmp_path, profile):
    config = RuntimeConfig.from_environment(environment(tmp_path, POISONTRACE_PROFILE=profile))
    admin_passcode, original, replacement = (secrets.token_urlsafe(24) for _ in range(3))
    initialize_admin(config, "operator", admin_passcode)
    app = build_application(config)
    service = build_accounts(config.web.database, seeds=())
    analyst = service.create_analyst("analyst", "Analyst", original)
    other = service.create_analyst("other", "Other", original)
    _, analyst_token = service.authenticate("analyst", original)
    _, second_token = service.authenticate("analyst", original)
    _, other_token = service.authenticate("other", original)
    with TestClient(app, base_url="https://testserver", headers={"Origin": "https://testserver"}) as client:
        path = f"/api/admin/users/{analyst.id}/passcode"
        assert client.post(path, json={"passcode": replacement}).status_code == 401
        client.cookies.set("poisontrace_session", analyst_token)
        assert client.post(path, json={"passcode": replacement}).status_code == 403
        client.cookies.clear()
        assert client.post("/api/auth/login", json={"username": "operator", "passcode": admin_passcode}).status_code == 200
        admin = service.list_users("operator")[0]
        assert client.post(f"/api/admin/users/{admin.id}/passcode", json={"passcode": replacement}).status_code == 400
        for payload in ({}, {"passcode": ""}, {"passcode": "x" * 1025}, {"passcode": {"secret": replacement}}):
            response = client.post(path, json=payload)
            assert response.status_code in (400, 422)
            assert replacement not in response.text
        missing = client.post("/api/admin/users/999999/passcode", json={"passcode": replacement})
        assert missing.status_code == 404
        malformed = client.post(path, content='{"passcode":', headers={"Content-Type": "application/json"})
        assert malformed.status_code == 422
        assert malformed.json() == {"detail": "Invalid passcode reset request"}
        if profile == "hosted":
            assert client.post(path, json={"passcode": replacement}, headers={"Origin": "https://foreign.invalid"}).status_code == 403
        response = client.post(path, json={"passcode": replacement, "role": "superadmin", "status": "active"})
        assert response.status_code == 200
        assert response.json() == {"status": "passcode reset", "user_id": analyst.id}
        assert original not in response.text and replacement not in response.text
        assert client.get("/api/runs").status_code == 403
        assert service.current_user(other_token).id == other.id
        for token in (analyst_token, second_token):
            with pytest.raises(AuthenticationError):
                service.current_user(token)
        with pytest.raises(AuthenticationError):
            service.authenticate("analyst", original)
        recovered, token = service.authenticate("analyst", replacement)
        assert (recovered.id, recovered.role) == (analyst.id, "analyst")
        service.update_user(analyst.id, status="disabled")
        assert client.post(path, json={"passcode": original}).status_code == 200
        assert service.list_users("analyst")[0].status == "disabled"
        with pytest.raises(AuthenticationError):
            service.authenticate("analyst", original)
        service.update_user(analyst.id, status="active")
        with pytest.raises(AuthenticationError):
            service.current_user(token)
        assert service.authenticate("analyst", original)[0].id == analyst.id


def test_reset_service_authenticates_actor_in_transaction_and_rejects_stale_or_nonadmin(tmp_path):
    config = RuntimeConfig.from_environment(environment(tmp_path))
    passcode = secrets.token_urlsafe(24)
    initialize_admin(config, "operator", passcode)
    service = build_accounts(config.web.database, seeds=())
    analyst = service.create_analyst("analyst", "Analyst", passcode)
    _, analyst_token = service.authenticate("analyst", passcode)
    admin, admin_token = service.authenticate("operator", passcode)
    for token in (None, "unknown"):
        with pytest.raises(AuthenticationError):
            service.reset_analyst_passcode(token, analyst.id, secrets.token_urlsafe(24))
    with pytest.raises(PermissionError):
        service.reset_analyst_passcode(analyst_token, analyst.id, secrets.token_urlsafe(24))
    recover_admin(config, "operator", secrets.token_urlsafe(24))
    with pytest.raises(AuthenticationError):
        service.reset_analyst_passcode(admin_token, analyst.id, secrets.token_urlsafe(24))
    assert service.current_user(analyst_token).id == analyst.id
    assert service.list_users("operator")[0].id == admin.id


def test_reset_and_recovery_keep_private_credentials_saved_results_and_one_way_hashes(tmp_path):
    config = RuntimeConfig.from_environment(environment(tmp_path, POISONTRACE_PROFILE="hosted"))
    admin_passcode, passcode, replacement, provider_key = (secrets.token_urlsafe(24) for _ in range(4))
    initialize_admin(config, "operator", admin_passcode)
    service = build_accounts(config.web.database, seeds=())
    analyst = service.create_analyst("analyst", "Analyst", passcode)
    app = build_application(config)
    with TestClient(app, base_url="https://testserver", headers={"Origin": "https://testserver"}) as client:
        assert client.post("/api/auth/login", json={"username": "analyst", "passcode": passcode}).status_code == 200
        credential = client.post("/api/credentials", json={"provider": "openai", "secret": provider_key, "label": "Generated"}).json()
        from job_helpers import complete_investigation
        run = complete_investigation(client, None, dict(workflow="metadata-v1", provider="fake", mode="clean", scenario_id="authentication-alert-poisoned-002"))
        assert run.status_code == 200
        path = f"/api/runs/{run.json()['run_id']}"
        saved = client.get(path).json()
        before_credentials = client.get("/api/credentials").json()
        client.post("/api/auth/login", json={"username": "operator", "passcode": admin_passcode})
        assert client.post(f"/api/admin/users/{analyst.id}/passcode", json={"passcode": replacement}).status_code == 200
        recover_admin(config, "operator", replacement)
        assert client.get("/api/admin/users").status_code == 401
    with TestClient(build_application(config), base_url="https://testserver", headers={"Origin": "https://testserver"}) as client:
        assert client.post("/api/auth/login", json={"username": "analyst", "passcode": replacement}).status_code == 200
        assert client.get(path).json() == saved
        assert client.get("/api/credentials").json() == before_credentials
        assert client.post(f"/api/credentials/{credential['credential_id']}/test").status_code == 200
        assert client.get("/api/admin/users").status_code == 403
        assert client.post("/api/auth/login", json={"username": "operator", "passcode": replacement}).status_code == 200
        assert client.get(path).status_code == 403
        assert client.get("/api/credentials").status_code == 403
    with service.store.transaction() as records:
        for username in ("analyst", "operator"):
            stored = records.find_credentials(username)[1]
            assert stored.startswith("scrypt$")
            assert all(value not in stored for value in (replacement, passcode, admin_passcode))


def test_reset_serializes_with_authentication_and_expired_admin_cannot_reset(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    config = RuntimeConfig.from_environment(environment(tmp_path))
    original, replacement = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    initialize_admin(config, "operator", original)
    service = build_accounts(config.web.database, seeds=())
    analyst = service.create_analyst("analyst", "Analyst", original)
    _, admin_token = service.authenticate("operator", original)
    def login():
        try:
            return service.authenticate("analyst", original)[1]
        except AuthenticationError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        authenticating = pool.submit(login)
        resetting = pool.submit(service.reset_analyst_passcode, admin_token, analyst.id, replacement)
        resetting.result()
        token = authenticating.result()
    if token:
        with pytest.raises(AuthenticationError):
            service.current_user(token)
    with pytest.raises(AuthenticationError):
        service.authenticate("analyst", original)
    assert service.authenticate("analyst", replacement)[0].id == analyst.id
    expired = build_accounts(config.web.database, seeds=(), clock=lambda: service.clock() + 28801)
    with pytest.raises(AuthenticationError):
        expired.reset_analyst_passcode(admin_token, analyst.id, original)


def test_bootstrap_refuses_unusable_credentials_before_creating_storage(tmp_path):
    config = RuntimeConfig.from_environment(environment(tmp_path))
    for username, passcode in (("operator", "x" * 1025), ("x" * 255, secrets.token_urlsafe(24))):
        with pytest.raises(ValueError):
            initialize_admin(config, username, passcode)
        assert not config.data_root.exists()


def test_operator_recovery_refuses_echoing_terminal_fallback(tmp_path, monkeypatch, capsys):
    import getpass
    import sys
    import warnings
    from poisontrace import production

    config = RuntimeConfig.from_environment(environment(tmp_path))
    passcode = secrets.token_urlsafe(24)
    initialize_admin(config, "operator", passcode)
    monkeypatch.setattr(production.RuntimeConfig, "from_environment", lambda: config)
    monkeypatch.setattr(sys, "argv", ["production", "recover-admin"])
    monkeypatch.setattr("builtins.input", lambda prompt: "operator")
    def unavailable(prompt):
        warnings.warn("synthetic terminal fallback", getpass.GetPassWarning)
        raise AssertionError("must never request an echoed passcode")
    monkeypatch.setattr(getpass, "getpass", unavailable)
    with pytest.raises(SystemExit) as failure:
        production.main()
    assert failure.value.code == 1
    output = capsys.readouterr()
    assert "hidden input is required" in output.err
    assert passcode not in output.err + output.out
    assert build_accounts(config.web.database, seeds=()).authenticate("operator", passcode)[0].role == "superadmin"


def test_account_management_validation_never_echoes_submitted_passcodes(tmp_path):
    config = RuntimeConfig.from_environment(environment(tmp_path))
    passcode, submitted = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    initialize_admin(config, "operator", passcode)
    with TestClient(build_application(config)) as client:
        assert client.post("/api/auth/login", json={"username": "operator", "passcode": passcode}).status_code == 200
        for method, path in (("POST", "/api/admin/users"), ("PATCH", "/api/admin/users/1")):
            response = client.request(method, path, json={"passcode": {"malformed": submitted}})
            assert response.status_code == 422
            assert submitted not in response.text
            assert response.json() == {"detail": "Invalid account-management request"}
