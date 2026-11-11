"""Run orchestration through its application interface, without HTTP composition."""

from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from poisontrace.adapters.models.fake import FakeModel
from poisontrace.application.runs import RunApplicationService
from poisontrace.adapters.persistence.traces import SqliteTraceStore
from poisontrace.application.scenarios import ScenarioService
from poisontrace.adapters.scenarios.repository import YamlScenarioRepository
from poisontrace.adapters.secrets.storage import EncryptedSqliteSecrets


@pytest.fixture
def run_dependencies(tmp_path):
    directory = tmp_path / "scenarios"
    directory.mkdir()
    for name in ("authentication-alert-001.yaml", "authentication-alert-poisoned-002.yaml"):
        source = Path("backend/tests/fixtures/scenarios") / name
        (directory / name).write_bytes(source.read_bytes())
    (directory / "broken.yaml").write_text("scenario_id: '999'\nname: Broken\n", encoding="utf-8")
    return SqliteTraceStore(tmp_path / "runs.db"), ScenarioService(YamlScenarioRepository(directory))


@pytest.mark.parametrize("scenario_id,mode,verdict,tool_status", [
    ("001", "clean", "Blocked", "Executed"),
    ("002", "poisoned", "Attack success", "Executed"),
    ("002", "defended", "Attack success", "Blocked"),
])
def test_run_module_creates_lists_and_reads_persisted_evidence(run_dependencies, scenario_id, mode, verdict, tool_status):
    store, scenarios = run_dependencies
    calls = []

    def model_factory(provider, model, api_key=None):
        calls.append((provider, model, api_key))
        return FakeModel()

    runs = RunApplicationService(store, scenarios, model_factory)
    created = runs.create({"scenario_id": scenario_id, "mode": mode, "provider": "fake", "session_id": "study"})
    assert created["mode"] == mode.title()
    assert created["injection_verdict"] == verdict
    assert created["tool_call_status"] == tool_status
    assert calls == [("fake", None, None)]
    assert runs.list() == [created]
    assert runs.summary(created["run_id"]) == created
    detail = runs.get(created["run_id"])
    assert detail["run_configuration"]["session_id"] == "study"
    assert detail["metrics"]["injection_verdict"] == verdict
    assert detail["trace"] == [{"kind": event.kind, "data": event.data} for event in store.events_for(created["run_id"])]
    assert detail["trace"][-1]["kind"] == "recommendation_created"


def test_run_module_supplies_only_the_selected_key_to_injected_model(run_dependencies, tmp_path):
    store, scenarios = run_dependencies
    secrets = EncryptedSqliteSecrets(tmp_path / "secrets.db", Fernet.generate_key())
    reference = secrets.save("openai", "synthetic-provider-key")
    calls = []

    def model_factory(provider, model, api_key=None):
        calls.append((provider, model, api_key))
        return FakeModel()

    runs = RunApplicationService(store, scenarios, model_factory, secrets)
    created = runs.create({"scenario_id": "001", "provider": "openai", "model": "chosen-model", "credential_id": reference.credential_id})
    assert calls == [("openai", "chosen-model", "synthetic-provider-key")]
    detail = runs.get(created["run_id"])
    assert detail["run_configuration"]["credential_id"] == reference.credential_id
    assert "synthetic-provider-key" not in str(detail)
    with pytest.raises(ValueError, match="does not match run provider"):
        runs.create({"scenario_id": "001", "provider": "gemini", "credential_id": reference.credential_id})
    assert len(calls) == 1


@pytest.mark.parametrize("payload,error", [
    ({"scenario_id": "001", "provider": "unknown"}, ValueError),
    ({"scenario_id": "001", "mode": "unknown"}, ValueError),
    ({"scenario_id": "missing", "provider": "fake"}, KeyError),
    ({"scenario_id": "broken.yaml", "provider": "fake"}, ValueError),
])
def test_rejected_runs_do_not_construct_models_or_persist_results(run_dependencies, payload, error):
    store, scenarios = run_dependencies

    def model_factory(provider, model, api_key=None):
        pytest.fail("rejected input reached model construction")

    runs = RunApplicationService(store, scenarios, model_factory)
    with pytest.raises(error):
        runs.create(payload)
    assert store.run_ids() == []
