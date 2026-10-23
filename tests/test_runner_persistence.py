from poisontrace.agent import FakeModel
from poisontrace.domain import ExperimentMode, Scenario
from poisontrace.gateway import ToolGateway
from poisontrace.runner import ScenarioRunner
from poisontrace.trace import SqliteTraceStore


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
    assert len(store.latest_events()) == 5
