"""Durable shared-schema contracts for persistence adapters."""
import sqlite3

import pytest

from poisontrace.adapters.persistence.campaigns import SqliteCampaignStore
from poisontrace.adapters.persistence.traces import SqliteTraceStore
from poisontrace.application.ports import TraceEvent
from poisontrace.domain import ExperimentMode, ExperimentResult




@pytest.mark.parametrize("first", [SqliteTraceStore, SqliteCampaignStore])
def test_shared_schema_reopens_existing_data_and_child_associations(tmp_path, first):
    database = tmp_path / "shared.db"
    first(database)
    traces = SqliteTraceStore(database)
    campaigns = SqliteCampaignStore(database)
    result = ExperimentResult("001", ExperimentMode.CLEAN, "escalate", True, False)
    traces.record(TraceEvent("first", {"ordinal": "1"}, "run-a"))
    traces.record(TraceEvent("second", {"ordinal": "2"}, "run-a"))
    run_id = traces.save_result(result, "run-a")
    cid = campaigns.create(provider="fake", model="fake", credential_id=None,
                           scenarios=[("b-poisoned.yaml", "002"), ("a-poisoned.yaml", "001")])
    campaigns.associate_child_run(cid, 1, child_run_id=run_id)
    campaigns.associate_child_run(cid, 0, error="ValueError")
    campaigns.set_status(cid, "completed_with_errors")
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO users (username,display_name,role,status,passcode_hash) VALUES ('synthetic','Synthetic','analyst','active','hash')")
        connection.execute("INSERT INTO auth_sessions (token_hash,user_id) VALUES ('synthetic-token',1)")
    reopened = SqliteCampaignStore(database).get(cid)
    assert reopened["scenario_filenames"] == ["b-poisoned.yaml", "a-poisoned.yaml"]
    assert reopened["scenarios"][0]["error"] == "ValueError"
    assert reopened["scenarios"][1]["child_run_id"] == run_id
    assert reopened["status"] == "completed_with_errors"
    assert SqliteTraceStore(database).result_for(run_id) == result
    assert [event.kind for event in traces.events_for(run_id)] == ["first", "second"]
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT token_hash FROM auth_sessions").fetchall() == [("synthetic-token",)]
    with pytest.raises(KeyError):
        campaigns.get("missing")
    with pytest.raises(KeyError):
        traces.result_for(run_id + 1)
    with pytest.raises(ValueError, match="run_key is required"):
        traces.save_result(result)
