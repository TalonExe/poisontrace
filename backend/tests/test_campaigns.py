from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    __import__("importlib.util").util.find_spec("fastapi") is None,
    reason="install the optional web dependencies to run HTTP endpoint tests",
)


def test_campaign_creation_discovers_poisoned_files_and_persists_without_secret(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig
    from poisontrace.application.ports import CredentialReference

    class ReferencesOnlySecrets:
        def reference(self, credential_id):
            return CredentialReference(credential_id, "fake", "test", "••••••••")

    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    source = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml")
    scenario_text = source.read_text(encoding="utf-8")
    (scenario_dir / "z-poisoned.yaml").write_text(scenario_text, encoding="utf-8")
    (scenario_dir / "a-poisoned.yaml").write_text(scenario_text, encoding="utf-8")
    (scenario_dir / "clean.yaml").write_text(scenario_text, encoding="utf-8")

    database = tmp_path / "runs.db"
    client = analyst_client(create_app(build_backend(WebConfig(scenario_dir=scenario_dir, database=database), ReferencesOnlySecrets())))
    response = client.post(
        "/api/campaigns",
        json={
            "provider": "fake",
            "model": "fake-model",
            "credential_id": "cred-123",
        },
    )

    assert response.status_code == 201
    campaign = response.json()
    assert campaign["status"] == "created"
    assert campaign["scenario_filenames"] == ["a-poisoned.yaml", "z-poisoned.yaml"]
    assert campaign["provider"] == "fake"
    assert campaign["model"] == "fake-model"
    assert campaign["credential_id"] == "cred-123"

    reloaded = analyst_client(create_app(build_backend(WebConfig(scenario_dir=scenario_dir, database=database), ReferencesOnlySecrets()))).get(
        f"/api/campaigns/{campaign['campaign_id']}"
    )
    assert reloaded.status_code == 200
    assert reloaded.json() == campaign

    raw_database = database.read_bytes()
    assert b"secret" not in raw_database
    assert b"clean.yaml" not in raw_database


def test_campaign_creation_rejects_when_no_poisoned_scenarios_exist(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    (scenario_dir / "clean.yaml").write_text("not used", encoding="utf-8")
    client = analyst_client(create_app(build_backend(WebConfig(scenario_dir=scenario_dir, database=tmp_path / "runs.db"))))

    response = client.post("/api/campaigns", json={"provider": "fake", "model": "fake"})

    assert response.status_code == 400
    assert response.json()["detail"] == "no poisoned scenarios found"


def test_campaign_execution_runs_each_selected_scenario_once_and_aggregates_results(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    first = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml").read_text(encoding="utf-8")
    second = Path("backend/tests/fixtures/scenarios/authentication-alert-strong-poisoned-003.yaml").read_text(encoding="utf-8")
    (scenario_dir / "b-poisoned.yaml").write_text(first, encoding="utf-8")
    (scenario_dir / "a-poisoned.yaml").write_text(second, encoding="utf-8")

    backend = build_backend(WebConfig(scenario_dir=scenario_dir, database=tmp_path / "runs.db"))
    client = analyst_client(create_app(backend))
    created = client.post("/api/campaigns", json={"provider": "fake", "model": "fake-campaign-model"})
    assert created.status_code == 201

    executed = client.post(f"/api/campaigns/{created.json()['campaign_id']}/execute")

    assert executed.status_code == 200
    campaign = executed.json()
    assert campaign["status"] == "completed"
    assert campaign["total"] == 2
    assert campaign["completed"] == 2
    assert campaign["failed"] == 0
    assert campaign["attack_successes"] == 2
    assert [item["filename"] for item in campaign["scenarios"]] == ["a-poisoned.yaml", "b-poisoned.yaml"]
    assert all(item["child_run_id"] is not None for item in campaign["scenarios"])
    assert all(item["model"] == "fake" for item in campaign["results"])

    reloaded = client.get(f"/api/campaigns/{campaign['campaign_id']}")
    assert reloaded.status_code == 200
    assert reloaded.json()["status"] == "completed"
    assert [item["child_run_id"] for item in reloaded.json()["scenarios"]] == [
        item["child_run_id"] for item in campaign["scenarios"]
    ]


def test_campaign_execution_continues_after_a_child_failure(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    scenario_text = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml").read_text(encoding="utf-8")
    (scenario_dir / "a-poisoned.yaml").write_text(scenario_text, encoding="utf-8")
    (scenario_dir / "b-poisoned.yaml").write_text(scenario_text, encoding="utf-8")

    backend = build_backend(WebConfig(scenario_dir=scenario_dir, database=tmp_path / "runs.db"))
    client = analyst_client(create_app(backend))
    created = client.post("/api/campaigns", json={"provider": "fake"}).json()
    (scenario_dir / "a-poisoned.yaml").write_text("invalid: true", encoding="utf-8")

    executed = client.post(f"/api/campaigns/{created['campaign_id']}/execute")

    assert executed.status_code == 200
    campaign = executed.json()
    assert campaign["status"] == "completed_with_errors"
    assert campaign["total"] == 2
    assert campaign["completed"] == 1
    assert campaign["failed"] == 1
    assert campaign["scenarios"][0]["error"] == "ValueError"
    assert campaign["scenarios"][1]["child_run_id"] is not None


def test_campaign_history_lists_persisted_summary(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    source = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml").read_text(encoding="utf-8")
    (scenario_dir / "only-poisoned.yaml").write_text(source, encoding="utf-8")
    client = analyst_client(create_app(build_backend(WebConfig(scenario_dir=scenario_dir, database=tmp_path / "runs.db"))))
    created = client.post("/api/campaigns", json={"provider": "fake"}).json()
    client.post(f"/api/campaigns/{created['campaign_id']}/execute")

    response = client.get("/api/campaigns")

    assert response.status_code == 200
    assert response.json() == [
        {
            "campaign_id": created["campaign_id"],
            "status": "completed",
            "provider": "fake",
            "model": "fake",
            "credential_id": None,
            "scenario_count": 1,
            "completed": 1,
            "failed": 0,
            "attack_successes": 1,
            "injection_successes": 1,
            "task_successes": 0,
        }
    ]


def test_campaign_scenario_details_and_rerun_preserve_campaign_configuration(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig
    from poisontrace.application.ports import CredentialReference

    class ReferencesOnlySecrets:
        def reference(self, credential_id):
            return CredentialReference(credential_id, "fake", "test", "••••••••")

        def retrieve(self, credential_id):
            return "synthetic-secret"

    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    source = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml").read_text(encoding="utf-8")
    (scenario_dir / "only-poisoned.yaml").write_text(source, encoding="utf-8")
    client = analyst_client(create_app(build_backend(WebConfig(scenario_dir=scenario_dir, database=tmp_path / "runs.db"), ReferencesOnlySecrets())))

    created = client.post(
        "/api/campaigns",
        json={"provider": "fake", "model": "campaign-model", "credential_id": "cred-ref"},
    ).json()
    executed = client.post(f"/api/campaigns/{created['campaign_id']}/execute")
    assert executed.status_code == 200

    detail = client.get(f"/api/campaigns/{created['campaign_id']}")
    assert detail.status_code == 200
    scenario = detail.json()["scenarios"][0]
    assert scenario["filename"] == "only-poisoned.yaml"
    assert scenario["scenario_id"] == "002"
    assert scenario["child_run_id"] is not None
    assert scenario["outcome"] == "Attack success"
    assert scenario["failure_state"] is None
    assert "secret" not in detail.text

    rerun = client.post(f"/api/campaigns/{created['campaign_id']}/scenarios/0/rerun")
    assert rerun.status_code == 200
    rerun_scenario = rerun.json()["scenarios"][0]
    assert rerun.json()["provider"] == "fake"
    assert rerun.json()["model"] == "campaign-model"
    assert rerun.json()["credential_id"] == "cred-ref"
    assert rerun_scenario["child_run_id"] != scenario["child_run_id"]
    assert rerun_scenario["outcome"] == "Attack success"
    assert rerun_scenario["failure_state"] is None


def test_complete_campaign_workflow_is_available_through_public_http_seams(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    source = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml").read_text(encoding="utf-8")
    (scenario_dir / "b-poisoned.yaml").write_text(source, encoding="utf-8")
    (scenario_dir / "a-poisoned.yaml").write_text(source, encoding="utf-8")
    client = analyst_client(create_app(build_backend(WebConfig(scenario_dir=scenario_dir, database=tmp_path / "runs.db"))))

    created = client.post("/api/campaigns", json={"provider": "fake", "model": "workflow-model"})
    assert created.status_code == 201
    campaign_id = created.json()["campaign_id"]
    assert created.json()["status"] == "created"
    assert created.json()["scenario_filenames"] == ["a-poisoned.yaml", "b-poisoned.yaml"]

    executed = client.post(f"/api/campaigns/{campaign_id}/execute")
    assert executed.status_code == 200
    assert executed.json()["status"] == "completed"
    original_child_runs = [item["child_run_id"] for item in executed.json()["scenarios"]]

    history = client.get("/api/campaigns")
    assert history.status_code == 200
    assert history.json()[0]["campaign_id"] == campaign_id
    assert history.json()[0]["completed"] == 2
    assert history.json()[0]["attack_successes"] == 2

    details = client.get(f"/api/campaigns/{campaign_id}")
    assert details.status_code == 200
    assert all(item["outcome"] == "Attack success" for item in details.json()["scenarios"])

    rerun = client.post(f"/api/campaigns/{campaign_id}/scenarios/1/rerun")
    assert rerun.status_code == 200
    assert rerun.json()["scenarios"][1]["child_run_id"] != original_child_runs[1]

    refreshed_history = client.get("/api/campaigns")
    assert refreshed_history.status_code == 200
    assert refreshed_history.json()[0]["completed"] == 2
    assert refreshed_history.json()[0]["attack_successes"] == 2


def test_campaign_http_errors_and_ordered_child_traces(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig

    directory = tmp_path / "scenarios"
    directory.mkdir()
    source = Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml")
    (directory / "only-poisoned.yaml").write_bytes(source.read_bytes())
    backend = build_backend(WebConfig(scenario_dir=directory, database=tmp_path / "runs.db"))
    client = analyst_client(create_app(backend))
    for suffix in ("", "/execute", "/scenarios/0/rerun"):
        response = client.get("/api/campaigns/missing") if not suffix else client.post("/api/campaigns/missing" + suffix)
        assert response.status_code == 404
    for payload in ({"secret": "synthetic"}, {"provider": "unknown"}, {"provider": "openai"}, {"credential_id": "missing"}):
        assert client.post("/api/campaigns", json=payload).status_code == 400
    campaign = client.post("/api/campaigns", json={}).json()
    cid = campaign["campaign_id"]
    assert client.post(f"/api/campaigns/{cid}/scenarios/-1/rerun").status_code == 404
    assert client.post(f"/api/campaigns/{cid}/execute").status_code == 200
    assert client.post(f"/api/campaigns/{cid}/execute").status_code == 400
    child = client.get(f"/api/campaigns/{cid}").json()["scenarios"][0]
    assert child["trace"] == [{"kind": event.kind, "data": event.data} for event in backend.store.events_for(child["child_run_id"])]
    assert child["trace"][-1]["kind"] == "recommendation_created"
