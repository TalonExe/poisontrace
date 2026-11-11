"""Configuration and concrete web composition through startup interfaces."""
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from poisontrace.config import WebConfig
from poisontrace.bootstrap import build_web_backend, build_backend, create_app
from poisontrace.adapters.models.fake import FakeModel
from poisontrace.adapters.secrets.storage import EncryptedSqliteSecrets


def test_config_preserves_defaults_and_hides_key():
    key = Fernet.generate_key().decode()
    config = WebConfig.from_environment({"POISONTRACE_SECRETS_KEY": key})
    assert config.scenario_dir == Path("backend/scenarios")
    assert config.database == Path("poisontrace.db")
    assert config.secrets_database == Path("poisontrace-secrets.db")
    assert config.require_secrets_key() == key.encode()
    assert key not in repr(config)
    with pytest.raises(RuntimeError, match="POISONTRACE_SECRETS_KEY is required"):
        WebConfig.from_environment({}).require_secrets_key()
    with pytest.raises(ValueError, match="Fernet key"):
        WebConfig(secrets_key=b"invalid").require_secrets_key()


def test_local_bootstrap_validates_before_creating_files(tmp_path):
    config = WebConfig(scenario_dir=tmp_path, database=tmp_path / "runs.db", secrets_database=tmp_path / "secrets.db")
    with pytest.raises(RuntimeError, match="POISONTRACE_SECRETS_KEY is required"):
        build_web_backend(config=config)
    assert list(tmp_path.iterdir()) == []
    backend = build_web_backend(config=WebConfig(scenario_dir=tmp_path, database=config.database, secrets_database=config.secrets_database, secrets_key=Fernet.generate_key()))
    saved = backend.credentials.save({"provider": "fake", "secret": "synthetic-key"})
    assert backend.secrets.retrieve(saved["credential_id"]) == "synthetic-key"
    assert config.database.exists() and config.secrets_database.exists()


def test_backend_composes_shared_dependencies_and_http_without_secret_key(tmp_path, analyst_client):
    scenario = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml")
    (tmp_path / "one-poisoned.yaml").write_bytes(scenario.read_bytes())
    config = WebConfig(scenario_dir=tmp_path, database=tmp_path / "runs.db")
    calls = []
    def factory(provider, model, api_key=None):
        calls.append((provider, model, api_key))
        return FakeModel()
    backend = build_backend(config, model_factory=factory)
    assert backend.runs.store is backend.store
    assert backend.secrets is None
    created = backend.campaign_service.create({})
    assert backend.campaign_service.execute(created["campaign_id"])["completed"] == 1
    assert calls == [("fake", "fake", None)]
    client = analyst_client(create_app(backend))
    assert client.get("/api/campaigns").json()[0]["completed"] == 1
    assert client.get("/api/credentials").status_code == 503


def test_managed_bootstrap_needs_no_local_key_or_secret_database(tmp_path):
    class Client:
        def put_secret(self, *args): pass
        def get_secret(self, cid): return "synthetic-managed-key"
        def delete_secret(self, cid): pass
    config = WebConfig(scenario_dir=tmp_path, database=tmp_path / "runs.db", secrets_database=tmp_path / "unused.db")
    backend = build_web_backend(config=config, managed_secret_client=Client())
    saved = backend.credentials.save({"provider": "fake", "secret": "synthetic-managed-key"})
    assert backend.secrets.retrieve(saved["credential_id"]) == "synthetic-managed-key"
    assert not config.secrets_database.exists()


def test_model_composition_preserves_provider_defaults_and_keys(monkeypatch):
    from poisontrace import bootstrap
    calls = []
    def construct(*, model_name, api_key):
        calls.append((model_name, api_key))
        return FakeModel()
    monkeypatch.setattr(bootstrap, "GeminiModel", construct)
    monkeypatch.setattr(bootstrap, "OpenAIModel", construct)
    assert isinstance(bootstrap.build_model("fake", None), FakeModel)
    bootstrap.build_model("gemini", None, "synthetic-gemini")
    bootstrap.build_model("openai", None, "synthetic-openai")
    bootstrap.build_model("openai", "chosen", "synthetic-key")
    assert calls == [("gemini-3.5-flash-lite", "synthetic-gemini"), ("gpt-5-mini", "synthetic-openai"), ("chosen", "synthetic-key")]
    with pytest.raises(ValueError, match="unsupported provider"):
        bootstrap.build_model("unknown", None)


