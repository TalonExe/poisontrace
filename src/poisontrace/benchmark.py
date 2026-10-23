from collections.abc import Callable

from poisontrace.domain import ExperimentMode, ExperimentResult, Scenario
from poisontrace.runner import ScenarioRunner


class BenchmarkRunner:
    def __init__(self, scenario_runner_factory: Callable[[], ScenarioRunner]) -> None:
        self.scenario_runner_factory = scenario_runner_factory

    def run(
        self,
        scenario: Scenario,
        mode: ExperimentMode,
        repeated_runs: int = 0,
    ) -> list[ExperimentResult]:
        if repeated_runs < 0:
            raise ValueError("repeated_runs must not be negative")
        return [
            self.scenario_runner_factory().run(scenario, mode)
            for _ in range(repeated_runs + 1)
        ]
