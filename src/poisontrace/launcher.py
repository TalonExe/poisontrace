"""Launch the PoisonTrace API and dashboard development server together."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Iterable


def python_executable(project_root: Path) -> Path:
    relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    return project_root / ".venv" / relative


def npm_executable() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def validate_environment(project_root: Path, *, node_path: str | None = None, npm_path: str | None = None) -> list[str]:
    errors: list[str] = []
    if not python_executable(project_root).is_file():
        errors.append(f"Python virtual environment not found at {python_executable(project_root)}. Create .venv first.")
    if not (project_root / "frontend" / "package.json").is_file():
        errors.append("Frontend package manifest is missing at frontend/package.json.")
    if not (project_root / "frontend" / "node_modules").is_dir():
        errors.append("Frontend dependencies are missing. Run `npm install` in frontend/.")
    if node_path is None and shutil.which("node") is None:
        errors.append("Node.js is unavailable. Install Node.js or activate the configured NVM version.")
    if npm_path is None and shutil.which(npm_executable()) is None:
        errors.append("npm is unavailable. Install Node.js or activate the configured NVM version.")
    if not os.environ.get("POISONTRACE_SECRETS_KEY"):
        errors.append("POISONTRACE_SECRETS_KEY is missing. Set it before launching the local web app.")
    return errors


def commands(project_root: Path) -> tuple[list[str], list[str]]:
    backend = [str(python_executable(project_root)), "-m", "uvicorn", "poisontrace.web:app", "--host", "127.0.0.1", "--port", "8000"]
    frontend = [npm_executable(), "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"]
    return backend, frontend


def stop_processes(processes: Iterable[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    errors = validate_environment(project_root)
    if errors:
        print("PoisonTrace cannot start:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    backend_command, frontend_command = commands(project_root)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(project_root / "src") + os.pathsep + environment.get("PYTHONPATH", "")
    processes: list[subprocess.Popen] = []
    try:
        print("Starting API at http://127.0.0.1:8000", flush=True)
        processes.append(subprocess.Popen(backend_command, cwd=project_root, env=environment))
        print("Starting dashboard at http://127.0.0.1:5173", flush=True)
        processes.append(subprocess.Popen(frontend_command, cwd=project_root / "frontend", env=environment))
        for process in processes:
            process.wait()
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        stop_processes(processes)
