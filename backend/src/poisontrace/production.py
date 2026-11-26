"""Single-process container composition, separate from the development launcher.

The hosted profile is a packaging profile, not authorization for public exposure.
Operational gates remain separate tickets. Hosted content is read-only.
"""
from dataclasses import dataclass, replace
from contextlib import ExitStack, asynccontextmanager, closing, contextmanager
from importlib.resources import files
import os
from pathlib import Path
import shutil
import sqlite3
import time
from tempfile import NamedTemporaryFile

from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from poisontrace.adapters.execution.jobs import executor_lock
from poisontrace.config import WebConfig


@dataclass(frozen=True)
class RuntimeConfig:
    profile: str
    data_root: Path
    frontend_root: Path
    web: WebConfig
    host: str = "0.0.0.0"
    port: int = 8000

    @classmethod
    def from_environment(cls, environment=None):
        env = os.environ if environment is None else environment
        profile = env.get("POISONTRACE_PROFILE", "local")
        if profile not in {"local", "hosted"}:
            raise ValueError("POISONTRACE_PROFILE must be local or hosted")
        root = Path(env.get("POISONTRACE_DATA_ROOT", "/data"))
        frontend = Path(env.get("POISONTRACE_FRONTEND_ROOT", "/opt/poisontrace/frontend"))
        if not root.is_absolute() or not frontend.is_absolute():
            raise ValueError("data and frontend roots must be absolute paths")
        root, frontend = root.resolve(), frontend.resolve()
        if root == frontend or root in frontend.parents or frontend in root.parents:
            raise ValueError("data and frontend roots must be separate")
        try:
            port = int(env.get("PORT", "8000"))
        except ValueError:
            raise ValueError("PORT must be an integer between 1 and 65535") from None
        if not 1 <= port <= 65535:
            raise ValueError("PORT must be between 1 and 65535")
        host = env.get("POISONTRACE_BIND", "0.0.0.0").strip()
        if not host:
            raise ValueError("POISONTRACE_BIND must not be empty")
        web = WebConfig(scenario_dir=root / "scenarios", database=root / "poisontrace.db",
                        secrets_database=root / "poisontrace-secrets.db",
                        secrets_key=env.get("POISONTRACE_SECRETS_KEY", "").encode(),
                        public_origin=env.get("POISONTRACE_PUBLIC_ORIGIN", ""),
                        trusted_proxy_cidrs=WebConfig.from_environment(env).trusted_proxy_cidrs)
        if ledger_value := env.get("POISONTRACE_RECOVERY_LEDGER"):
            ledger = Path(ledger_value)
            if not ledger.is_absolute() or ledger.resolve().is_relative_to(root):
                raise ValueError("recovery ledger must be absolute and outside application state")
            web = replace(web, recovery_ledger=ledger.resolve())
        result = cls(profile, root, frontend, web, host, port)
        result.validate()
        return result

    def validate(self):
        if self.profile not in {"local", "hosted"}:
            raise ValueError("profile must be local or hosted")
        self.web.require_secrets_key()
        replace(self.web, profile=self.profile).validate_http()
        if not (self.frontend_root / "index.html").is_file():
            raise ValueError("built frontend index.html is required")


def _probe_directory(directory):
    with NamedTemporaryFile(prefix=".readiness-", dir=directory) as probe:
        probe.write(b"ready")
        probe.flush()
        os.fsync(probe.fileno())


def ensure_data_root(config):
    try:
        config.data_root.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise RuntimeError("persistent storage is unavailable") from None


def prepare_storage(config):
    config.validate()  # No mkdir or SQLite construction before validation.
    try:
        ensure_data_root(config)
        _probe_directory(config.data_root)
        config.web.scenario_dir.mkdir(exist_ok=True)
        (config.data_root / "investigation-cases").mkdir(exist_ok=True)
        marker = config.data_root / ".scenario-seeds-v1"
        if not marker.exists():
            seeds = files("poisontrace").joinpath("seeds/scenarios")
            for seed in seeds.iterdir():
                if seed.name.endswith(".yaml"):
                    destination = config.web.scenario_dir / seed.name
                    # Never replace an operator edit, even after interrupted initialization.
                    if not destination.exists():
                        with seed.open("rb") as source, destination.open("xb") as target:
                            shutil.copyfileobj(source, target)
            marker.touch()
    except OSError:
        raise RuntimeError("persistent storage is unavailable") from None


@contextmanager
def runtime_lock(config):
    paths = [config.data_root / "runtime"]
    if config.web.recovery_ledger is not None:
        paths.append(config.web.recovery_ledger)
    with ExitStack() as locks:
        for path in paths:
            if not locks.enter_context(executor_lock(path)):
                raise RuntimeError("stop the application before maintenance or starting another replica")
        yield


def initialize_admin(config, username, passcode):
    """Explicit operator command. Refuses a second bootstrap; never resets accounts."""
    from poisontrace.bootstrap import build_accounts
    from poisontrace.config import AccountSeed
    if not username.strip() or len(username.strip().casefold()) > 254 or not passcode or len(passcode) > 1024:
        raise ValueError("admin username of 1 to 254 characters and passcode of 1 to 1024 characters are required")
    config.validate()
    ensure_data_root(config)
    with runtime_lock(config):
        prepare_storage(config)
        # Single writer/operator command, invoked while the server is stopped.
        if config.web.database.exists():
            accounts = build_accounts(config.web.database, seeds=())
            if accounts.list_users():
                raise ValueError("accounts already exist; bootstrap will not reset or add an admin")
        build_accounts(config.web.database, seeds=(AccountSeed(username, "superadmin", passcode),))


