"""Campaign behavior through explicit application dependencies."""
from pathlib import Path

import pytest

from poisontrace.application.campaigns import CampaignApplicationService
from poisontrace.application.runs import RunApplicationService
from poisontrace.adapters.models.fake import FakeModel
from poisontrace.adapters.persistence.campaigns import InMemoryCampaignStore
from poisontrace.adapters.persistence.traces import SqliteTraceStore
from poisontrace.adapters.scenarios.loader import CampaignScenarioFiles
from poisontrace.application.scenarios import ScenarioService
from poisontrace.adapters.scenarios.repository import YamlScenarioRepository
from poisontrace.application.ports import CredentialReference


@pytest.fixture
def campaign_dependencies(tmp_path):
    directory = tmp_path / "scenarios"
    directory.mkdir()
    source = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml")
    for name in ("b-poisoned.yaml", "a-poisoned.yaml", "clean.yaml"):
        (directory / name).write_bytes(source.read_bytes())
    store = SqliteTraceStore(tmp_path / "runs.db")
    campaigns = InMemoryCampaignStore()
    calls = []
    def factory(provider, model, api_key=None):
        calls.append((provider, model, api_key))
        return FakeModel()
    class Secrets:
        provider = "openai"
        def reference(self, cid):
            return CredentialReference(cid, self.provider, "test", "masked")
        def retrieve(self, cid):
            return "synthetic-key"
    secrets = Secrets()
    runs = RunApplicationService(store, ScenarioService(YamlScenarioRepository(directory)), factory)
    service = CampaignApplicationService(campaigns, store, CampaignScenarioFiles(directory), factory, runs.summary, secrets)
    return service, campaigns, store, directory, calls, secrets


def test_campaign_interface_owns_selection_execution_details_and_reruns(campaign_dependencies):
    service, campaigns, store, directory, calls, secrets = campaign_dependencies
    created = service.create({"provider": "openai", "model": "chosen", "credential_id": "ref"})
    cid = created["campaign_id"]
    assert created["scenario_filenames"] == ["a-poisoned.yaml", "b-poisoned.yaml"]
    assert service.get(cid) == created
    assert calls == []
    executed = service.execute(cid)
    assert (executed["completed"], executed["failed"], executed["attack_successes"]) == (2, 0, 2)
    assert calls == [("openai", "chosen", "synthetic-key")]
    detail = service.get(cid)
    for item in detail["scenarios"]:
        rid = item["child_run_id"]
        assert item["trace"] == [{"kind": e.kind, "data": e.data} for e in store.events_for(rid)]
        assert store.result_for(rid).run_configuration == {"campaign_id": cid, "provider": "openai", "credential_id": "ref", "model": "chosen", "mode": "poisoned", "scenario_id": "002"}
        assert item["outcome"] == "Attack success"
    old_id = detail["scenarios"][0]["child_run_id"]
    rerun = service.rerun(cid, 0)
    assert rerun["scenarios"][0]["child_run_id"] != old_id
    assert calls == [("openai", "chosen", "synthetic-key")] * 2
    assert "synthetic-key" not in str(rerun)
    assert service.list()[0]["completed"] == 2
    with pytest.raises(ValueError, match="already completed"):
        service.execute(cid)
    with pytest.raises(KeyError):
        service.rerun(cid, 2)


def test_campaign_failures_repair_and_credential_revalidation(campaign_dependencies):
    service, campaigns, store, directory, calls, secrets = campaign_dependencies
    created = service.create({"provider": "openai", "model": "chosen", "credential_id": "ref"})
    cid = created["campaign_id"]
    secrets.provider = "gemini"
    for operation in (lambda: service.create({"provider": "openai", "model": "chosen", "credential_id": "ref"}), lambda: service.execute(cid), lambda: service.rerun(cid, 0)):
        with pytest.raises(ValueError, match="does not match campaign provider"):
            operation()
    assert calls == []
    assert campaigns.get(cid)["status"] == "created"
    secrets.provider = "openai"
    path = directory / "a-poisoned.yaml"
    original = path.read_bytes()
    path.write_text("invalid: true", encoding="utf-8")
    with pytest.raises(ValueError):
        service.create({})
    executed = service.execute(cid)
    assert executed["status"] == "completed_with_errors"
    assert (executed["completed"], executed["failed"]) == (1, 1)
    assert service.get(cid)["scenarios"][0]["failure_state"] == "ValueError"
    assert service.rerun(cid, 0)["scenarios"][0]["error"] == "ValueError"
    path.write_bytes(original)
    repaired = service.rerun(cid, 0)
    assert repaired["status"] == "completed_with_errors"
    assert repaired["scenarios"][0]["error"] is None
    assert repaired["scenarios"][0]["outcome"] == "Attack success"
    assert service.list()[0]["failed"] == 0
    campaigns.associate_child_run(cid, 0, child_run_id=99999)
    assert service.get(cid)["scenarios"][0]["failure_state"] == "missing_child_run"
