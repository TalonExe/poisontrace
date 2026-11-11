import json

from poisontrace.domain import AgentDecision, Scenario, ToolCall, ToolDefinition


class FakeModel:
    model_name = "fake"
    prompt_version = "fake-v1"

    def respond(self, scenario: Scenario, tools: tuple[ToolDefinition, ...]) -> AgentDecision:
        raw_output = {
            "tool_name": "get_authentication_alert",
            "arguments": {"scenario_id": scenario.scenario_id},
            "recommendation": scenario.expected_recommendation,
        }
        if any("COMPROMISED" in tool.description for tool in tools):
            raw_output["marker"] = "COMPROMISED"
        decision = AgentDecision(
            tool_call=ToolCall("get_authentication_alert", {"scenario_id": scenario.scenario_id}),
            recommendation=scenario.expected_recommendation,
        )
        return AgentDecision(
            tool_call=decision.tool_call,
            recommendation=decision.recommendation,
            raw_output=json.dumps(raw_output),
        )
