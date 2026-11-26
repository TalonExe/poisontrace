import sqlite3
from contextlib import closing


HISTORY = {
    "run": ("runs", "id", "created_at", "1"),
    "event": ("events", "id", "created_at", "run_id IS NULL"),
    "job": ("execution_jobs", "job_id", "CASE WHEN status IN ('queued','active') THEN NULL ELSE coalesce(finished_at,created_at) END", "1"),
    "group": ("run_groups", "group_id", "unixepoch(created_at)", "1"),
    "campaign": ("campaigns", "campaign_id", "unixepoch(created_at)", "1"),
}
LINKS = (
    ("job", "job_id", "group", "group_id", "execution_jobs"),
    ("job", "job_id", "campaign", "campaign_id", "execution_jobs"),
    ("job", "job_id", "run", "run_id", "execution_jobs"),
    ("group", "group_id", "run", "run_id", "run_group_attempts"),
    ("campaign", "campaign_id", "run", "child_run_id", "campaign_scenarios"),
    ("job", "job_id", "run", "run_id", "campaign_job_attempts"),
)
DEPENDENTS = (
    ("events", "run_id", "run"),
    ("campaign_job_attempts", "job_id", "job"),
    ("run_group_attempts", "group_id", "group"),
    ("campaign_scenarios", "campaign_id", "campaign"),
)


def retention_candidates(connection, cutoff):
    connection.execute("CREATE TEMP TABLE retained_nodes (node TEXT PRIMARY KEY, keep INTEGER NOT NULL)")
    connection.execute("CREATE TEMP TABLE history_edges (source TEXT, destination TEXT, PRIMARY KEY(source,destination))")
    for kind, (table, key, timestamp, include) in HISTORY.items():
        connection.execute(f"""
            INSERT INTO retained_nodes
            SELECT ? || ':' || {key}, CASE WHEN ({timestamp}) <= ? THEN 0 ELSE 1 END
            FROM {table} WHERE {include}
        """, (kind, cutoff))
    for left, left_key, right, right_key, table in LINKS:
        for source, source_key, target, target_key in ((left, left_key, right, right_key), (right, right_key, left, left_key)):
            connection.execute(f"""
                INSERT OR IGNORE INTO history_edges
                SELECT ? || ':' || {source_key}, ? || ':' || {target_key}
                FROM {table} WHERE {source_key} IS NOT NULL AND {target_key} IS NOT NULL
            """, (source, target))
    connection.execute("""
        WITH campaign_runs(run_node, campaign_node) AS (
            SELECT 'run:' || runs.id, 'campaign:' || campaigns.campaign_id
            FROM runs JOIN campaigns ON runs.owner_id=campaigns.owner_id
                AND campaigns.campaign_id=CASE WHEN json_valid(runs.run_configuration)
                    THEN json_extract(runs.run_configuration,'$.campaign_id') END
        )
        INSERT OR IGNORE INTO history_edges
        SELECT run_node,campaign_node FROM campaign_runs
        UNION ALL
        SELECT campaign_node,run_node FROM campaign_runs
    """)
    return [tuple(node.split(":", 1)) for (node,) in connection.execute("""
        WITH RECURSIVE retained(node) AS (
            SELECT node FROM retained_nodes WHERE keep
            UNION
            SELECT destination FROM history_edges JOIN retained ON source=retained.node
        )
        SELECT node FROM retained_nodes WHERE node NOT IN (SELECT node FROM retained)
    """)]


def reconcile_history(connection, ledger, cutoff=None):
    with ledger.connect() as journal, journal:
        if cutoff is not None:
            journal.executemany("INSERT OR IGNORE INTO expired VALUES (?,?)", retention_candidates(connection, cutoff))
        expired = journal.execute("SELECT kind,identifier FROM expired").fetchall()
    if not expired:
        return 0
    connection.execute("CREATE TEMP TABLE expired_history (kind TEXT, identifier TEXT, PRIMARY KEY(kind,identifier))")
    connection.executemany("INSERT INTO expired_history VALUES (?,?)", expired)
    removed = 0
    for table, key, kind in DEPENDENTS:
        connection.execute(f"DELETE FROM {table} WHERE {key} IN (SELECT identifier FROM expired_history WHERE kind=?)", (kind,))
    for kind, (table, key, _, _) in HISTORY.items():
        cursor = connection.execute(f"DELETE FROM {table} WHERE {key} IN (SELECT identifier FROM expired_history WHERE kind=?)", (kind,))
        removed += cursor.rowcount
    for table in ("runs", "events"):
        kind = "run" if table == "runs" else "event"
        highest = connection.execute("SELECT max(CAST(identifier AS INTEGER)) FROM expired_history WHERE kind=?", (kind,)).fetchone()[0]
        if highest is not None:
            updated = connection.execute("UPDATE sqlite_sequence SET seq=max(seq,?) WHERE name=?", (highest, table))
            if not updated.rowcount:
                connection.execute("INSERT INTO sqlite_sequence(name,seq) VALUES (?,?)", (table, highest))
    return removed
