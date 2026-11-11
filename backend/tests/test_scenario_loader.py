from pathlib import Path

from poisontrace.domain import Scenario
from poisontrace.adapters.scenarios.loader import load_scenario


def test_poisoned_fixtures_use_bounded_marker_injection_payloads():
    poisoned = sorted(Path("backend/tests/fixtures/scenarios").glob("*poisoned*.yaml"))
    assert poisoned

    forbidden = ("sk-", "api_key", "recovery code", "security mailbox", "http://", "https://", "@")
    for path in poisoned:
        scenario = load_scenario(path)
        description = " ".join(tool.description for tool in scenario.tools)
        assert "COMPROMISED" in description, path.name
        assert "SOC" in description, path.name
        assert not any(value.lower() in description.lower() for value in forbidden), path.name


def test_loader_reads_versioned_authentication_scenario():
    scenario = load_scenario(Path("backend/tests/fixtures/scenarios/authentication-alert-001.yaml"))

    assert isinstance(scenario, Scenario)
    assert scenario.scenario_id == "001"
    assert scenario.expected_recommendation == "escalate"
    assert scenario.tools[0].name == "get_authentication_alert"
    assert scenario.approved_tools == scenario.tools
