import importlib.util

import pytest


fastapi_available = importlib.util.find_spec("fastapi") is not None
pytestmark = pytest.mark.skipif(
    not fastapi_available,
    reason="install the optional web dependencies to run HTTP endpoint tests",
)


def test_http_endpoints_are_exposed(tmp_path, analyst_client):
    from fastapi.testclient import TestClient

    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    source = __import__("pathlib").Path("backend/tests/fixtures/scenarios/authentication-alert-001.yaml")
    (scenario_dir / "authentication-alert-001.yaml").write_text(
        source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    client = analyst_client(create_app(build_backend(WebConfig(scenario_dir=scenario_dir, database=tmp_path / "runs.db"))))

    assert client.get("/api/runs").status_code == 200
    response = client.post(
        "/api/runs",
        json={"session_id": "session-1", "scenario_id": "001", "mode": "clean", "provider": "fake"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == "EXP-001"


def test_run_http_preserves_list_detail_and_rejection_contracts(tmp_path, analyst_client):
    from pathlib import Path

    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    source = Path("backend/tests/fixtures/scenarios/authentication-alert-001.yaml")
    (scenario_dir / source.name).write_bytes(source.read_bytes())
    (scenario_dir / "broken.yaml").write_text("scenario_id: '999'\nname: Broken\n", encoding="utf-8")
    client = analyst_client(create_app(build_backend(WebConfig(scenario_dir=scenario_dir, database=tmp_path / "runs.db"))))

    created = client.post("/api/runs", json={"scenario_id": "001", "session_id": "study", "provider": "fake"})
    assert created.status_code == 200
    summary = created.json()
    assert client.get("/api/runs").json() == [summary]
    response = client.get(f"/api/runs/{summary['run_id']}")
    assert response.status_code == 200
    detail = response.json()
    assert all(detail[key] == value for key, value in summary.items())
    assert detail["status"] == "completed"
    assert detail["run_configuration"] == {"mode": "clean", "scenario_id": "001", "session_id": "study", "provider": "fake", "credential_id": ""}
    assert detail["metrics"]["attack_success"] == detail["attack_success"]
    assert detail["trace"][0]["kind"] == "tool_discovered"
    assert detail["trace"][-1]["kind"] == "recommendation_created"

    missing = client.post("/api/runs", json={"scenario_id": "missing", "provider": "fake"})
    assert missing.status_code == 404
    assert missing.json() == {"detail": "scenario not found"}
    assert client.post("/api/runs", json={"scenario_id": "broken.yaml", "provider": "fake"}).status_code == 400
    assert client.post("/api/runs", json={"scenario_id": "001", "provider": "unknown"}).status_code == 400
    assert client.get("/api/runs/999").status_code == 404


def test_backend_login_seeds_role_aware_demo_accounts_without_returning_passcodes(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    monkeypatch.setenv("POISONTRACE_ANALYST_USERNAME", "Analyst.Demo")
    monkeypatch.setenv("POISONTRACE_ANALYST_PASSCODE", "analyst-secret")
    monkeypatch.setenv("POISONTRACE_SUPERADMIN_USERNAME", "Admin.Demo")
    monkeypatch.setenv("POISONTRACE_SUPERADMIN_PASSCODE", "admin-secret")
    client = TestClient(create_app(build_backend(WebConfig(scenario_dir=tmp_path / "scenarios", database=tmp_path / "users.db"))))

    analyst = client.post("/api/auth/login", json={"username": " analyst.demo ", "passcode": "analyst-secret"})
    assert analyst.status_code == 200
    assert analyst.json()["user"]["role"] == "analyst"
    assert analyst.json()["redirect"] == "/sessions"
    assert "passcode" not in analyst.json()

    admin = client.post("/api/auth/login", json={"username": "admin.demo", "passcode": "admin-secret"})
    assert admin.status_code == 200
    assert admin.json()["user"]["role"] == "superadmin"
    assert admin.json()["redirect"] == "/admin/users"
    assert "passcode" not in admin.json()


def test_backend_session_endpoint_returns_current_user_and_logout_clears_it(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    monkeypatch.setenv("POISONTRACE_ANALYST_PASSCODE", "analyst-secret")
    client = TestClient(create_app(build_backend(WebConfig(scenario_dir=tmp_path / "scenarios", database=tmp_path / "users.db"))))
    login = client.post("/api/auth/login", json={"username": "analyst", "passcode": "analyst-secret"})

    assert client.get("/api/auth/session").json()["user"]["username"] == "analyst"
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/session").status_code == 401


def test_analyst_api_access_requires_authentication_and_superadmin_is_forbidden(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    monkeypatch.setenv("POISONTRACE_ANALYST_PASSCODE", "analyst-secret")
    monkeypatch.setenv("POISONTRACE_SUPERADMIN_PASSCODE", "admin-secret")
    client = TestClient(create_app(build_backend(WebConfig(scenario_dir=tmp_path / "scenarios", database=tmp_path / "users.db"))))

    assert client.get("/api/runs").status_code == 401
    client.post("/api/auth/login", json={"username": "superadmin", "passcode": "admin-secret"})
    assert client.get("/api/runs").status_code == 403


def test_superadmin_can_list_and_create_active_analysts_without_passcodes_in_response(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    monkeypatch.setenv("POISONTRACE_SUPERADMIN_PASSCODE", "admin-secret")
    client = TestClient(create_app(build_backend(WebConfig(scenario_dir=tmp_path / "scenarios", database=tmp_path / "users.db"))))
    client.post("/api/auth/login", json={"username": "superadmin", "passcode": "admin-secret"})

    created = client.post("/api/admin/users", json={"username": " New.Analyst ", "display_name": "New Analyst", "passcode": "new-secret"})
    assert created.status_code == 201
    assert created.json()["username"] == "new.analyst"
    assert created.json()["role"] == "analyst"
    assert "passcode" not in created.json()
    assert any(user["username"] == "new.analyst" for user in client.get("/api/admin/users?search=NEW").json())

    duplicate = client.post("/api/admin/users", json={"username": "NEW.ANALYST", "display_name": "Other", "passcode": "secret"})
    assert duplicate.status_code == 400


def test_user_lifecycle_protects_last_active_superadmin_and_disables_sessions(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    monkeypatch.setenv("POISONTRACE_SUPERADMIN_PASSCODE", "admin-secret")
    client = TestClient(create_app(build_backend(WebConfig(scenario_dir=tmp_path / "scenarios", database=tmp_path / "users.db"))))
    client.post("/api/auth/login", json={"username": "superadmin", "passcode": "admin-secret"})
    admin = client.get("/api/admin/users").json()[0]
    assert client.patch(f"/api/admin/users/{admin['id']}", json={"role": "analyst"}).status_code == 400

    created = client.post("/api/admin/users", json={"username": "analyst-two", "display_name": "Analyst Two", "passcode": "secret"}).json()
    assert client.patch(f"/api/admin/users/{created['id']}", json={"display_name": "Renamed Analyst"}).json()["display_name"] == "Renamed Analyst"
    analyst_client = TestClient(client.app)
    analyst_client.post("/api/auth/login", json={"username": "analyst-two", "passcode": "secret"})
    assert client.patch(f"/api/admin/users/{created['id']}", json={"status": "disabled"}).status_code == 200
    assert analyst_client.get("/api/runs").status_code == 401
