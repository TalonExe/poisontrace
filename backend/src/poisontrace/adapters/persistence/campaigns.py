import sqlite3
from pathlib import Path
from uuid import uuid4

from poisontrace.adapters.persistence.support import initialize_database
from poisontrace.application.principals import analyst_owner_id


class InMemoryCampaignStore:
    def __init__(self, runs=None) -> None: self.campaigns = {}; self.owners = {}; self.runs = runs
    def owner_for(self, campaign_id): return self.owners.get(campaign_id)
    def ids_for(self, owner_id): return [cid for cid in reversed(self.campaigns) if self.owners.get(cid) == owner_id]
    def create(self, *, provider, model, credential_id, scenarios):
        cid = f"CMP-{uuid4().hex}"
        self.owners[cid] = analyst_owner_id()
        self.campaigns[cid] = {"campaign_id": cid, "status": "created", "provider": provider, "model": model, "credential_id": credential_id, "scenario_filenames": [x[0] for x in scenarios], "scenarios": [{"filename": x[0], "scenario_id": x[1], "child_run_id": None, "error": None} for x in scenarios]}
        return cid
    def get(self, campaign_id):
        if campaign_id not in self.campaigns: raise KeyError(campaign_id)
        value = self.campaigns[campaign_id]
        return {**value, "scenarios": [dict(item) for item in value["scenarios"]]}
    def list(self): return list(reversed([self.get(cid) for cid in self.campaigns]))
    def _authorize(self, campaign_id):
        owner = analyst_owner_id()
        if owner is None or self.owner_for(campaign_id) != owner:
            raise KeyError('campaign not found')
        return owner
    def set_status(self, campaign_id, status):
        self._authorize(campaign_id)
        self.campaigns[campaign_id]["status"] = status
    def associate_child_run(self, campaign_id, ordinal, *, child_run_id=None, error=None):
        owner = self._authorize(campaign_id)
        if child_run_id is not None and (self.runs is None or self.runs.owner_for(child_run_id) != owner):
            raise KeyError('run not found')
        self.campaigns[campaign_id]["scenarios"][ordinal].update(child_run_id=child_run_id, error=error)


class SqliteCampaignStore:
    def __init__(self, database: Path) -> None: self.database = database; initialize_database(database)
    def owner_for(self, campaign_id):
        with sqlite3.connect(self.database) as c:
            row = c.execute('SELECT owner_id FROM campaigns WHERE campaign_id=?', (campaign_id,)).fetchone()
        return row[0] if row else None
    def ids_for(self, owner_id):
        with sqlite3.connect(self.database) as c:
            return [r[0] for r in c.execute('SELECT campaign_id FROM campaigns WHERE owner_id=? ORDER BY created_at DESC, rowid DESC', (owner_id,))]
    def create(self, *, provider, model, credential_id, scenarios):
        cid = f"CMP-{uuid4().hex}"
        with sqlite3.connect(self.database) as c:
            c.execute("INSERT INTO campaigns (campaign_id,status,provider,model,credential_id,owner_id) VALUES (?,?,?,?,?,?)", (cid,"created",provider,model,credential_id,analyst_owner_id()))
            c.executemany("INSERT INTO campaign_scenarios (campaign_id,ordinal,filename,scenario_id) VALUES (?,?,?,?)", [(cid,i,f,s) for i,(f,s) in enumerate(scenarios)])
        return cid
    def get(self, campaign_id):
        with sqlite3.connect(self.database) as c:
            row = c.execute("SELECT campaign_id,status,provider,model,credential_id FROM campaigns WHERE campaign_id=?", (campaign_id,)).fetchone()
            if row is None: raise KeyError(campaign_id)
            items = c.execute("SELECT ordinal,filename,scenario_id,child_run_id,error FROM campaign_scenarios WHERE campaign_id=? ORDER BY ordinal", (campaign_id,)).fetchall()
        return {"campaign_id": row[0], "status": row[1], "provider": row[2], "model": row[3], "credential_id": row[4], "scenario_filenames": [x[1] for x in items], "scenarios": [{"filename": x[1], "scenario_id": x[2], "child_run_id": x[3], "error": x[4]} for x in items]}
    def list(self):
        with sqlite3.connect(self.database) as c: ids = [x[0] for x in c.execute("SELECT campaign_id FROM campaigns ORDER BY created_at DESC, rowid DESC")]
        return [self.get(cid) for cid in ids]
    def set_status(self, campaign_id, status):
        with sqlite3.connect(self.database) as c:
            c.execute('BEGIN IMMEDIATE')
            self._authorize(c, campaign_id)
            c.execute("UPDATE campaigns SET status=? WHERE campaign_id=?", (status, campaign_id))
    def associate_child_run(self, campaign_id, ordinal, *, child_run_id=None, error=None):
        with sqlite3.connect(self.database) as c:
            c.execute('BEGIN IMMEDIATE')
            owner = self._authorize(c, campaign_id)
            if child_run_id is not None:
                child = c.execute('SELECT owner_id FROM runs WHERE id=?', (child_run_id,)).fetchone()
                if child is None or child[0] != owner:
                    raise KeyError('run not found')
            c.execute("UPDATE campaign_scenarios SET child_run_id=?,error=? WHERE campaign_id=? AND ordinal=?", (child_run_id, error, campaign_id, ordinal))

    @staticmethod
    def _authorize(connection, campaign_id):
        owner = analyst_owner_id()
        row = connection.execute('SELECT owner_id FROM campaigns WHERE campaign_id=?', (campaign_id,)).fetchone()
        if owner is None or row is None or row[0] != owner:
            raise KeyError('campaign not found')
        return owner