def recover_admin(config, username, passcode, *, enable_disabled=False):
    from poisontrace.bootstrap import build_accounts
    config.validate()
    if not config.web.database.is_file():
        raise ValueError("an existing superadmin is required; use init-admin for a fresh installation")
    return build_accounts(config.web.database, seeds=()).recover_superadmin(
        username, passcode, enable_disabled=enable_disabled)


def storage_ready(config):
    try:
        for directory in (config.data_root, config.web.scenario_dir, config.data_root / "investigation-cases"):
            _probe_directory(directory)
        for database, table in ((config.web.database, "users"), (config.web.secrets_database, "credentials")):
            # mode=rw prevents a missing database being recreated by a health probe.
            with closing(sqlite3.connect(database.as_uri() + "?mode=rw", uri=True, timeout=0.2)) as connection:
                connection.execute(f"SELECT 1 FROM {table} LIMIT 1")
                connection.execute("BEGIN IMMEDIATE")
                connection.rollback()
        return (config.frontend_root / "index.html").is_file()
    except (OSError, sqlite3.Error):
        return False


def build_application(config=None, *, clock=time.time):
    from poisontrace.bootstrap import build_web_backend, build_accounts
    from poisontrace.interfaces.http.app import create_app
    config = config or RuntimeConfig.from_environment()
    config.validate()
    ensure_data_root(config)
    with runtime_lock(config):
        if (config.data_root / ".restore-pending").exists():
            raise RuntimeError("restore requires operator activation")
        prepare_storage(config)
        backend = build_web_backend(config=replace(config.web, profile=config.profile))
        # Production startup never reads development account seed variables.
        app = create_app(backend, auth_service=build_accounts(config.web.database, seeds=(), clock=clock))
    app.state.runtime_config = config
    lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def runtime_lifespan(app):
        with runtime_lock(config):
            if (config.data_root / ".restore-pending").exists():
                raise RuntimeError("restore requires operator activation")
            async with lifespan(app):
                yield

    app.router.lifespan_context = runtime_lifespan

    @app.get("/health/live", include_in_schema=False)
    def live():
        return {"status": "alive"}

    @app.get("/health/ready", include_in_schema=False)
    def ready():
        available = storage_ready(config)
        return JSONResponse({"status": "ready" if available else "unavailable"}, status_code=200 if available else 503)

    assets = config.frontend_root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith(("api/", "assets/", "health/")):
            raise HTTPException(404, "Not found")
        target = (config.frontend_root / path).resolve()
        if config.frontend_root not in target.parents and target != config.frontend_root:
            raise HTTPException(404, "Not found")
        if target.is_file():
            return FileResponse(target)
        # Missing file requests must not receive HTML with a successful status.
        if Path(path).suffix:
            raise HTTPException(404, "Not found")
        return FileResponse(config.frontend_root / "index.html", headers={"Cache-Control": "no-cache"})

    return app


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PoisonTrace container runtime")
    parser.add_argument("command", choices=("serve", "init-admin", "recover-admin"), default="serve", nargs="?")
    parser.add_argument("--enable-disabled", action="store_true", help="Explicitly re-enable the existing superadmin during recovery")
    args = parser.parse_args()
    if args.enable_disabled and args.command != "recover-admin":
        parser.error("--enable-disabled requires recover-admin")
    if args.command in {"init-admin", "recover-admin"}:
        import getpass
        import warnings
        try:
            config = RuntimeConfig.from_environment()
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                if args.command == "init-admin":
                    username = os.environ.get("POISONTRACE_ADMIN_USERNAME") or input("First admin username: ")
                    passcode = os.environ.get("POISONTRACE_ADMIN_PASSCODE") or getpass.getpass("First admin passcode: ")
                    initialize_admin(config, username, passcode)
                    print("First admin created. Remove bootstrap variables before starting the server.")
                else:
                    username = input("Existing superadmin username: ")
                    passcode = getpass.getpass("New admin passcode: ")
                    if passcode != getpass.getpass("Confirm new admin passcode: "):
                        raise ValueError("passcodes do not match; recovery cancelled")
                    if not config.data_root.is_dir():
                        raise ValueError("existing application state is required")
                    with runtime_lock(config):
                        recover_admin(config, username, passcode, enable_disabled=args.enable_disabled)
                    print("Superadmin recovered. All affected sessions were revoked.")
        except ValueError as exc:
            parser.exit(1, f"{exc}\n")
        except (OSError, sqlite3.Error, RuntimeError):
            parser.exit(1, "Account operation failed; check storage availability and access.\n")
        except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
            parser.exit(1, "Account operation cancelled; a terminal with hidden input is required.\n")
    else:
        import uvicorn
        config = RuntimeConfig.from_environment()
        uvicorn.run(build_application(config), host=config.host, port=config.port, workers=1,
                    proxy_headers=False)


if __name__ == "__main__":
    main()
