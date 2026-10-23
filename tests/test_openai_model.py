import json

from poisontrace.domain import Scenario
from poisontrace.openai_model import DECISION_SCHEMA, OpenAIModel


class FakeResponses:
    def __init__(self):
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return type("Response", (), {
            "output_text": json.dumps({
                "tool_name": "get_authentication_alert",
                "arguments": {"scenario_id": "authentication-alert-001"},
                "recommendation": "escalate",
            })
        })()


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_openai_model_parses_structured_decision_without_network_call():
    client = FakeClient()
    model = OpenAIModel(client=client, model_name="gpt-5-mini")

    decision = model.respond(Scenario.authentication_alert(), Scenario.authentication_alert().tools)

    assert decision.tool_call.name == "get_authentication_alert"
    assert decision.tool_call.arguments["scenario_id"] == "authentication-alert-001"
    assert decision.recommendation == "escalate"
    assert client.responses.request["model"] == "gpt-5-mini"
    assert client.responses.request["text"]["format"]["type"] == "json_schema"


def test_decision_schema_declares_closed_tool_arguments():
    arguments = DECISION_SCHEMA["properties"]["arguments"]

    assert arguments == {
        "type": "object",
        "additionalProperties": False,
        "properties": {"scenario_id": {"type": "string"}},
        "required": ["scenario_id"],
    }
