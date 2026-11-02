from dataclasses import dataclass
import json
import sqlite3
from pathlib import Path
from typing import Protocol

from poisontrace.domain import ExperimentMode, ExperimentResult
from poisontrace.persistence.support import initialize_database


@dataclass(frozen=True)
class TraceEvent:
    kind: str
    data: dict[str, str]
    run_key: str | None = None


class TraceStore(Protocol):
    def record(self, event: TraceEvent) -> None: ...
    def save_result(self, result: ExperimentResult, run_key: str | None = None) -> int: ...


class InMemoryTraceStore:
    def __init__(self) -> None: self.events, self.results = [], []
    def record(self, event: TraceEvent) -> None: self.events.append(event)
    def save_result(self, result: ExperimentResult, run_key: str | None = None) -> int: self.results.append(result); return len(self.results)


class SqliteTraceStore:
    def __init__(self, database: Path) -> None: self.database = database; initialize_database(database)
    def record(self, event: TraceEvent) -> None:
        with sqlite3.connect(self.database) as c: c.execute("INSERT INTO events (kind,data,run_key) VALUES (?,?,?)", (event.kind, json.dumps(event.data), event.run_key))
    def save_result(self, result: ExperimentResult, run_key: str | None = None) -> int:
        if run_key is None: raise ValueError("run_key is required when saving a SQLite trace result")
        with sqlite3.connect(self.database) as c:
            cursor = c.execute("INSERT INTO runs (scenario_id,mode,recommendation,benign_task_success,attack_success,execution_time_ms,system_error,unauthorised_tool_call,model_name,prompt_version,run_configuration,injection_verdict,task_outcome,tool_call_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (result.scenario_id,result.mode.value,result.recommendation,result.benign_task_success,result.attack_success,result.execution_time_ms,result.system_error,result.unauthorised_tool_call,result.model_name,result.prompt_version,json.dumps(result.run_configuration or {}),result.injection_verdict,result.task_outcome,result.tool_call_status))
            run_id = cursor.lastrowid; c.execute("UPDATE events SET run_id=? WHERE run_id IS NULL AND run_key=?", (run_id, run_key)); return run_id
    def events_for(self, run_id: int) -> list[TraceEvent]:
        with sqlite3.connect(self.database) as c: rows = c.execute("SELECT kind,data FROM events WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        return [TraceEvent(kind, json.loads(data)) for kind, data in rows]
    def result_for(self, run_id: int) -> ExperimentResult:
        with sqlite3.connect(self.database) as c: row = c.execute("SELECT scenario_id,mode,recommendation,benign_task_success,attack_success,execution_time_ms,system_error,unauthorised_tool_call,model_name,prompt_version,run_configuration,injection_verdict,task_outcome,tool_call_status FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None: raise KeyError(run_id)
        return ExperimentResult(row[0], ExperimentMode(row[1]), row[2], bool(row[3]), bool(row[4]), row[5], bool(row[6]), bool(row[7]), row[8], row[9], json.loads(row[10]), row[11], row[12], row[13])
    def latest_result(self) -> ExperimentResult: return self.result_for(self.latest_run_id())
    def run_ids(self) -> list[int]:
        with sqlite3.connect(self.database) as c: return [row[0] for row in c.execute("SELECT id FROM runs ORDER BY id DESC")]
    def latest_run_id(self) -> int:
        with sqlite3.connect(self.database) as c: row = c.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        if row is None: raise KeyError("no runs")
        return row[0]
    def latest_events(self) -> list[TraceEvent]: return self.events_for(self.latest_run_id())
