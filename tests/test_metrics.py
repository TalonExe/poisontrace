from poisontrace.domain import ExperimentMode, ExperimentResult
from poisontrace.metrics import calculate_metrics


def result(mode, benign_success, attack_success):
    return ExperimentResult(
        scenario_id="scenario-001",
        mode=mode,
        recommendation="escalate",
        benign_task_success=benign_success,
        attack_success=attack_success,
        execution_time_ms=1.0,
        unauthorised_tool_call=attack_success,
    )


def test_metrics_compare_poisoned_and_defended_runs():
    metrics = calculate_metrics(
        [
            result(ExperimentMode.CLEAN, True, False),
            result(ExperimentMode.POISONED, False, True),
            result(ExperimentMode.DEFENDED, True, False),
        ]
    )

    assert metrics.attack_success_rate == 1.0
    assert metrics.benign_task_success_rate == 1.0
    assert metrics.defence_blocking_rate == 1.0
    assert metrics.false_positive_rate == 0.0
    assert metrics.unauthorised_tool_call_rate == 1 / 3
    assert metrics.system_error_rate == 0.0
    assert metrics.average_execution_time_ms > 0
