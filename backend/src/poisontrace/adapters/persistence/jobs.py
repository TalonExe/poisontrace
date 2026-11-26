from contextlib import contextmanager
import json
import sqlite3
import time
from uuid import uuid4

from poisontrace.application.ports import ExecutionBusy


class SqliteJobStore:
    def __init__(self, database, *, clock=time.time):
        self.database, self.clock = database, clock
        with self.connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS execution_jobs (job_id TEXT PRIMARY KEY, owner_id INTEGER NOT NULL, intent TEXT NOT NULL, fingerprint TEXT NOT NULL, snapshot TEXT NOT NULL, status TEXT NOT NULL, claim TEXT, lease_until REAL, created_at REAL NOT NULL, started_at REAL, finished_at REAL, run_id INTEGER, error_category TEXT, dispatched INTEGER NOT NULL DEFAULT 0, UNIQUE(owner_id,intent))')
            if 'dispatched' not in {row[1] for row in c.execute('PRAGMA table_info(execution_jobs)')}:
                c.execute('ALTER TABLE execution_jobs ADD COLUMN dispatched INTEGER NOT NULL DEFAULT 0')
            if 'group_id' not in {row[1] for row in c.execute('PRAGMA table_info(execution_jobs)')}:
                c.execute('ALTER TABLE execution_jobs ADD COLUMN group_id TEXT')
            if 'campaign_id' not in {row[1] for row in c.execute('PRAGMA table_info(execution_jobs)')}:
                c.execute('ALTER TABLE execution_jobs ADD COLUMN campaign_id TEXT')
            c.execute("CREATE TABLE IF NOT EXISTS campaign_job_attempts (job_id TEXT NOT NULL, ordinal INTEGER NOT NULL, status TEXT NOT NULL, run_id INTEGER, PRIMARY KEY(job_id, ordinal))")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS execution_jobs_outstanding ON execution_jobs((1)) WHERE status IN ('queued','active')")
            c.execute('CREATE INDEX IF NOT EXISTS execution_jobs_owner ON execution_jobs(owner_id,created_at)')

    @contextmanager
    def connection(self):
        c = sqlite3.connect(self.database, timeout=0.25)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        except sqlite3.OperationalError:
            raise ExecutionBusy('Execution storage is busy; retry the same intent') from None
        finally:
            c.close()

    def public(self, row, connection):
        job = {k: row[k] for k in ('job_id', 'status', 'created_at', 'started_at', 'finished_at', 'run_id', 'error_category', 'group_id')}
        if row['campaign_id']:
            snapshot = json.loads(row['snapshot'])
            job.update(campaign_id=row['campaign_id'], ordinal=snapshot['ordinal'], excluded_files=list(snapshot['exclusions'].values()))
            job['attempts'] = [dict(attempt) for attempt in connection.execute(
                'SELECT ordinal,status,run_id FROM campaign_job_attempts WHERE job_id=? ORDER BY ordinal', (row['job_id'],)
            )]
        elif not row['group_id'] and json.loads(row['snapshot']).get('kind') == 'metadata':
            job['workflow'] = 'metadata-v1'
        return job

    def find_intent(self, owner, intent, fingerprint):
        with self.connection() as c:
            row = c.execute('SELECT * FROM execution_jobs WHERE owner_id=? AND intent=?', (owner, intent)).fetchone()
            if row is None:
                return None
            if row['fingerprint'] != fingerprint:
                raise ValueError('submission intent already belongs to different inputs')
            return self.public(row, c)

    def admit(self, owner, intent, fingerprint, snapshot):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            existing = c.execute('SELECT * FROM execution_jobs WHERE owner_id=? AND intent=?', (owner, intent)).fetchone()
            if existing:
                if existing['fingerprint'] != fingerprint:
                    raise ValueError('submission intent already belongs to different inputs')
                return self.public(existing, c)
            if c.execute("SELECT 1 FROM execution_jobs WHERE status IN ('queued','active')").fetchone():
                raise ExecutionBusy('Execution is busy; no waiting queue is available')
            identifier = uuid4().hex
            c.execute("INSERT INTO execution_jobs(job_id,owner_id,intent,fingerprint,snapshot,status,created_at) VALUES(?,?,?,?,?,'queued',?)", (identifier, owner, intent, fingerprint, json.dumps(snapshot), self.clock()))
            return self.public(c.execute('SELECT * FROM execution_jobs WHERE job_id=?', (identifier,)).fetchone(), c)

    def get(self, identifier, owner):
        with self.connection() as c:
            row = c.execute('SELECT * FROM execution_jobs WHERE job_id=? AND owner_id=?', (identifier, owner)).fetchone()
            if row is None:
                raise KeyError('job not found')
            return self.public(row, c)

    def admit_campaign(self, owner, intent, fingerprint, snapshot):
        identifier = snapshot['configuration']['campaign_id']
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            existing = c.execute('SELECT * FROM execution_jobs WHERE owner_id=? AND intent=?', (owner, intent)).fetchone()
            if existing:
                if existing['fingerprint'] != fingerprint:
                    raise ValueError('submission intent already belongs to different inputs')
                return self.public(existing, c)
            if c.execute("SELECT 1 FROM execution_jobs WHERE status IN ('queued','active')").fetchone():
                raise ExecutionBusy('Execution is busy; no waiting queue is available')
            campaign = c.execute('SELECT status FROM campaigns WHERE campaign_id=? AND owner_id=?', (identifier, owner)).fetchone()
            if campaign is None:
                raise KeyError('campaign not found')
            if snapshot['ordinal'] is None and campaign['status'] != 'created':
                raise ExecutionBusy('Campaign execution has already been claimed')
            job_id = uuid4().hex
            c.execute("INSERT INTO execution_jobs(job_id,owner_id,intent,fingerprint,snapshot,status,created_at,campaign_id) VALUES(?,?,?,?,?,'queued',?,?)",
                      (job_id, owner, intent, fingerprint, json.dumps(snapshot), self.clock(), identifier))
            c.executemany("INSERT INTO campaign_job_attempts(job_id,ordinal,status) VALUES(?,?,'queued')",
                          [(job_id, index) for index in snapshot['attempts']])
            if snapshot['ordinal'] is None:
                c.execute("UPDATE campaigns SET status='running' WHERE campaign_id=?", (identifier,))
                c.executemany("UPDATE campaign_scenarios SET error='invalid_scenario' WHERE campaign_id=? AND ordinal=?",
                              [(identifier, index) for index in snapshot['exclusions']])
            return self.public(c.execute('SELECT * FROM execution_jobs WHERE job_id=?', (job_id,)).fetchone(), c)

    def start_campaign_attempt(self, claim, ordinal):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            updated = c.execute("UPDATE execution_jobs SET lease_until=? WHERE job_id=? AND owner_id=? AND claim=? AND status='active' AND lease_until>?",
                                (self.clock()+60, claim['job_id'], claim['owner_id'], claim['claim'], self.clock()))
            if updated.rowcount != 1:
                raise ExecutionBusy('Execution claim is expired')
            updated = c.execute("UPDATE campaign_job_attempts SET status='active' WHERE job_id=? AND ordinal=? AND status='queued'", (claim['job_id'], ordinal))
            if updated.rowcount != 1:
                raise ExecutionBusy('Campaign attempt is already dispatched')

    def list(self, owner):
        with self.connection() as c:
            return [self.public(row, c) for row in c.execute('SELECT * FROM execution_jobs WHERE owner_id=? ORDER BY created_at DESC LIMIT 100', (owner,))]

    def reconcile(self):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            self.interrupt(c, expired_only=False)

    def claim(self):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            self.interrupt(c, expired_only=True)
            row = c.execute("SELECT * FROM execution_jobs WHERE status='queued' LIMIT 1").fetchone()
            if row is None:
                return None
            token = uuid4().hex
            c.execute("UPDATE execution_jobs SET status='active',claim=?,started_at=?,lease_until=? WHERE job_id=? AND status='queued'", (token, self.clock(), self.clock()+60, row['job_id']))
            return {'job_id': row['job_id'], 'owner_id': row['owner_id'], 'claim': token, 'snapshot': json.loads(row['snapshot'])}

    def fail_claim(self, claim, category='investigation_execution_error'):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute("SELECT group_id,campaign_id FROM execution_jobs WHERE job_id=? AND owner_id=? AND claim=? AND status='active'", (claim['job_id'], claim['owner_id'], claim['claim'])).fetchone()
            if row is None:
                return
            status = 'failed'
            if row['group_id']:
                self.interrupt_group(c, claim['job_id'])
                status, category = 'interrupted', 'provider_outcome_uncertain'
            elif row['campaign_id']:
                self.interrupt_campaign(c, claim['job_id'])
                status, category = 'interrupted', 'provider_outcome_uncertain'
            c.execute("UPDATE execution_jobs SET status=?,error_category=?,finished_at=?,lease_until=NULL WHERE job_id=?", (status, category, self.clock(), claim['job_id']))

    def begin_attempt(self, claim):
        with self.connection() as c:
            updated = c.execute("UPDATE execution_jobs SET dispatched=1 WHERE job_id=? AND owner_id=? AND claim=? AND status='active' AND dispatched=0 AND lease_until>?", (claim['job_id'], claim['owner_id'], claim['claim'], self.clock()))
            if updated.rowcount != 1:
                raise ExecutionBusy('Execution claim is expired or already dispatched')

    def admit_group(self, owner, intent, fingerprint, snapshot, identifier=None):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            existing = c.execute('SELECT * FROM execution_jobs WHERE owner_id=? AND intent=?', (owner, intent)).fetchone()
            if existing:
                if existing['fingerprint'] != fingerprint:
                    raise ValueError('submission intent already belongs to different inputs')
                return self.public(existing, c)
            if c.execute("SELECT 1 FROM execution_jobs WHERE status IN ('queued','active')").fetchone():
                raise ExecutionBusy('Execution is busy; no waiting queue is available')
            if identifier is None:
                identifier = uuid4().hex
                c.execute("INSERT INTO run_groups(group_id,plan,owner_id,status) VALUES(?,?,?,'queued')", (identifier, json.dumps(snapshot['plan']), owner))
            else:
                group = c.execute('SELECT owner_id,status,plan FROM run_groups WHERE group_id=?', (identifier,)).fetchone()
                if group is None or group['owner_id'] != owner:
                    raise KeyError('group not found')
                if json.loads(group['plan']) != snapshot['plan']:
                    raise ValueError('group inputs changed')
                c.execute("UPDATE run_groups SET status='queued' WHERE group_id=?", (identifier,))
            job_id = uuid4().hex
            offset = c.execute('SELECT COALESCE(MAX(attempt),0) FROM run_group_attempts WHERE group_id=?', (identifier,)).fetchone()[0]
            plan = snapshot['plan']
            attempts = [dict(attempt=offset+i+1, repeat=repeat, condition=condition) for i, (repeat, condition) in enumerate((r, condition) for r in range(1, plan['repeats']+1) for condition in plan['conditions'])]
            c.executemany("INSERT INTO run_group_attempts(group_id,attempt,repeat,condition,job_id,execution_status) VALUES(?,?,?,?,?,'queued')", [(identifier, a['attempt'], a['repeat'], a['condition'], job_id) for a in attempts])
            snapshot = {**snapshot, 'group_id':identifier, 'attempts':attempts}
            c.execute("INSERT INTO execution_jobs(job_id,owner_id,intent,fingerprint,snapshot,status,created_at,group_id) VALUES(?,?,?,?,?,'queued',?,?)", (job_id,owner,intent,fingerprint,json.dumps(snapshot),self.clock(),identifier))
            return self.public(c.execute('SELECT * FROM execution_jobs WHERE job_id=?', (job_id,)).fetchone(), c)

    def start_group_attempt(self, claim, attempt):
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            updated = c.execute("UPDATE execution_jobs SET lease_until=? WHERE job_id=? AND owner_id=? AND claim=? AND status='active' AND lease_until>?", (self.clock()+60, claim['job_id'], claim['owner_id'], claim['claim'], self.clock()))
            if updated.rowcount != 1:
                raise ExecutionBusy('Execution claim is no longer valid')
            updated = c.execute("UPDATE run_group_attempts SET execution_status='active' WHERE job_id=? AND attempt=? AND execution_status='queued' AND run_id IS NULL", (claim['job_id'], attempt))
            if updated.rowcount != 1:
                raise ExecutionBusy('Attempt is already dispatched')
            c.execute("UPDATE run_groups SET status='running' WHERE group_id=? AND owner_id=?", (claim['snapshot']['group_id'], claim['owner_id']))

    def interrupt_group(self, c, identifier):
        c.execute("UPDATE run_group_attempts SET execution_status=CASE WHEN execution_status='active' THEN 'interrupted' ELSE 'missing' END WHERE job_id=? AND run_id IS NULL AND execution_status IN ('active','queued')", (identifier,))
        c.execute("UPDATE run_groups SET status='interrupted' WHERE group_id=(SELECT group_id FROM execution_jobs WHERE job_id=?)", (identifier,))

    def interrupt(self, c, *, expired_only):
        query = "SELECT job_id FROM execution_jobs WHERE status='active'"
        rows = c.execute(query + (' AND lease_until<=?' if expired_only else ''), (self.clock(),) if expired_only else ()).fetchall()
        for row in rows:
            self.interrupt_group(c, row['job_id'])
            self.interrupt_campaign(c, row['job_id'])
            c.execute("UPDATE execution_jobs SET status='interrupted',error_category='provider_outcome_uncertain',finished_at=?,lease_until=NULL WHERE job_id=?", (self.clock(), row['job_id']))

    def interrupt_campaign(self, c, job_id):
        c.execute("UPDATE campaign_job_attempts SET status=CASE WHEN status='active' THEN 'interrupted' ELSE 'missing' END WHERE job_id=? AND status IN ('active','queued')", (job_id,))
        c.execute("UPDATE campaigns SET status='interrupted' WHERE campaign_id=(SELECT campaign_id FROM execution_jobs WHERE job_id=? AND json_type(snapshot,'$.ordinal')='null')", (job_id,))
