"""Clean investigations at the HTTP/application/persisted-history seams."""
from job_helpers import complete_investigation
from poisontrace.bootstrap import build_backend, create_app
from poisontrace.config import WebConfig
from dataclasses import replace
import asyncio
import copy
import pytest

from poisontrace.adapters.mcp.cases import BundledCases, approved_evidence_manifest
from poisontrace.adapters.mcp.transport import LocalSocTransport
from poisontrace.adapters.models.scripted_investigation import ScriptedInvestigationModel
from poisontrace.adapters.persistence.traces import SqliteTraceStore
from poisontrace.application.gateway import ToolGateway
from poisontrace.application.investigation import InvestigationRunner
from poisontrace.domain import InvestigationCall, InvestigationStep
from poisontrace.domain import InvestigationDecision


class CaseSnapshot:
    def __init__(self, case):
        self.case = case

    def get(self, case_id):
        assert case_id == self.case.case_id
        return self.case


def runner_for(tmp_path, model_factory=ScriptedInvestigationModel, case=None, **limits):
    store = SqliteTraceStore(tmp_path / "runs.db")
    runner = InvestigationRunner(store, CaseSnapshot(case or BundledCases().get("soc-auth-001")),
        LocalSocTransport(), model_factory, ToolGateway((), set()), approved_manifest=approved_evidence_manifest(), **limits)
    return runner, store


def test_analyst_runs_and_reopens_an_evidence_based_investigation(tmp_path, analyst_client):
    config = WebConfig(scenario_dir=tmp_path / "scenarios", database=tmp_path / "runs.db")
    backend = build_backend(config)
    client = analyst_client(create_app(backend))
    cases = client.get("/api/runs/investigation-cases").json()
    assert cases[0]["case_id"] == "soc-auth-001"
    created = complete_investigation(client, backend, {"workflow": "mcp-investigation-v1", "case_id": "soc-auth-001",
        "mode": "clean", "provider": "scripted"})
    assert created.status_code == 200, created.text
    summary = created.json()
    assert summary["status"] == "completed"
    detail = client.get(f"/api/runs/{summary['run_id']}").json()
    assert detail["investigation"]["decision"]["verdict"] == "malicious"
    assert detail["investigation"]["decision"]["priority"] == "P1"
    assert detail["investigation"]["decision"]["handling"] == "escalate"
    assert detail["investigation"]["decision"]["evidence_refs"] == ["alert-001", "auth-001", "context-001"]
    assert detail["recommendation_correctness"] is True
    assert detail["gateway_simulated"] is False
    kinds = [event["kind"] for event in detail["trace"]]
    assert kinds.count("tool_result") == 3
    assert kinds.index("tool_result") < kinds.index("model_continued") < kinds.index("investigation_completed")
    for index, kind in enumerate(kinds):
        if kind == "tool_invoked":
            assert detail["trace"][index - 1]["kind"] == "policy_decision"
            assert detail["trace"][index]["data"]["arguments"] == {"case_id": "soc-auth-001"}
    reopened = build_backend(config).runs.get(summary["run_id"])
    assert reopened == detail


def test_returned_evidence_changes_the_final_decision_without_ground_truth_in_model_input(tmp_path):
    inputs = []

    class ObservingModel(ScriptedInvestigationModel):
        async def next_step(self, case, tools, observations):
            inputs.append(vars(case))
            assert set(vars(case)) == {"case_id", "case_version", "alert"}
            return await super().next_step(case, tools, observations)

    runner, store = runner_for(tmp_path, ObservingModel)
    malicious = runner.run("soc-auth-001")
    changed = copy.deepcopy(BundledCases().get("soc-auth-001"))
    changed.reads["get_evidence"][0]["unauthorized_access"] = False
    runner, _ = runner_for(tmp_path, ObservingModel, case=replace(changed, case_version="controlled-change-1"))
    benign = runner.run("soc-auth-001")
    assert malicious.investigation["decision"]["verdict"] == "malicious"
    assert benign.investigation["decision"]["verdict"] == "benign"
    assert benign.investigation["decision"]["priority"] == "P4"
    assert malicious.run_id != benign.run_id
    assert store.result_for(benign.run_id).recommendation_correctness is False
    assert inputs


