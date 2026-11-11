from poisontrace.domain import ExperimentMode, ExperimentResult
from poisontrace.adapters.persistence.traces import SqliteTraceStore, TraceEvent


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
    store.record(TraceEvent("recommendation_created", {"value": "escalate"}, run_key="run-a"))
    run_id = store.save_result(result, run_key="run-a")

    reopened = SqliteTraceStore(database)

    assert reopened.events_for(run_id)[0].kind == "recommendation_created"
    assert reopened.result_for(run_id) == result


def test_sqlite_trace_store_keeps_interleaved_run_events_separate(tmp_path):
    database = tmp_path / "runs.db"
    first = ExperimentResult("scenario-a", ExperimentMode.CLEAN, "first", True, False)
    second = ExperimentResult("scenario-b", ExperimentMode.POISONED, "second", False, True)
    store = SqliteTraceStore(database)

    store.record(TraceEvent("tool_called", {"name": "first-tool"}, run_key="run-a"))
    store.record(TraceEvent("tool_called", {"name": "second-tool"}, run_key="run-b"))
    first_id = store.save_result(first, run_key="run-a")
    second_id = store.save_result(second, run_key="run-b")

    assert [event.data["name"] for event in store.events_for(first_id)] == ["first-tool"]
    assert [event.data["name"] for event in store.events_for(second_id)] == ["second-tool"]
