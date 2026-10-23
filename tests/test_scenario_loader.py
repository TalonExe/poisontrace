from pathlib import Path

from poisontrace.domain import Scenario
from poisontrace.scenario_loader import load_scenario


def test_loader_reads_versioned_authentication_scenario():
    scenario = load_scenario(Path("scenarios/authentication-alert.yaml"))

    assert isinstance(scenario, Scenario)
    assert scenario.scenario_id == "authentication-alert-001"
    assert scenario.expected_recommendation == "escalate"
    assert scenario.tools[0].name == "get_authentication_alert"
    assert scenario.approved_tools == scenario.tools
