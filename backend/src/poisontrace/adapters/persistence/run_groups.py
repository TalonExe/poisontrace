"""Matched-group persistence. Claims and attempt slots are atomic; execution stays request-bound."""
import json
import sqlite3
from uuid import uuid4

from poisontrace.adapters.persistence.support import initialize_database


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

    def create(self, plan):
        identifier = uuid4().hex
        with sqlite3.connect(self.database) as c:
            c.execute('INSERT INTO run_groups (group_id,plan) VALUES (?,?)', (identifier,json.dumps(plan)))
        return identifier

    def get(self, identifier):
        with sqlite3.connect(self.database) as c:
            row = c.execute('SELECT plan,status,created_at FROM run_groups WHERE group_id=?',(identifier,)).fetchone()
            if row is None:
                raise KeyError(identifier)
            attempts = c.execute('SELECT attempt,repeat,condition,run_id FROM run_group_attempts WHERE group_id=? ORDER BY attempt',(identifier,)).fetchall()
        return dict(group_id=identifier, plan=json.loads(row[0]), status=row[1], created_at=row[2],
                    attempts=[dict(zip(('attempt','repeat','condition','run_id'),a)) for a in attempts])

    def list(self):
        with sqlite3.connect(self.database) as c:
            identifiers = [r[0] for r in c.execute('SELECT group_id FROM run_groups ORDER BY rowid DESC')]
        return [self.get(identifier) for identifier in identifiers]

    def claim(self, identifier, slots):
        with sqlite3.connect(self.database) as c:
            c.execute('BEGIN IMMEDIATE')
            changed = c.execute("UPDATE run_groups SET status='running' WHERE group_id=? AND status!='running'",(identifier,)).rowcount
            if not changed:
                raise ValueError('group is already running; inspect retained attempts')
            offset = c.execute('SELECT COALESCE(MAX(attempt),0) FROM run_group_attempts WHERE group_id=?',(identifier,)).fetchone()[0]
            attempts = [dict(attempt=offset+i+1,repeat=repeat,condition=condition) for i,(repeat,condition) in enumerate(slots)]
            c.executemany('INSERT INTO run_group_attempts (group_id,attempt,repeat,condition) VALUES (?,?,?,?)',
                          [(identifier,a['attempt'],a['repeat'],a['condition']) for a in attempts])
        return attempts

    def finish_attempt(self, identifier, attempt, run_id):
        with sqlite3.connect(self.database) as c:
            c.execute('UPDATE run_group_attempts SET run_id=? WHERE group_id=? AND attempt=?',(run_id,identifier,attempt))

    def finish(self, identifier):
        with sqlite3.connect(self.database) as c:
            c.execute("UPDATE run_groups SET status='finished' WHERE group_id=?",(identifier,))
