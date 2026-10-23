from poisontrace.domain import AgentDecision, Scenario, ToolCall, ToolDefinition


class FakeModel:
    model_name = "fake"
    prompt_version = "fake-v1"

    def respond(self, scenario: Scenario, tools: tuple[ToolDefinition, ...]) -> AgentDecision:
        return AgentDecision(
            tool_call=ToolCall("get_authentication_alert", {"scenario_id": scenario.scenario_id}),
            recommendation=scenario.expected_recommendation,
        )
