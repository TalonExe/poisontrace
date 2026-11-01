from pathlib import Path
import shutil

from poisontrace.launcher import commands, validate_environment


def test_launcher_builds_backend_and_frontend_commands(tmp_path, monkeypatch):
    (tmp_path / ".venv" / "Scripts").mkdir(parents=True)
    (tmp_path / ".venv" / "Scripts" / "python.exe").touch()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "package.json").write_text("{}")
    (tmp_path / "frontend" / "node_modules").mkdir()
    monkeypatch.setenv("POISONTRACE_SECRETS_KEY", "test-key")
    backend, frontend = commands(tmp_path)

    assert backend[1:4] == ["-m", "uvicorn", "poisontrace.web:app"]
    assert frontend[1:3] == ["run", "dev"]


def test_launcher_reports_missing_runtime_requirements(tmp_path, monkeypatch):
    monkeypatch.delenv("POISONTRACE_SECRETS_KEY", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _: None)
    errors = validate_environment(tmp_path)

    assert any("virtual environment" in error for error in errors)
    assert any("package manifest" in error for error in errors)
    assert any("Node.js" in error for error in errors)
    assert any("npm" in error for error in errors)
    assert any("POISONTRACE_SECRETS_KEY" in error for error in errors)