def test_bootstrap_import_does_not_start_web_or_create_storage(tmp_path):
    import os
    import subprocess
    import sys
    environment = os.environ.copy()
    environment.pop("POISONTRACE_SECRETS_KEY", None)
    environment["PYTHONPATH"] = str(Path("backend/src").resolve())
    result = subprocess.run(
        [sys.executable, "-c", "import sys; import poisontrace.bootstrap; assert 'poisontrace.web' not in sys.modules"],
        cwd=tmp_path, env=environment, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []


def test_default_app_factory_stays_key_optional(tmp_path, monkeypatch, analyst_client):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("POISONTRACE_SECRETS_KEY", raising=False)
    client = analyst_client(create_app())
    assert client.get("/api/runs").json() == []
    assert client.get("/api/credentials").status_code == 503
    assert not (tmp_path / "poisontrace-secrets.db").exists()


def test_web_entrypoint_constructs_configured_app(tmp_path):
    import os
    import subprocess
    import sys

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path("backend/src").resolve())
    environment["POISONTRACE_SECRETS_KEY"] = Fernet.generate_key().decode()
    environment.pop("POISONTRACE_ANALYST_PASSCODE", None)
    environment.pop("POISONTRACE_SUPERADMIN_PASSCODE", None)
    script = """
from pathlib import Path
from fastapi import FastAPI
from poisontrace.web import app
assert isinstance(app, FastAPI)
assert Path('poisontrace.db').is_file()
assert Path('poisontrace-secrets.db').is_file()
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=tmp_path, env=environment,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr


def test_backend_runs_and_lists_persisted_results(tmp_path):
    backend = build_backend(WebConfig(scenario_dir=tmp_path / "scenarios", database=tmp_path / "runs.db"))
    (tmp_path / "scenarios").mkdir()
    source = __import__("pathlib").Path("backend/tests/fixtures/scenarios/authentication-alert-001.yaml")
    (tmp_path / "scenarios/authentication-alert-001.yaml").write_text(
        source.read_text(encoding="utf-8"), encoding="utf-8"
    )

    created = backend.runs.create(
        {
            "session_id": "session-1",
            "scenario_id": "001",
            "mode": "defended",
            "provider": "fake",
        }
    )

    assert created["id"] == "EXP-001"
    assert created["mode"] == "Defended"
    assert backend.runs.list() == [created]
    assert backend.store.result_for(1).run_configuration["session_id"] == "session-1"


def test_backend_rejects_unknown_provider(tmp_path):
    backend = build_backend(WebConfig(scenario_dir=tmp_path, database=tmp_path / "runs.db"))
    try:
        backend.runs.create({"provider": "local"})
    except ValueError as error:
        assert "unsupported provider" in str(error)
    else:
        raise AssertionError("unknown provider was accepted")


def test_backend_rejects_unknown_credential_reference(tmp_path):
    backend = build_backend(WebConfig(scenario_dir=tmp_path, database=tmp_path / "runs.db"))
    try:
        backend.runs.create({"provider": "fake", "credential_id": "cred-missing"})
    except ValueError as error:
        assert "credential storage" in str(error)
    else:
        raise AssertionError("unknown credential reference was accepted")


def test_backend_rejects_credential_for_the_wrong_provider(tmp_path):
    secrets = EncryptedSqliteSecrets(tmp_path / "secrets.db", Fernet.generate_key())
    reference = secrets.save("openai", "sk-test-secret", "OpenAI")
    backend = build_backend(WebConfig(scenario_dir=tmp_path, database=tmp_path / "runs.db"), secrets)

    try:
        backend.runs.create({"provider": "gemini", "credential_id": reference.credential_id})
    except ValueError as error:
        assert "provider" in str(error)
    else:
        raise AssertionError("a credential for another provider was accepted")


def test_run_detail_exposes_separate_injection_task_and_tool_outcomes(tmp_path):
    backend = build_backend(WebConfig(scenario_dir=tmp_path / "scenarios", database=tmp_path / "runs.db"))
    (tmp_path / "scenarios").mkdir()
    source = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml")
    (tmp_path / "scenarios/authentication-alert-poisoned-002.yaml").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    created = backend.runs.create({"scenario_id": "002", "mode": "poisoned", "provider": "fake"})
    detail = backend.runs.get(created["run_id"])
    assert detail["injection_verdict"] == "Attack success"
    assert detail["task_outcome"] == "Failed"
    assert detail["tool_call_status"] == "Executed"
    assert detail["attack_success"] is True
    assert detail["benign_task_success"] is False
