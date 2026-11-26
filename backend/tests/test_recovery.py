import gc
import time
from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
import pytest

from poisontrace.production import RuntimeConfig, build_application, initialize_admin
from test_durable_groups import selection
from test_production import environment


def test_encrypted_restore_reconciles_revocations_and_requires_activation(tmp_path):
    from poisontrace.adapters.persistence.jobs import SqliteJobStore
    from poisontrace.recovery import activate, backup, restore

    ledger = str(tmp_path / "recovery-ledger.db")
    config = RuntimeConfig.from_environment(environment(tmp_path, POISONTRACE_RECOVERY_LEDGER=ledger))
    initialize_admin(config, "operator", "scratch-admin")
    archive = tmp_path / "backups" / "snapshot.ptbackup"
    archive.parent.mkdir()
    recovery_key = Fernet.generate_key()
    app = build_application(config)
    deleted_scenario = next(config.web.scenario_dir.glob("*.yaml"))
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": "operator", "passcode": "scratch-admin"}).status_code == 200
        for name in ("alice", "bob"):
            assert client.post("/api/admin/users", json={"username": name, "display_name": name, "passcode": f"scratch-{name}"}).status_code == 201
        assert client.post("/api/auth/login", json={"username": "alice", "passcode": "scratch-alice"}).status_code == 200
        refs = [client.post("/api/credentials", json={"provider": "openai", "secret": f"scratch-secret-{i}"}).json()["credential_id"] for i in range(2)]
        case_path = "/api/runs/investigation-cases/soc-auth-001"
        case = client.get(case_path).json()
        update = {name: case[name] for name in ("expected_decision", "dataset_category", "attack_targets")}
        update["base_version"] = case["case_version"]
        update["expected_decision"]["priority"] = "P2"
        assert client.put(case_path, json=update).status_code == 200
        case_version = client.get(case_path).json()["case_version"]
        payload = selection()
        payload["case_version"] = case_version
        submitted = client.post("/api/run-groups", json=payload, headers={"Idempotency-Key": uuid4().hex})
        assert submitted.status_code == 202, submitted.text
        group_path = "/api/run-groups/" + submitted.json()["group_id"]
        job_path = "/api/investigation-jobs/" + submitted.json()["job_id"]
        deadline = time.monotonic() + 50
        while client.get(job_path).json()["status"] in {"queued", "active"} and time.monotonic() < deadline:
            time.sleep(0.1)
        assert client.get(job_path).json()["status"] == "completed"
        group = client.get(group_path).json()
        run_path = "/api/runs/" + str(group["attempts"][0]["run_id"])
        history = client.get(run_path).json()
        with pytest.raises(RuntimeError, match="stop"):
            backup(config, archive, recovery_key)
        session = client.cookies.get("poisontrace_session")
    offline_client = TestClient(app)
    offline_client.cookies.set("poisontrace_session", session)
    single = {"case_id": "soc-auth-001", "provider": "scripted", "mode": "clean"}
    previously_interrupted = offline_client.post("/api/investigation-jobs", json=single, headers={"Idempotency-Key": uuid4().hex})
    assert previously_interrupted.status_code == 202
    jobs = SqliteJobStore(config.web.database)
    claim = jobs.claim()
    assert claim["job_id"] == previously_interrupted.json()["job_id"]
    jobs.reconcile()
    interrupted_path = "/api/investigation-jobs/" + claim["job_id"]
    interrupted = offline_client.get(interrupted_path).json()
    assert interrupted["status"] == "interrupted"
    pending = offline_client.post("/api/investigation-jobs", json=single, headers={"Idempotency-Key": uuid4().hex})
    assert pending.status_code == 202, pending.text
    pending_path = "/api/investigation-jobs/" + pending.json()["job_id"]
    assert offline_client.get(pending_path).json()["status"] == "queued"
    offline_client.close()
    gc.collect()
    backup(config, archive, recovery_key)

    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"username": "alice", "passcode": "scratch-alice"}).status_code == 200
        assert client.delete(f"/api/credentials/{refs[0]}").status_code in (200, 204)
        assert client.post(f"/api/credentials/{refs[0]}/test").status_code == 404
        assert client.delete(f"/api/scenarios/{deleted_scenario.stem}").status_code == 200
    gc.collect()

    started_recovery = time.monotonic()
    target = tmp_path / "restored"
    for bad_key in (b"", Fernet.generate_key()):
        with pytest.raises(ValueError):
            restore(config, archive, target, bad_key)
        assert not target.exists()
    from dataclasses import replace
    wrong_app_key = replace(config, web=replace(config.web, secrets_key=Fernet.generate_key()))
    with pytest.raises(ValueError, match="application encryption key"):
        restore(wrong_app_key, archive, target, recovery_key)
    assert not target.exists()
    restore(config, archive, target, recovery_key)
    recovered = RuntimeConfig.from_environment(environment(
        tmp_path, POISONTRACE_DATA_ROOT=str(target), POISONTRACE_SECRETS_KEY=config.web.secrets_key.decode(),
        POISONTRACE_RECOVERY_LEDGER=ledger
    ))
    with pytest.raises(RuntimeError, match="activation"):
        build_application(recovered)
    activate(recovered)
    assert not (recovered.web.scenario_dir / deleted_scenario.name).exists()
    with TestClient(build_application(recovered)) as client:
        client.cookies.set("poisontrace_session", session)
        assert client.get(group_path).status_code == 401
        client.cookies.clear()
        assert client.post("/api/auth/login", json={"username": "bob", "passcode": "scratch-bob"}).status_code == 200
        assert client.get(group_path).status_code == 404
        assert client.get(run_path).status_code == 404
        assert client.get(pending_path).status_code == 404
        assert client.post(f"/api/credentials/{refs[1]}/test").status_code == 404
        assert client.post("/api/auth/login", json={"username": "alice", "passcode": "scratch-alice"}).status_code == 200
        assert client.post(f"/api/credentials/{refs[0]}/test").status_code == 404
        assert client.post(f"/api/credentials/{refs[1]}/test").status_code == 200
        assert client.get(group_path).json() == group
        assert client.get(run_path).json() == history
        assert client.get(case_path).json()["case_version"] == case_version
        restored_job = client.get(pending_path).json()
        assert restored_job["status"] == "interrupted"
        assert restored_job["run_id"] is None
        assert client.get(interrupted_path).json() == interrupted
    print(f"Scratch restore through application verification: {time.monotonic() - started_recovery:.2f} seconds")

