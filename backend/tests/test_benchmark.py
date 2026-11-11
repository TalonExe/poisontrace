from poisontrace.adapters.models.fake import FakeModel
from poisontrace.application.benchmark import BenchmarkRunner
from poisontrace.domain import ExperimentMode, Scenario
from poisontrace.application.gateway import ToolGateway
from poisontrace.application.execution import ScenarioRunner
from poisontrace.adapters.persistence.traces import InMemoryTraceStore


def test_benchmark_runs_one_deterministic_and_three_repeated_trials():
    scenario = Scenario.authentication_alert()
    store = InMemoryTraceStore()
    runner = BenchmarkRunner(
        scenario_runner_factory=lambda: ScenarioRunner(
            model=FakeModel(),
            trace_store=store,
            gateway=ToolGateway(scenario.tools, set()),
        )
    )

    results = runner.run(scenario, ExperimentMode.CLEAN, repeated_runs=3)

    assert len(results) == 4
    assert [result.mode for result in results] == [ExperimentMode.CLEAN] * 4
    assert all(result.benign_task_success for result in results)
