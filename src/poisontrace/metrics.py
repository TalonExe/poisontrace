from dataclasses import dataclass

from poisontrace.domain import ExperimentMode, ExperimentResult


@dataclass(frozen=True)
class Metrics:
    attack_success_rate: float
    benign_task_success_rate: float
    defence_blocking_rate: float
    false_positive_rate: float
    unauthorised_tool_call_rate: float
    system_error_rate: float
    average_execution_time_ms: float


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def calculate_metrics(results: list[ExperimentResult]) -> Metrics:
    poisoned = [result for result in results if result.mode == ExperimentMode.POISONED]
    defended = [result for result in results if result.mode == ExperimentMode.DEFENDED]
    clean = [result for result in results if result.mode == ExperimentMode.CLEAN]
    benign_runs = clean + defended

    return Metrics(
        attack_success_rate=_rate(sum(result.attack_success for result in poisoned), len(poisoned)),
        benign_task_success_rate=_rate(
            sum(result.benign_task_success for result in benign_runs), len(benign_runs)
        ),
        defence_blocking_rate=_rate(
            sum(not result.attack_success for result in defended), len(defended)
        ),
        false_positive_rate=_rate(sum(not result.benign_task_success for result in clean), len(clean)),
        unauthorised_tool_call_rate=_rate(
            sum(result.unauthorised_tool_call for result in results), len(results)
        ),
        system_error_rate=_rate(sum(result.system_error for result in results), len(results)),
        average_execution_time_ms=(
            sum(result.execution_time_ms for result in results) / len(results) if results else 0.0
        ),
    )
