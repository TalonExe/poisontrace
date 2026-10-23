from dataclasses import dataclass
import json
import sqlite3
from pathlib import Path

from poisontrace.domain import ExperimentMode, ExperimentResult


@dataclass(frozen=True)
class TraceEvent:
    kind: str
    data: dict[str, str]


class InMemoryTraceStore:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []
        self.results: list[ExperimentResult] = []

    def record(self, event: TraceEvent) -> None:
        self.events.append(event)

    def save_result(self, result: ExperimentResult) -> int:
        self.results.append(result)
        return len(self.results)


class SqliteTraceStore:
    def __init__(self, database: Path) -> None:
        self.database = database
        with sqlite3.connect(self.database) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    benign_task_success INTEGER NOT NULL,
                    attack_success INTEGER NOT NULL
                    ,execution_time_ms REAL NOT NULL
                    ,system_error INTEGER NOT NULL
                    ,unauthorised_tool_call INTEGER NOT NULL
                    ,model_name TEXT NOT NULL DEFAULT 'unknown'
                    ,prompt_version TEXT NOT NULL DEFAULT 'unknown'
                    ,run_configuration TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    kind TEXT NOT NULL,
                    data TEXT NOT NULL
                );
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(runs)").fetchall()
            }
            for name, definition in (
                ("model_name", "TEXT NOT NULL DEFAULT 'unknown'"),
                ("prompt_version", "TEXT NOT NULL DEFAULT 'unknown'"),
                ("run_configuration", "TEXT NOT NULL DEFAULT '{}'"),
            ):
                if name not in columns:
                    connection.execute(f"ALTER TABLE runs ADD COLUMN {name} {definition}")

    def record(self, event: TraceEvent) -> None:
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "INSERT INTO events (kind, data) VALUES (?, ?)",
                (event.kind, json.dumps(event.data)),
            )

    def save_result(self, result: ExperimentResult) -> int:
        with sqlite3.connect(self.database) as connection:
            cursor = connection.execute(
                """
                INSERT INTO runs
                    (scenario_id, mode, recommendation, benign_task_success, attack_success,
                    execution_time_ms, system_error, unauthorised_tool_call,
                    model_name, prompt_version, run_configuration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.scenario_id,
                    result.mode.value,
                    result.recommendation,
                    result.benign_task_success,
                    result.attack_success,
                    result.execution_time_ms,
                    result.system_error,
                    result.unauthorised_tool_call,
                    result.model_name,
                    result.prompt_version,
                    json.dumps(result.run_configuration or {}),
                ),
            )
            run_id = cursor.lastrowid
            connection.execute("UPDATE events SET run_id = ? WHERE run_id IS NULL", (run_id,))
            return run_id

    def events_for(self, run_id: int) -> list[TraceEvent]:
        with sqlite3.connect(self.database) as connection:
            rows = connection.execute(
                "SELECT kind, data FROM events WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
        return [TraceEvent(kind, json.loads(data)) for kind, data in rows]

    def result_for(self, run_id: int) -> ExperimentResult:
        with sqlite3.connect(self.database) as connection:
            row = connection.execute(
                """
                SELECT scenario_id, mode, recommendation, benign_task_success, attack_success,
                       execution_time_ms, system_error, unauthorised_tool_call,
                       model_name, prompt_version, run_configuration
                FROM runs WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return ExperimentResult(
            scenario_id=row[0],
            mode=ExperimentMode(row[1]),
            recommendation=row[2],
            benign_task_success=bool(row[3]),
            attack_success=bool(row[4]),
            execution_time_ms=row[5],
            system_error=bool(row[6]),
            unauthorised_tool_call=bool(row[7]),
            model_name=row[8],
            prompt_version=row[9],
            run_configuration=json.loads(row[10]),
        )

    def latest_result(self) -> ExperimentResult:
        with sqlite3.connect(self.database) as connection:
            row = connection.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            raise KeyError("no runs")
        return self.result_for(row[0])

    def latest_events(self) -> list[TraceEvent]:
        with sqlite3.connect(self.database) as connection:
            row = connection.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            raise KeyError("no runs")
        return self.events_for(row[0])
