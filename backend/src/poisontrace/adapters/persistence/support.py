import sqlite3
from pathlib import Path


def initialize_database(database: Path) -> None:
    """Create the shared schema and apply only additive migrations."""
    with sqlite3.connect(database) as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, scenario_id TEXT NOT NULL, mode TEXT NOT NULL, recommendation TEXT NOT NULL, benign_task_success INTEGER NOT NULL, attack_success INTEGER NOT NULL, execution_time_ms REAL NOT NULL, system_error INTEGER NOT NULL, unauthorised_tool_call INTEGER NOT NULL, model_name TEXT NOT NULL DEFAULT 'unknown', prompt_version TEXT NOT NULL DEFAULT 'unknown', run_configuration TEXT NOT NULL DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, kind TEXT NOT NULL, data TEXT NOT NULL, run_key TEXT);
        CREATE TABLE IF NOT EXISTS campaigns (campaign_id TEXT PRIMARY KEY, status TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL, credential_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS campaign_scenarios (campaign_id TEXT NOT NULL, ordinal INTEGER NOT NULL, filename TEXT NOT NULL, scenario_id TEXT NOT NULL, child_run_id INTEGER, error TEXT, PRIMARY KEY (campaign_id, ordinal), FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id));
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL, passcode_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, last_login_at TEXT);
        CREATE TABLE IF NOT EXISTS auth_sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(id));
        """)
        if "expires_at" not in {row[1] for row in connection.execute("PRAGMA table_info(auth_sessions)")}:
            connection.execute("ALTER TABLE auth_sessions ADD COLUMN expires_at REAL")
        connection.execute("CREATE TABLE IF NOT EXISTS login_limits (key_hash TEXT PRIMARY KEY, attempts INTEGER NOT NULL, expires_at REAL NOT NULL)")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(runs)")}
        for name, definition in (("model_name", "TEXT NOT NULL DEFAULT 'unknown'"), ("prompt_version", "TEXT NOT NULL DEFAULT 'unknown'"), ("run_configuration", "TEXT NOT NULL DEFAULT '{}'"), ("injection_verdict", "TEXT NOT NULL DEFAULT 'Blocked'"), ("task_outcome", "TEXT NOT NULL DEFAULT 'Failed'"), ("tool_call_status", "TEXT NOT NULL DEFAULT 'Not requested'")):
            if name not in columns: connection.execute(f"ALTER TABLE runs ADD COLUMN {name} {definition}")
        if "created_at" not in columns:
            connection.execute("ALTER TABLE runs ADD COLUMN created_at REAL")
        if "created_at" not in {row[1] for row in connection.execute("PRAGMA table_info(events)")}:
            connection.execute("ALTER TABLE events ADD COLUMN created_at REAL")
        if "outcome_evidence" not in columns:
            connection.execute("ALTER TABLE runs ADD COLUMN outcome_evidence TEXT NOT NULL DEFAULT '{}'")
        if "owner_id" not in columns:
            connection.execute("ALTER TABLE runs ADD COLUMN owner_id INTEGER")
        connection.execute("CREATE INDEX IF NOT EXISTS runs_owner_id ON runs(owner_id, id)")
        if "owner_id" not in {row[1] for row in connection.execute("PRAGMA table_info(campaigns)")}:
            connection.execute("ALTER TABLE campaigns ADD COLUMN owner_id INTEGER")
        connection.execute("CREATE INDEX IF NOT EXISTS campaigns_owner_id ON campaigns(owner_id)")
        if "run_key" not in {row[1] for row in connection.execute("PRAGMA table_info(events)")}: connection.execute("ALTER TABLE events ADD COLUMN run_key TEXT")
        if "error" not in {row[1] for row in connection.execute("PRAGMA table_info(campaign_scenarios)")}: connection.execute("ALTER TABLE campaign_scenarios ADD COLUMN error TEXT")