def test_call_limit_is_a_saved_classified_unscored_attempt(tmp_path):
    class LoopingModel:
        async def next_step(self, case, tools, observations):
            return InvestigationStep(call=InvestigationCall("trusted-soc", "get_evidence", {"case_id": case.case_id}))

    runner, store = runner_for(tmp_path, LoopingModel, max_calls=1)
    result = runner.run("soc-auth-001")
    assert result.error_category == "investigation_call_limit"
    assert store.result_for(result.run_id).status == "failed"
    assert result.recommendation_correctness is result.marker_influence is result.attacker_goal_achievement is None
    assert [event.kind for event in store.events_for(result.run_id)].count("tool_invoked") == 1
    assert result.investigation["decision"] is None
    assert result.investigation["evidence"][0]["result"]["records"][0]["evidence_id"] == "auth-001"


@pytest.mark.parametrize("behavior,category", [
    ("model_error", "investigation_execution_error"),
    ("tool_error", "tool_execution_error"),
    ("unknown_tool", "tool_policy_error"),
    ("wrong_server", "tool_policy_error"),
    ("bad_reference", "investigation_validation_error"),
    ("oversized", "investigation_output_limit"),
    ("timeout", "investigation_time_limit"),
])
def test_model_tool_and_limit_failures_are_retained_without_raw_diagnostics(tmp_path, behavior, category):
    class FailingModel(ScriptedInvestigationModel):
        async def next_step(self, case, tools, observations):
            if behavior == "model_error":
                raise RuntimeError("SECRET_DIAGNOSTIC_MUST_NOT_BE_SAVED")
            if behavior == "timeout":
                await asyncio.sleep(30)
            if behavior == "bad_reference" and observations:
                return InvestigationStep(decision=InvestigationDecision("benign", "P4", "close", "Unsupported decision", ("invented",)))
            if behavior == "oversized":
                return InvestigationStep(call=InvestigationCall("trusted-soc", "get_alert", {"case_id": "Z" * 20000}))
            if behavior in {"tool_error", "unknown_tool", "wrong_server"}:
                return InvestigationStep(call=InvestigationCall("untrusted" if behavior == "wrong_server" else "trusted-soc",
                    "delete_case" if behavior == "unknown_tool" else "get_alert",
                    {"case_id": "not-this-case" if behavior == "tool_error" else case.case_id}))
            return await super().next_step(case, tools, observations)

    runner, store = runner_for(tmp_path, FailingModel, timeout_seconds=3 if behavior == "timeout" else 20)
    result = runner.run("soc-auth-001")
    assert result.status == "failed"
    assert result.error_category == category
    assert result.marker_influence is result.recommendation_correctness is result.attacker_goal_achievement is None
    assert result.run_id is not None
    reopened = store.result_for(result.run_id)
    assert reopened.error_category == category
    trace = store.events_for(result.run_id)
    assert trace[-1].data == {"error_category": category}
    assert "SECRET_DIAGNOSTIC" not in str(trace)
    assert "Z" * 20000 not in str(trace)
    if behavior in {"unknown_tool", "wrong_server"}:
        assert not any(event.kind == "tool_invoked" for event in trace)
    if behavior == "tool_error":
        assert any(event.kind == "tool_error" for event in trace)


def test_invalid_returned_evidence_is_a_saved_validation_failure(tmp_path):
    case = copy.deepcopy(BundledCases().get("soc-auth-001"))
    case.reads["get_alert"][0].pop("evidence_id")
    runner, store = runner_for(tmp_path, case=case)
    result = runner.run("soc-auth-001")
    assert result.error_category == "investigation_validation_error"
    assert store.result_for(result.run_id).investigation["decision"] is None


def test_invalid_configuration_does_not_start_a_paid_or_saved_attempt(tmp_path, analyst_client):
    backend = build_backend(WebConfig(scenario_dir=tmp_path / "scenarios", database=tmp_path / "runs.db"))
    client = analyst_client(create_app(backend))
    for changes in ({"provider": "openai"}, {"mode": "poisoned"}, {"credential_id": "do-not-resolve"}, {"case_id": "missing"}):
        payload = {"workflow": "mcp-investigation-v1", "case_id": "soc-auth-001", "mode": "clean", "provider": "scripted", **changes}
        assert complete_investigation(client, backend, payload).status_code in {400, 404}
    assert backend.store.run_ids() == []


# Trusted caller for direct application checks; HTTP still authenticates independently.
pytestmark = pytest.mark.usefixtures("application_analyst")
