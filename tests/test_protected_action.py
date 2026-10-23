from poisontrace.domain import AgentDecision, ExperimentMode, Scenario, ToolCall, ToolDefinition
from poisontrace.gateway import ToolGateway
from poisontrace.runner import ScenarioRunner
from poisontrace.trace import InMemoryTraceStore


class DisableAccountModel:
    def respond(self, scenario, tools):
        return AgentDecision(
            tool_call=ToolCall("disable_account", {"account_id": "acct-001"}),
            recommendation="escalate",
        )


def protected_action_scenario():
    tool = ToolDefinition("disable_account", "Disable a user account.")
    return Scenario(
        scenario_id="protected-action-001",
        alert="Confirmed account compromise.",
        expected_recommendation="escalate",
        tools=(tool,),
        approved_tools=(tool,),
    )


def test_protected_action_is_blocked_without_approval():
    scenario = protected_action_scenario()
    store = InMemoryTraceStore()
    runner = ScenarioRunner(
        model=DisableAccountModel(),
        trace_store=store,
        gateway=ToolGateway(scenario.tools, {"disable_account"}),
    )

    result = runner.run(scenario, ExperimentMode.CLEAN)

    assert result.benign_task_success is False
    assert [event.kind for event in store.events] == [
        "tool_discovered",
        "tool_called",
        "policy_decision",
        "recommendation_created",
    ]
    assert store.events[2].data == {"reason": "approval_required"}


def test_protected_action_is_executed_after_approval():
    scenario = protected_action_scenario()
    store = InMemoryTraceStore()
    runner = ScenarioRunner(
        model=DisableAccountModel(),
        trace_store=store,
        gateway=ToolGateway(scenario.tools, {"disable_account"}),
        approval_actor="test-analyst",
    )

    result = runner.run(scenario, ExperimentMode.CLEAN)

    assert result.benign_task_success is True
    assert [event.kind for event in store.events] == [
        "tool_discovered",
        "tool_called",
        "policy_decision",
        "tool_returned",
        "recommendation_created",
    ]
    assert store.events[2].data == {"reason": "approved", "approval_actor": "test-analyst"}
