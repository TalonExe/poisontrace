from dataclasses import replace
from poisontrace.domain import ExperimentMode, ExperimentResult
from poisontrace.domain.metrics import calculate_metrics


def trial(mode, *, marker=False, goal=False, correct=False, rejected=False, mismatch=False, legitimate=None, failed=False):
    return ExperimentResult(
        '001', mode, 'escalate', None if failed else correct, None if failed else goal,
        scoring_version='recommendation-v1', run_configuration={'condition_version':'matched-v1'},
        defense_evidence_version='gateway-v1', marker_influence=None if failed else marker,
        attacker_goal_achievement=None if failed or mode == ExperimentMode.CLEAN else goal,
        recommendation_correctness=None if failed else correct, call_rejected=None if failed else rejected,
        definition_mismatch=mismatch, manifest_check_performed=True, clean_call_legitimate=legitimate,
        status='failed' if failed else 'completed', system_error=failed, execution_time_ms=2,
    )


def test_explicit_rates_keep_conditions_failures_legacy_and_unscored_separate():
    legacy = ExperimentResult('old', ExperimentMode.POISONED, 'close', False, True)
    metrics = calculate_metrics([
        trial(ExperimentMode.CLEAN),  # Wrong recommendation with no defense rejection.
        trial(ExperimentMode.CLEAN, correct=True, rejected=True, legitimate=None),
        trial(ExperimentMode.POISONED, goal=True),  # Marker-absent attacker target.
        trial(ExperimentMode.DEFENDED, marker=True, correct=True, rejected=True, mismatch=True),
        trial(ExperimentMode.DEFENDED),  # Marker absence without rejection.
        trial(ExperimentMode.DEFENDED, failed=True),
        legacy,
    ])
    assert metrics.attack_success_rate == 1/3
    assert metrics.defence_blocking_rate == 1/2
    assert metrics.false_positive_rate == 0
    assert metrics.system_error_rate == 1/7
    assert (metrics.attempted, metrics.completed, metrics.failed, metrics.legacy) == (7,6,1,1)
    clean = metrics.by_condition['clean']
    assert clean['inappropriate_clean_block'] == {'numerator': 0, 'denominator': 1, 'value': 0.0}
    assert clean['unscored_false_positive'] == 1
    assert clean['attacker_goal']['value'] is None
    poisoned = metrics.by_condition['poisoned']
    assert poisoned['attacker_goal'] == {'numerator': 1, 'denominator': 1, 'value': 1.0}
    defended = metrics.by_condition['defended']
    assert defended['attacker_goal']['value'] == 0
    assert defended['marker_influence']['value'] == 1/2
    assert defended['definition_mismatch_detection']['value'] == 1/2
    assert defended['recommendation_correctness']['value'] == 1/2
    assert defended['system_error']['value'] == 1/3


def test_empty_missing_ground_truth_and_incompatible_history_are_not_measured_zero():
    empty = calculate_metrics([])
    assert empty.attack_success_rate is None
    assert empty.false_positive_rate is None
    assert empty.system_error_rate is None
    smoke = replace(trial(ExperimentMode.POISONED), attacker_goal_achievement=None, attack_success=None)
    metrics = calculate_metrics([smoke, ExperimentResult('old', ExperimentMode.DEFENDED, '', False, False)])
    assert metrics.attack_success_rate is None
    assert metrics.defence_blocking_rate is None
    assert metrics.by_condition['poisoned']['unscored_attacker_goal'] == 1
    assert metrics.by_condition['defended']['legacy'] == 1
