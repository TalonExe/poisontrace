from poisontrace.domain import ExperimentMode, ExperimentResult
from poisontrace.trace import SqliteTraceStore, TraceEvent


def test_sqlite_trace_store_persists_events_and_results(tmp_path):
    database = tmp_path / "runs.db"
    result = ExperimentResult(
        scenario_id="authentication-alert-001",
        mode=ExperimentMode.CLEAN,
        recommendation="escalate",
        benign_task_success=True,
        attack_success=False,
    )
    store = SqliteTraceStore(database)
    store.record(TraceEvent("recommendation_created", {"value": "escalate"}))
    run_id = store.save_result(result)

    reopened = SqliteTraceStore(database)

    assert reopened.events_for(run_id)[0].kind == "recommendation_created"
    assert reopened.result_for(run_id) == result
