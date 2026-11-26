"""Matched-group persistence. Claims and attempt slots are atomic; execution stays request-bound."""
import json
import sqlite3
from uuid import uuid4

from poisontrace.adapters.persistence.support import initialize_database
from poisontrace.application.principals import analyst_owner_id


class SqliteRunGroupStore:
    def __init__(self, database):
        self.database = database
        initialize_database(database)
        with sqlite3.connect(database) as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS run_groups (
                    group_id TEXT PRIMARY KEY, plan TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ready',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS run_group_attempts (
                    group_id TEXT NOT NULL, attempt INTEGER NOT NULL, repeat INTEGER NOT NULL,
                    condition TEXT NOT NULL, run_id INTEGER,
                    PRIMARY KEY (group_id, attempt));
            ''')
            if 'owner_id' not in {row[1] for row in c.execute('PRAGMA table_info(run_groups)')}:
                c.execute('ALTER TABLE run_groups ADD COLUMN owner_id INTEGER')
            for name, definition in (('job_id', 'TEXT'), ('execution_status', 'TEXT')):
                if name not in {row[1] for row in c.execute('PRAGMA table_info(run_group_attempts)')}:
                    c.execute(f'ALTER TABLE run_group_attempts ADD COLUMN {name} {definition}')
            c.execute('CREATE INDEX IF NOT EXISTS run_groups_owner_id ON run_groups(owner_id)')

    def owner_for(self, identifier):
        with sqlite3.connect(self.database) as c:
            row = c.execute('SELECT owner_id FROM run_groups WHERE group_id=?', (identifier,)).fetchone()
        return row[0] if row else None

    def ids_for(self, owner_id):
        with sqlite3.connect(self.database) as c:
            return [r[0] for r in c.execute('SELECT group_id FROM run_groups WHERE owner_id=? ORDER BY rowid DESC', (owner_id,))]

    def create(self, plan):
        identifier = uuid4().hex
        with sqlite3.connect(self.database) as c:
            c.execute('INSERT INTO run_groups (group_id,plan,owner_id) VALUES (?,?,?)', (identifier,json.dumps(plan),analyst_owner_id()))
        return identifier

    def get(self, identifier):
        with sqlite3.connect(self.database) as c:
            row = c.execute('SELECT plan,status,created_at FROM run_groups WHERE group_id=?',(identifier,)).fetchone()
            if row is None:
                raise KeyError(identifier)
            attempts = c.execute('SELECT attempt,repeat,condition,run_id,job_id,execution_status FROM run_group_attempts WHERE group_id=? ORDER BY attempt',(identifier,)).fetchall()
        return dict(group_id=identifier, plan=json.loads(row[0]), status=row[1], created_at=row[2],
                    attempts=[dict(zip(('attempt','repeat','condition','run_id','job_id','execution_status'),a)) for a in attempts])

    def list(self):
        with sqlite3.connect(self.database) as c:
            identifiers = [r[0] for r in c.execute('SELECT group_id FROM run_groups ORDER BY rowid DESC')]
        return [self.get(identifier) for identifier in identifiers]
