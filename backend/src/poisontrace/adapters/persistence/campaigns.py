import sqlite3
from pathlib import Path
from uuid import uuid4

from poisontrace.adapters.persistence.support import initialize_database


class InMemoryCampaignStore:
    def __init__(self) -> None: self.campaigns = {}
    def create(self, *, provider, model, credential_id, scenarios):
        cid = f"CMP-{uuid4().hex}"
        self.campaigns[cid] = {"campaign_id": cid, "status": "created", "provider": provider, "model": model, "credential_id": credential_id, "scenario_filenames": [x[0] for x in scenarios], "scenarios": [{"filename": x[0], "scenario_id": x[1], "child_run_id": None, "error": None} for x in scenarios]}
        return cid
    def get(self, campaign_id):
        if campaign_id not in self.campaigns: raise KeyError(campaign_id)
        value = self.campaigns[campaign_id]
        return {**value, "scenarios": [dict(item) for item in value["scenarios"]]}
    def list(self): return list(reversed([self.get(cid) for cid in self.campaigns]))
    def set_status(self, campaign_id, status): self.campaigns[campaign_id]["status"] = status
    def associate_child_run(self, campaign_id, ordinal, *, child_run_id=None, error=None): self.campaigns[campaign_id]["scenarios"][ordinal].update(child_run_id=child_run_id, error=error)


class SqliteCampaignStore:
    def __init__(self, database: Path) -> None: self.database = database; initialize_database(database)
    def create(self, *, provider, model, credential_id, scenarios):
        cid = f"CMP-{uuid4().hex}"
        with sqlite3.connect(self.database) as c:
            c.execute("INSERT INTO campaigns (campaign_id,status,provider,model,credential_id) VALUES (?,?,?,?,?)", (cid,"created",provider,model,credential_id))
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
        with sqlite3.connect(self.database) as c: c.execute("UPDATE campaigns SET status=? WHERE campaign_id=?", (status, campaign_id))
    def associate_child_run(self, campaign_id, ordinal, *, child_run_id=None, error=None):
        with sqlite3.connect(self.database) as c: c.execute("UPDATE campaign_scenarios SET child_run_id=?,error=? WHERE campaign_id=? AND ordinal=?", (child_run_id, error, campaign_id, ordinal))
