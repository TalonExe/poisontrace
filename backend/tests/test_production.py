"""Production composition uses only synthetic accounts and isolated state."""
from job_helpers import complete_investigation
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from poisontrace.production import RuntimeConfig, build_application, initialize_admin


def environment(tmp_path, **changes):
    frontend = tmp_path / "frontend"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text("<html>synthetic SPA</html>")
    return {"POISONTRACE_PROFILE": "local", "POISONTRACE_PUBLIC_ORIGIN": "https://testserver", "POISONTRACE_DATA_ROOT": str(tmp_path / "state"),
            "POISONTRACE_FRONTEND_ROOT": str(frontend), "POISONTRACE_SECRETS_KEY": Fernet.generate_key().decode(), **changes}


def test_invalid_configuration_creates_no_storage(tmp_path):
    for changes in ({"POISONTRACE_SECRETS_KEY": ""}, {"PORT": "0"}, {"POISONTRACE_PROFILE": "typo"},
                    {"POISONTRACE_DATA_ROOT": "relative"}, {"POISONTRACE_FRONTEND_ROOT": str(tmp_path / "missing")}):
        with pytest.raises((ValueError, RuntimeError)):
            build_application(RuntimeConfig.from_environment(environment(tmp_path, **changes)))
        assert not (tmp_path / "state").exists()


def test_profiles_use_one_root_and_seed_only_once(tmp_path):
    env = environment(tmp_path, POISONTRACE_PROFILE="hosted")
    config = RuntimeConfig.from_environment(env)
    app = build_application(config)
    assert config.web.database.parent == config.data_root
    assert config.web.secrets_database.parent == config.data_root
    assert config.web.scenario_dir.parent == config.data_root
    files = list(config.web.scenario_dir.glob("*.yaml"))
    assert files
    files[0].unlink()
    build_application(config)
    assert not files[0].exists(), "restart must not undo local deletions"
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "alive"}
        assert client.get("/health/ready").status_code == 200
        import gc
        gc.collect()  # Existing persistence adapters release their connection cycles on GC.
        config.web.secrets_database.unlink()
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}


def test_first_admin_routing_roles_and_restart(tmp_path):
    config = RuntimeConfig.from_environment(environment(tmp_path))
    with pytest.raises(ValueError):
        initialize_admin(config, "", "")
    assert not config.data_root.exists()
    initialize_admin(config, "Synthetic-Operator", "generated-test-passcode")
    with pytest.raises(ValueError, match="already"):
        initialize_admin(config, "another", "other-generated-passcode")
    with TestClient(build_application(config)) as client:
        for path in ("/sessions", "/dashboard/single", "/results/runs/1", "/results/groups/1", "/admin/users"):
            response = client.get(path)
            assert response.status_code == 200 and "synthetic SPA" in response.text
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/api").status_code == 404
        assert client.get("/api/unknown").status_code == 401
        assert client.post("/api/auth/login", json={"username": "synthetic-operator", "passcode": "generated-test-passcode"}).status_code == 200
        assert client.get("/api/runs").status_code == 403
        assert client.post("/api/admin/users", json={"username": "synthetic-analyst", "display_name": "Synthetic analyst", "passcode": "generated-analyst-passcode"}).status_code == 201
        client.post("/api/auth/logout")
        assert client.post("/api/auth/login", json={"username": "synthetic-analyst", "passcode": "generated-analyst-passcode"}).status_code == 200
        assert client.get("/api/admin/users").status_code == 403
        credential = client.post("/api/credentials", json={"provider": "openai", "secret": "synthetic-never-sent-key", "label": "Synthetic"})
        assert credential.status_code in (200, 201), credential.text
        credential_id = credential.json()["credential_id"]
        case = client.get("/api/runs/investigation-cases/soc-auth-001").json()
        update = {key: case[key] for key in ("expected_decision", "dataset_category", "attack_targets")}
        update["base_version"] = case["case_version"]
        update["expected_decision"]["priority"] = "P2"
        assert client.put("/api/runs/investigation-cases/soc-auth-001", json=update).status_code == 200
        scenario = next(config.web.scenario_dir.glob("*.yaml"))
        scenario.write_bytes(scenario.read_bytes() + b"\n# synthetic persisted edit\n")
        edited_scenario = scenario.read_bytes()
        for path in ("/api/unknown", "/api/runs/99999"):
            response = client.get(path)
            assert response.status_code == 404 and response.headers["content-type"].startswith("application/json")
        assert client.post("/api/runs", json={}).status_code == 400
        result = complete_investigation(client, None, {"workflow": "mcp-investigation-v1", "provider": "scripted", "mode": "clean", "case_id": "soc-auth-001"})
        assert result.status_code == 200, result.text
        run_id = result.json()["run_id"]
        saved = client.get(f"/api/runs/{run_id}").json()
        assert saved["trace"]
        cookies = dict(client.cookies)
    with TestClient(build_application(config)) as restarted:
        restarted.cookies.update(cookies)
        assert restarted.get(f"/api/runs/{run_id}").json() == saved
        assert restarted.get("/api/runs/investigation-cases/soc-auth-001").json()["expected_decision"]["priority"] == "P2"
        assert scenario.read_bytes() == edited_scenario
        assert credential_id in str(restarted.get("/api/credentials").json())
    from poisontrace.bootstrap import build_web_backend
    from poisontrace.application.principals import Principal, principal_scope
    with principal_scope(Principal(2, "analyst")):
        assert build_web_backend(config=config.web).secrets.retrieve(credential_id) == "synthetic-never-sent-key"


def test_unavailable_root_fails_without_databases(tmp_path):
    env = environment(tmp_path)
    root = Path(env["POISONTRACE_DATA_ROOT"])
    root.write_text("not a directory")
    with pytest.raises(RuntimeError, match="storage"):
        build_application(RuntimeConfig.from_environment(env))
    assert list(tmp_path.glob("*.db")) == []
