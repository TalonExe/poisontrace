from poisontrace.adapters.models.fake import FakeModel
from poisontrace.domain import ExperimentMode, Scenario
from poisontrace.application.gateway import ToolGateway
from poisontrace.application.execution import ScenarioRunner
from poisontrace.adapters.persistence.traces import SqliteTraceStore


def test_runner_persists_completed_run_to_sqlite(tmp_path):
    database = tmp_path / "runs.db"
    scenario = Scenario.authentication_alert()
    store = SqliteTraceStore(database)
    runner = ScenarioRunner(
        model=FakeModel(),
        trace_store=store,
        gateway=ToolGateway(scenario.tools, set()),
    )

    result = runner.run(scenario, ExperimentMode.CLEAN)

    persisted = store.latest_result()
    assert persisted == result
    assert [event.kind for event in store.latest_events()] == [
        "tool_discovered",
        "agent_output",
        "tool_called",
        "policy_decision",
        "tool_returned",
        "recommendation_created",
    ]