def test_retention_expires_linked_history_at_boundary_and_reconciles_old_backup(tmp_path):
    import sqlite3
    from contextlib import closing
    from poisontrace.recovery import activate, backup, expire_backups, expire_history, restore

    ledger = str(tmp_path / "ledger.db")
    config = RuntimeConfig.from_environment(environment(tmp_path, POISONTRACE_RECOVERY_LEDGER=ledger))
    build_application(config)
    gc.collect()
    with closing(sqlite3.connect(config.web.database)) as db, db:
        for run_id, created_at in ((1, 10), (2, 9), (3, 10), (4, 11), (5, 9), (6, 11)):
            db.execute("INSERT INTO runs(id,scenario_id,mode,recommendation,benign_task_success,attack_success,execution_time_ms,system_error,unauthorised_tool_call,created_at) VALUES (?, 'scratch','clean','review',1,0,1,0,0,?)", (run_id, created_at))
            db.execute("INSERT INTO events(run_id,kind,data,created_at) VALUES (?,'scratch','{}',?)", (run_id, created_at))
        for name in ("expired", "retained"):
            db.execute("INSERT INTO run_groups(group_id,plan,status,created_at) VALUES (?,'{}','finished','1970-01-01 00:00:09')", (name,))
        for index, (group, run_id) in enumerate((("expired", 1), ("retained", 2), ("retained", 4))):
            db.execute("INSERT INTO run_group_attempts(group_id,attempt,repeat,condition,run_id) VALUES (?,?,1,'clean',?)", (group, index, run_id))
        db.execute("INSERT INTO campaigns(campaign_id,status,provider,model,owner_id,created_at) VALUES ('campaign','completed','scripted','scratch',1,'1970-01-01 00:00:09')")
        db.execute("INSERT INTO campaign_scenarios(campaign_id,ordinal,filename,scenario_id,child_run_id) VALUES ('campaign',0,'scratch.yaml','scratch',6)")
        db.execute("UPDATE runs SET owner_id=1,run_configuration=json_object('campaign_id','campaign') WHERE id IN (5,6)")
    backups = tmp_path / "backup"
    backups.mkdir()
    path = backups / "snapshot.ptbackup"
    key = Fernet.generate_key()
    backup(config, path, key)
    expire_history(config, cutoff=10)
    recovered = tmp_path / "recovered"
    restore(config, path, recovered, key)
    restored_config = RuntimeConfig.from_environment(environment(
        tmp_path, POISONTRACE_DATA_ROOT=str(recovered), POISONTRACE_SECRETS_KEY=config.web.secrets_key.decode(),
        POISONTRACE_RECOVERY_LEDGER=ledger
    ))
    activate(restored_config)
    for current in (config, restored_config):
        with closing(sqlite3.connect(current.web.database)) as db:
            assert db.execute("SELECT id FROM runs ORDER BY id").fetchall() == [(2,), (4,), (5,), (6,)]
            assert db.execute("SELECT run_id FROM events ORDER BY run_id").fetchall() == [(2,), (4,), (5,), (6,)]
            assert db.execute("SELECT group_id FROM run_groups").fetchall() == [("retained",)]
            assert db.execute("SELECT run_id FROM run_group_attempts ORDER BY run_id").fetchall() == [(2,), (4,)]
    expiry = path.stat().st_mtime
    assert expire_backups(config, backups, cutoff=expiry - 1) == 0
    assert expire_backups(config, backups, cutoff=expiry) == 1
    assert not path.exists()


def test_failed_second_database_snapshot_leaves_no_published_backup(tmp_path, monkeypatch):
    from poisontrace import recovery

    snapshot = recovery.snapshot_database

    def fail_second(source, destination):
        if source.name == "poisontrace-secrets.db":
            assert (destination.parent / "poisontrace.db").is_file()
            raise OSError("synthetic snapshot failure")
        snapshot(source, destination)

    monkeypatch.setattr(recovery, "snapshot_database", fail_second)

    config = RuntimeConfig.from_environment(environment(tmp_path, POISONTRACE_RECOVERY_LEDGER=str(tmp_path / "ledger.db")))
    build_application(config)
    gc.collect()
    destination = tmp_path / "backups"
    destination.mkdir()
    with pytest.raises(OSError, match="synthetic snapshot failure"):
        recovery.backup(config, destination / "failed.ptbackup", Fernet.generate_key())
    assert not list(destination.iterdir())
