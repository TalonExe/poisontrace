import pytest
from poisontrace.bootstrap import build_backend, create_app
from poisontrace.config import WebConfig
from poisontrace.domain import AgentDecision, ExperimentMode, ExperimentResult, Scenario
from poisontrace.application.execution import ScenarioRunner
from poisontrace.application.gateway import ToolGateway


def test_summary_api_aggregates_persisted_outcomes_and_retains_history(tmp_path, analyst_client):
    backend = build_backend(WebConfig(scenario_dir=tmp_path / 'scenarios', database=tmp_path / 'runs.db'))
    scenario = Scenario.authentication_alert()
    class Wrong:
        def respond(self, scenario, tools): return AgentDecision(None, 'close', 'normal')
    class Failed:
        def respond(self, scenario, tools): raise RuntimeError('safe synthetic failure')
    for model in [Wrong(), Failed()]:
        ScenarioRunner(model, backend.store, ToolGateway(scenario.approved_tools, set())).run(scenario, ExperimentMode.CLEAN)
    old_id = backend.store.save_result(ExperimentResult('old', ExperimentMode.DEFENDED, 'close', False, True), 'old')
    client = analyst_client(create_app(backend))
    response = client.get('/api/runs/summary')
    assert response.status_code == 200
    metrics = response.json()
    assert (metrics['attempted'], metrics['completed'], metrics['failed'], metrics['legacy']) == (3,2,1,1)
    assert metrics['system_error_rate'] == 1/3
    assert metrics['false_positive_rate'] == 0
    assert metrics['defence_blocking_rate'] is None
    assert metrics['by_condition']['clean']['recommendation_correctness'] == {'numerator':0,'denominator':1,'value':0.0}
    assert client.get(f'/api/runs/{old_id}').json()['scoring_version'] == 'legacy'

def test_false_positive_uses_incident_trust_independently_of_gateway_manifest(tmp_path):
    from poisontrace.adapters.models.fake import FakeModel
    from poisontrace.domain.metrics import calculate_metrics
    scenario = Scenario.authentication_alert()
    backend = build_backend(WebConfig(scenario_dir=tmp_path / 'scenarios', database=tmp_path / 'runs.db'))
    result = ScenarioRunner(FakeModel(), backend.store, ToolGateway((), set())).run(scenario, ExperimentMode.CLEAN)
    assert result.call_rejected is True
    assert result.clean_call_legitimate is True
    metrics = calculate_metrics([result])
    assert metrics.false_positive_rate == 1
    assert metrics.by_condition['clean']['inappropriate_clean_block']['denominator'] == 1


# Trusted caller for direct application checks; HTTP still authenticates independently.
pytestmark = pytest.mark.usefixtures("application_analyst")
