import argparse
from contextlib import closing, contextmanager
from io import BytesIO
import os
from pathlib import Path, PurePosixPath
import sqlite3
from tempfile import TemporaryDirectory
import time
from uuid import uuid4
from zipfile import ZIP_STORED, ZipFile

from cryptography.fernet import Fernet, InvalidToken

from poisontrace.adapters.execution.jobs import executor_lock
from poisontrace.adapters.persistence.jobs import SqliteJobStore
from poisontrace.adapters.persistence.recovery_ledger import RecoveryLedger
from poisontrace.adapters.persistence.retention import reconcile_history
from poisontrace.production import RuntimeConfig, runtime_lock


DATABASES = ("poisontrace.db", "poisontrace-secrets.db")
CONTENT = {"scenarios": {".yaml", ".yml"}, "investigation-cases": {".json"}}
REQUIRED = {*DATABASES, ".scenario-seeds-v1", "backup-format-v1"}
MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024


def cipher_for(key):
    try:
        return Fernet(key)
    except (TypeError, ValueError):
        raise ValueError("a valid recovery key is required") from None


def ledger_for(config, root):
    if config.web.recovery_ledger is None:
        raise ValueError("an independent recovery ledger is required")
    return RecoveryLedger(config.web.recovery_ledger, root / DATABASES[1], Fernet(config.web.require_secrets_key()))


@contextmanager
def stopped(config):
    if not config.data_root.is_dir():
        raise ValueError("existing application state is required")
    with runtime_lock(config), executor_lock(config.web.database) as worker:
        if not worker:
            raise RuntimeError("stop the application and its executor before maintenance")
        yield


def outside_state(config, path):
    path = Path(path).resolve()
    if path.is_relative_to(config.data_root) or config.data_root.is_relative_to(path):
        raise ValueError("operation requires a path separate from application state")
    return path


def snapshot_database(source, destination):
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as live:
        with closing(sqlite3.connect(destination)) as copy:
            live.backup(copy)
            if copy.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise ValueError("SQLite snapshot failed validation")


def backup(config, destination, recovery_key):
    cipher = cipher_for(recovery_key)
    if recovery_key == config.web.require_secrets_key():
        raise ValueError("archive and application keys must be separate")
    destination = outside_state(config, destination)
    if destination.suffix != ".ptbackup":
        raise ValueError("archive path must end with .ptbackup")
    with stopped(config):
        ledger = ledger_for(config, config.data_root)
        if (config.data_root / ".restore-pending").exists():
            raise ValueError("restore must be activated before backup")
        with TemporaryDirectory(dir=config.data_root) as scratch:
            scratch = Path(scratch)
            for database in DATABASES:
                snapshot_database(config.data_root / database, scratch / database)
            files = {name: scratch / name for name in DATABASES}
            files[".scenario-seeds-v1"] = config.data_root / ".scenario-seeds-v1"
            for directory, suffixes in CONTENT.items():
                content = config.data_root / directory
                if content.is_symlink():
                    raise ValueError("unsupported application content directory")
                for path in content.iterdir():
                    if path.suffix in suffixes:
                        if not path.is_file() or path.is_symlink():
                            raise ValueError("unsupported application content path")
                        files[f"{directory}/{path.name}"] = path
            if sum(path.stat().st_size for path in files.values()) > MAX_SNAPSHOT_BYTES:
                raise ValueError("application snapshot exceeds the supported size")
            payload = BytesIO()
            with ZipFile(payload, "w", compression=ZIP_STORED) as archive:
                archive.writestr("backup-format-v1", str(ledger.scenario_revision()))
                for name, path in files.items():
                    archive.write(path, name)
            token = cipher.encrypt(payload.getvalue())
            temporary = destination.parent / f".{uuid4().hex}.partial"
            try:
                with temporary.open("xb") as output:
                    output.write(token)
                    output.flush()
                    os.fsync(output.fileno())
                os.link(temporary, destination)
                if os.name != "nt":
                    descriptor = os.open(destination.parent, os.O_RDONLY)
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
            finally:
                temporary.unlink(missing_ok=True)


