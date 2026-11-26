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
    campaigns = InMemoryCampaignStore(store)
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
    assert (executed["completed"], executed["failed"], executed["attack_successes"]) == (2, 0, 0)
    assert calls == [("openai", "chosen", "synthetic-key")] * 2
    detail = service.get(cid)
    for item in detail["scenarios"]:
        rid = item["child_run_id"]
        assert item["trace"] == [{"kind": e.kind, "data": e.data} for e in store.events_for(rid)]
        assert store.result_for(rid).run_configuration.items() >= {"campaign_id": cid, "provider": "openai", "credential_id": "ref", "model": "chosen", "mode": "poisoned", "scenario_id": "002"}.items()
        assert item["outcome"] == "Marker observed"
    old_id = detail["scenarios"][0]["child_run_id"]
    rerun = service.rerun(cid, 0)
    assert rerun["scenarios"][0]["child_run_id"] != old_id
    assert calls == [("openai", "chosen", "synthetic-key")] * 3
    assert "synthetic-key" not in str(rerun)
    summary = service.list()[0]
    assert summary["completed"] == 2
    assert summary["metrics"]["attempted"] == 3
    assert summary["metrics"]["by_condition"]["poisoned"]["attacker_goal"]["value"] is None
    assert summary["metrics"]["by_condition"]["poisoned"]["marker_influence"]["denominator"] == 3
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
    assert service.create({})["excluded_files"] == ["a-poisoned.yaml"]
    executed = service.execute(cid)
    assert executed["status"] == "completed_with_errors"
    assert (executed["completed"], executed["failed"]) == (1, 1)
    assert service.get(cid)["scenarios"][0]["failure_state"] == "ValueError"
    assert service.rerun(cid, 0)["scenarios"][0]["error"] == "ValueError"
    path.write_bytes(original)
    repaired = service.rerun(cid, 0)
    assert repaired["status"] == "completed_with_errors"
    assert repaired["scenarios"][0]["error"] is None
    assert repaired["scenarios"][0]["outcome"] == "Marker observed"
    assert service.list()[0]["failed"] == 0
    with pytest.raises(KeyError):
        campaigns.associate_child_run(cid, 0, child_run_id=99999)
    # Synthetic corrupt storage fixture, never a permitted application association.
    campaigns.campaigns[cid]['scenarios'][0]['child_run_id'] = 99999
    assert service.get(cid)["scenarios"][0]["failure_state"] == "missing_child_run"

def test_campaign_retains_provider_failures_and_uses_returned_ids(campaign_dependencies):
    service, campaigns, store, directory, calls, secrets = campaign_dependencies
    def fail(*args): raise RuntimeError('synthetic-secret provider body')
    from poisontrace.application.runs import RunApplicationService
    from poisontrace.adapters.scenarios.loader import CampaignScenarioFiles
    service = CampaignApplicationService(campaigns, store, CampaignScenarioFiles(directory), fail, RunApplicationService(store, None, None).summary)
    created = service.create({'provider': 'fake'})
    cid = created['campaign_id']
    executed = service.execute(cid)
    assert (executed['completed'], executed['failed']) == (0, 2)
    detail = service.get(cid)
    assert len(store.run_ids()) == 2
    for child in detail['scenarios']:
        assert child['child_run_id'] is not None
        assert child['status'] == 'failed'
        assert child['marker_influence'] is None
        assert child['trace'][-1]['kind'] == 'experiment_failed'
    assert 'synthetic-secret' not in str(detail)
    assert service.list()[0]['completed'] == 0
    assert service.list()[0]['metrics']['system_error_rate'] == 1
    assert service.list()[0]['metrics']['by_condition']['poisoned']['attacker_goal']['value'] is None


# Trusted caller for direct application checks; HTTP still authenticates independently.
pytestmark = pytest.mark.usefixtures("application_analyst")
