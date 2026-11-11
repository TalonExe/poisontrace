import json

import pytest

from poisontrace.domain import Scenario
from poisontrace.adapters.models.gemini import DECISION_SCHEMA, GeminiModel


class FakeModels:
    def __init__(self, text):
        self.text = text
        self.request = None

    def generate_content(self, **kwargs):
        self.request = kwargs
        return type("Response", (), {"text": self.text})()


class FakeClient:
    def __init__(self, text):
        self.models = FakeModels(text)


def test_gemini_model_returns_structured_decision_and_forwards_model_name():
    client = FakeClient(json.dumps({
        "tool_name": "get_authentication_alert",
        "arguments": {"scenario_id": "authentication-alert-001"},
        "recommendation": "escalate",
    }))
    model = GeminiModel(client=client, model_name="gemini-test")

    decision = model.respond(Scenario.authentication_alert(), Scenario.authentication_alert().tools)

    assert decision.tool_call.name == "get_authentication_alert"
    assert decision.tool_call.arguments == {"scenario_id": "authentication-alert-001"}
    assert decision.recommendation == "escalate"
    assert client.models.request["model"] == "gemini-test"
    assert client.models.request["config"].response_mime_type == "application/json"
    assert client.models.request["config"].response_schema == DECISION_SCHEMA


def test_gemini_model_forwards_api_key_when_constructing_default_client(monkeypatch):
    from google import genai

    calls = []

    class CapturingClient:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(genai, "Client", CapturingClient)

    GeminiModel(model_name="gemini-test", api_key="gemini-secret")

    assert calls == [{"api_key": "gemini-secret"}]


@pytest.mark.parametrize("text", ["not json", '{"tool_name": ""}'])
def test_gemini_model_rejects_malformed_or_incomplete_responses(text):
    model = GeminiModel(client=FakeClient(text))

    with pytest.raises(ValueError, match="invalid Gemini model response"):
        model.respond(Scenario.authentication_alert(), Scenario.authentication_alert().tools)


def test_gemini_model_does_not_retain_api_keys_or_raw_response():
    secret = "gemini-secret"
    model = GeminiModel(
        client=FakeClient(json.dumps({
            "tool_name": "",
            "arguments": {"scenario_id": "authentication-alert-001"},
            "recommendation": "escalate",
        })),
        api_key=secret,
    )

    decision = model.respond(Scenario.authentication_alert(), Scenario.authentication_alert().tools)

    assert secret not in repr(decision)
    assert not hasattr(model, "raw_response")
