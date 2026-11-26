from dataclasses import asdict, replace
import json
import sqlite3
from pathlib import Path

from poisontrace.domain import ExperimentMode, ExperimentResult
from poisontrace.application.ports import TraceEvent
from poisontrace.application.principals import analyst_owner_id
from poisontrace.adapters.persistence.support import initialize_database


class InMemoryTraceStore:
    def __init__(self) -> None: self.events, self.results = [], []
    def record(self, event: TraceEvent) -> None: self.events.append(event)
    def save_result(self, result: ExperimentResult, run_key: str | None = None) -> int:
        run_id = len(self.results) + 1
        self.results.append(replace(result, run_id=run_id))
        return run_id


class SqliteTraceStore:
    def __init__(self, database: Path) -> None: self.database = database; initialize_database(database)
    def record(self, event: TraceEvent) -> None:
        with sqlite3.connect(self.database) as c: c.execute("INSERT INTO events (kind,data,run_key,created_at) VALUES (?,?,?,unixepoch('now'))", (event.kind, json.dumps(event.data), event.run_key))
    def save_result(self, result: ExperimentResult, run_key: str | None = None) -> int:
        if run_key is None: raise ValueError("run_key is required when saving a SQLite trace result")
        with sqlite3.connect(self.database) as c:
            cursor = c.execute("INSERT INTO runs (scenario_id,mode,recommendation,benign_task_success,attack_success,execution_time_ms,system_error,unauthorised_tool_call,model_name,prompt_version,run_configuration,injection_verdict,task_outcome,tool_call_status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,unixepoch('now'))", (result.scenario_id,result.mode.value,result.recommendation,bool(result.benign_task_success),bool(result.attack_success),result.execution_time_ms,result.system_error,result.unauthorised_tool_call,result.model_name,result.prompt_version,json.dumps(result.run_configuration or {}),result.injection_verdict,result.task_outcome,result.tool_call_status))
            run_id = cursor.lastrowid
            c.execute("UPDATE runs SET owner_id=? WHERE id=?", (analyst_owner_id(), run_id))
            evidence = {key: value for key, value in asdict(result).items() if key in {
                "scoring_version", "marker_influence", "attacker_goal_achievement", "recommendation_correctness",
                "expected_recommendation", "attacker_target_recommendation",
                "defense_evidence_version", "manifest_check_performed", "definition_mismatch", "call_rejected",
                "policy_reason", "proposed_tool_name", "clean_call_legitimate", "gateway_simulated", "status", "error_category", "investigation"
            }}
            c.execute("UPDATE runs SET outcome_evidence=? WHERE id=?", (json.dumps(evidence), run_id))
            c.execute("UPDATE events SET run_id=? WHERE run_id IS NULL AND run_key=?", (run_id, run_key))
            job_id = (result.run_configuration or {}).get('job_id')
            if job_id:
                import time
                claim = c.execute("SELECT group_id,campaign_id FROM execution_jobs WHERE job_id=? AND claim=? AND owner_id=? AND status='active' AND lease_until>?", (job_id, result.run_configuration.get('job_claim'), analyst_owner_id(), time.time())).fetchone()
                if claim is None:
                    raise RuntimeError('execution claim is no longer valid')
                if claim[0]:
                    updated = c.execute("UPDATE run_group_attempts SET run_id=?,execution_status=? WHERE group_id=? AND job_id=? AND attempt=? AND execution_status='active' AND run_id IS NULL AND EXISTS(SELECT 1 FROM run_groups WHERE group_id=? AND owner_id=?)", (run_id, result.status, claim[0], job_id, result.run_configuration.get('group_attempt'), claim[0], analyst_owner_id()))
                    if updated.rowcount != 1:
                        raise RuntimeError('group attempt is no longer valid')
                    pending = c.execute('SELECT 1 FROM run_group_attempts WHERE job_id=? AND run_id IS NULL', (job_id,)).fetchone()
                    if pending is None:
                        c.execute("UPDATE run_groups SET status='finished' WHERE group_id=?", (claim[0],))
                        c.execute("UPDATE execution_jobs SET status='completed',finished_at=?,lease_until=NULL WHERE job_id=?", (time.time(), job_id))
                elif claim[1]:
                    self.link_campaign_attempt(c, job_id, claim[1], run_id, result, time.time())
                else:
                    c.execute("UPDATE execution_jobs SET status=?,run_id=?,error_category=?,finished_at=?,lease_until=NULL WHERE job_id=?", (result.status, run_id, result.error_category, time.time(), job_id))
            return run_id

    @staticmethod
    def link_campaign_attempt(connection, job_id, campaign_id, run_id, result, finished_at):
        ordinal = result.run_configuration['campaign_ordinal']
        if result.run_configuration['campaign_id'] != campaign_id:
            raise RuntimeError('campaign does not match execution claim')
        updated = connection.execute("UPDATE campaign_job_attempts SET status=?,run_id=? WHERE job_id=? AND ordinal=? AND status='active' AND run_id IS NULL",
                                     (result.status, run_id, job_id, ordinal))
        if updated.rowcount != 1:
            raise RuntimeError('campaign attempt is no longer valid')
        updated = connection.execute("UPDATE campaign_scenarios SET child_run_id=?,error=? WHERE campaign_id=? AND ordinal=? AND EXISTS(SELECT 1 FROM campaigns WHERE campaign_id=? AND owner_id=?)",
                                     (run_id, result.error_category, campaign_id, ordinal, campaign_id, analyst_owner_id()))
        if updated.rowcount != 1:
            raise RuntimeError('campaign association is no longer valid')
        pending = connection.execute("SELECT 1 FROM campaign_job_attempts WHERE job_id=? AND status='queued'", (job_id,)).fetchone()
        if pending:
            return
        rerun = connection.execute("SELECT json_extract(snapshot,'$.ordinal') FROM execution_jobs WHERE job_id=?", (job_id,)).fetchone()[0] is not None
        if rerun:
            status, job_run_id, error = result.status, run_id, result.error_category
        else:
            errors = connection.execute("SELECT 1 FROM campaign_scenarios WHERE campaign_id=? AND error IS NOT NULL", (campaign_id,)).fetchone()
            connection.execute("UPDATE campaigns SET status=? WHERE campaign_id=?", ('completed_with_errors' if errors else 'completed', campaign_id))
            status, job_run_id, error = 'completed', None, None
        connection.execute("UPDATE execution_jobs SET status=?,run_id=?,error_category=?,finished_at=?,lease_until=NULL WHERE job_id=?",
                           (status, job_run_id, error, finished_at, job_id))
    def events_for(self, run_id: int) -> list[TraceEvent]:
        with sqlite3.connect(self.database) as c: rows = c.execute("SELECT kind,data FROM events WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        return [TraceEvent(kind, json.loads(data)) for kind, data in rows]
    def result_for(self, run_id: int) -> ExperimentResult:
        with sqlite3.connect(self.database) as c: row = c.execute("SELECT scenario_id,mode,recommendation,benign_task_success,attack_success,execution_time_ms,system_error,unauthorised_tool_call,model_name,prompt_version,run_configuration,injection_verdict,task_outcome,tool_call_status,outcome_evidence FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None: raise KeyError(run_id)
        result = ExperimentResult(row[0], ExperimentMode(row[1]), row[2], bool(row[3]), bool(row[4]), row[5], bool(row[6]), bool(row[7]), row[8], row[9], json.loads(row[10]), row[11], row[12], row[13])
        evidence = json.loads(row[14])
        if evidence.get("scoring_version", "legacy") != "legacy":
            result = replace(result, **evidence, attack_success=evidence.get("attacker_goal_achievement"), benign_task_success=evidence.get("recommendation_correctness"))
        return replace(result, run_id=run_id)
    def latest_result(self) -> ExperimentResult: return self.result_for(self.latest_run_id())
    def run_ids(self) -> list[int]:
        with sqlite3.connect(self.database) as c: return [row[0] for row in c.execute("SELECT id FROM runs ORDER BY id DESC")]
    def run_ids_for(self, owner_id: int) -> list[int]:
        with sqlite3.connect(self.database) as c:
            return [row[0] for row in c.execute("SELECT id FROM runs WHERE owner_id=? ORDER BY id DESC", (owner_id,))]
    def owner_for(self, run_id: int) -> int | None:
        with sqlite3.connect(self.database) as c:
            row = c.execute("SELECT owner_id FROM runs WHERE id=?", (run_id,)).fetchone()
        return row[0] if row else None

    def activity_for(self, owner_id: int, start: int, end: int) -> dict:
        params = {"owner": owner_id, "start": start, "end": end}
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN")
            attempts = connection.execute("""
                SELECT id AS run_id, created_at AS at,
                       COALESCE(json_extract(run_configuration, '$.provider'), 'unknown') AS provider,
                       COALESCE(json_extract(outcome_evidence, '$.status'), 'completed') AS status
                FROM runs
                WHERE owner_id = :owner AND created_at >= :start AND created_at < :end
                  AND json_extract(run_configuration, '$.workflow') = 'mcp-investigation-v1'
            """, params).fetchall()
            groups = connection.execute("""
                SELECT group_id, unixepoch(created_at) AS at
                FROM run_groups
                WHERE owner_id = :owner
                  AND unixepoch(created_at) >= :start AND unixepoch(created_at) < :end
            """, params).fetchall()
            reruns = connection.execute("""
                SELECT job_id, group_id, created_at AS at
                FROM execution_jobs
                WHERE owner_id = :owner AND created_at >= :start AND created_at < :end
                  AND group_id IS NOT NULL AND json_extract(snapshot, '$.attempts[0].attempt') > 1
            """, params).fetchall()
            interrupted = connection.execute("""
                SELECT COUNT(*)
                FROM execution_jobs
                WHERE owner_id = :owner AND status = 'interrupted'
                  AND finished_at >= :start AND finished_at < :end
                  AND (group_id IS NOT NULL OR json_type(snapshot, '$.case') = 'object')
            """, params).fetchone()[0]
        return {
            "attempts": [dict(row) for row in attempts],
            "groups": [dict(row) for row in groups],
            "reruns": [dict(row) for row in reruns],
            "interrupted": interrupted,
        }
    def latest_run_id(self) -> int:
        with sqlite3.connect(self.database) as c: row = c.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        if row is None: raise KeyError("no runs")
        return row[0]
    def latest_events(self) -> list[TraceEvent]: return self.events_for(self.latest_run_id())