def restore(config, archive, target, recovery_key):
    cipher = cipher_for(recovery_key)
    archive = outside_state(config, archive)
    target = outside_state(config, target)
    if target.exists() or archive.is_relative_to(target):
        raise ValueError("restore requires a new isolated state directory")
    if archive.stat().st_size > 2 * MAX_SNAPSHOT_BYTES:
        raise ValueError("archive exceeds the supported size")
    try:
        payload = cipher.decrypt(archive.read_bytes())
    except InvalidToken:
        raise ValueError("incorrect recovery key or damaged archive") from None
    with TemporaryDirectory(dir=target.parent) as scratch:
        root = Path(scratch) / "state"
        root.mkdir()
        for directory in CONTENT:
            (root / directory).mkdir()
        with ZipFile(BytesIO(payload)) as snapshot:
            names = snapshot.namelist()
            if (not REQUIRED.issubset(names) or len(set(names)) != len(names)
                    or sum(item.file_size for item in snapshot.infolist()) > MAX_SNAPSHOT_BYTES):
                raise ValueError("invalid backup inventory")
            revision = int(snapshot.read("backup-format-v1"))
            if revision < 0:
                raise ValueError("invalid recovery revision")
            for name in names:
                path = PurePosixPath(name)
                if name == "backup-format-v1":
                    continue
                if name not in REQUIRED and (
                    len(path.parts) != 2 or path.parts[0] not in CONTENT
                    or path.suffix not in CONTENT[path.parts[0]] or path.as_posix() != name
                    or "\\" in name or ":" in name
                ):
                    raise ValueError("invalid backup path")
                with (root / name).open("xb") as output:
                    output.write(snapshot.read(name))
        for name in DATABASES:
            with closing(sqlite3.connect(root / name)) as connection:
                if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                    raise ValueError("invalid backup database")
        ledger = ledger_for(config, root)
        ledger.reconcile_credentials()
        ledger.reconcile_scenarios(root / "scenarios", revision)
        (root / ".restore-pending").write_text(str(revision), encoding="ascii")
        root.rename(target)


def activate(config):
    with stopped(config):
        pending = config.data_root / ".restore-pending"
        if not pending.is_file():
            raise ValueError("activation requires a pending isolated restore")
        ledger = ledger_for(config, config.data_root)
        ledger.reconcile_credentials()
        ledger.reconcile_scenarios(config.web.scenario_dir, int(pending.read_text(encoding="ascii")))
        jobs = SqliteJobStore(config.web.database)
        with jobs.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            reconcile_history(connection, ledger)
            connection.execute("DELETE FROM auth_sessions")
            connection.execute("UPDATE execution_jobs SET status='active' WHERE status='queued'")
            jobs.interrupt(connection, expired_only=False)
        pending.unlink()


def validate_cutoff(cutoff):
    import math
    if not math.isfinite(cutoff) or cutoff > time.time():
        raise ValueError("expiry cutoff must be a finite UTC time no later than now")


def expire_history(config, *, cutoff):
    validate_cutoff(cutoff)
    with stopped(config):
        if (config.data_root / ".restore-pending").exists():
            raise ValueError("restore must be activated before expiry")
        ledger = ledger_for(config, config.data_root)
        with closing(sqlite3.connect(config.web.database.as_uri() + "?mode=rw", uri=True)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            return reconcile_history(connection, ledger, cutoff)


def expire_backups(config, directory, *, cutoff):
    validate_cutoff(cutoff)
    directory = outside_state(config, directory)
    removed = 0
    for archive in directory.glob("*.ptbackup"):
        if archive.is_symlink() or not archive.is_file():
            continue
        if archive.stat().st_mtime <= cutoff:
            archive.unlink()
            removed += 1
    return removed


def main():
    parser = argparse.ArgumentParser(description="Operate on stopped production state and independent backups")
    commands = parser.add_subparsers(dest="command", required=True)
    store = commands.add_parser("backup")
    store.add_argument("archive", type=Path)
    recover = commands.add_parser("restore")
    recover.add_argument("archive", type=Path)
    recover.add_argument("target", type=Path)
    review = commands.add_parser("activate")
    review.add_argument("--reviewed", action="store_true", required=True)
    history = commands.add_parser("expire-history")
    history.add_argument("--days", required=True, type=int)
    archives = commands.add_parser("expire-backups")
    archives.add_argument("directory", type=Path)
    archives.add_argument("--days", required=True, type=int)
    args = parser.parse_args()
    try:
        config = RuntimeConfig.from_environment()
        key = os.environ.get("POISONTRACE_BACKUP_KEY", "").encode()
        if args.command == "backup":
            backup(config, args.archive, key)
        elif args.command == "restore":
            restore(config, args.archive, args.target, key)
        elif args.command == "activate":
            activate(config)
        else:
            if not 0 < args.days <= 36500:
                raise ValueError("retention days must be between 1 and 36500")
            cutoff = time.time() - args.days * 86400
            count = (expire_history(config, cutoff=cutoff) if args.command == "expire-history"
                     else expire_backups(config, args.directory, cutoff=cutoff))
            print(f"Expired {count} records.")
    except (OSError, RuntimeError, ValueError, sqlite3.Error):
        parser.exit(1, "Recovery operation failed. Check configuration, keys, file access and maintenance state.\n")


if __name__ == "__main__":
    main()
