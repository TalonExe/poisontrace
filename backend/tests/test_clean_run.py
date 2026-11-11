from poisontrace.adapters.models.fake import FakeModel
from poisontrace.domain import ExperimentMode, Scenario
from poisontrace.application.gateway import ToolGateway
from poisontrace.application.execution import ScenarioRunner
from poisontrace.adapters.persistence.traces import InMemoryTraceStore


def test_clean_authentication_alert_run_records_benign_success():
    scenario = Scenario.authentication_alert()
    trace_store = InMemoryTraceStore()
    runner = ScenarioRunner(
        model=FakeModel(),
        trace_store=trace_store,
        gateway=ToolGateway(approved_manifest=scenario.tools, high_impact_tools=set()),
    )

    result = runner.run(scenario, ExperimentMode.CLEAN)

    assert result.benign_task_success is True
    assert result.attack_success is False
    assert result.recommendation == "escalate"
    assert [event.kind for event in trace_store.events] == [
        "tool_discovered",
        "agent_output",
        "tool_called",
        "policy_decision",
        "tool_returned",
        "recommendation_created",
    ]
