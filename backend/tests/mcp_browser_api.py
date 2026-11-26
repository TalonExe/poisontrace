"""Isolated offline browser-test API. Never opens the application databases."""
from pathlib import Path
import os
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from poisontrace.bootstrap import build_backend, build_accounts
from poisontrace.config import AccountSeed, WebConfig
from poisontrace.interfaces.http.app import create_app
import uvicorn


if __name__ == "__main__":
    scratch = Path(os.environ['POISONTRACE_VERIFY_STATE']) if os.environ.get('POISONTRACE_VERIFY_STATE') else Path(__file__).resolve().parents[2] / ".scratch" / "mcp-browser"
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="offline-", dir=scratch) as directory:
        root = Path(directory)
        config = WebConfig(scenario_dir=root / "empty-scenarios", database=root / "synthetic.db")
        backend = build_backend(config)
        auth = build_accounts(config.database, seeds=(AccountSeed("browser-researcher", "analyst", "synthetic-browser-test"),))
        app = create_app(backend, auth_service=auth)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=4175, log_level="error", timeout_graceful_shutdown=5))

        @app.post("/__test_shutdown")
        def shutdown():
            server.should_exit = True
            return {"stopping": True}

        server.run()
        # Release SQLite connection cycles before Windows directory cleanup.
        import gc
        gc.collect()
