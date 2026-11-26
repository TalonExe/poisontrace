"""The acceptance runner must use the selected engine without Docker fallback."""
import importlib.util
from pathlib import Path
import subprocess

import pytest


def test_build_context_contains_only_required_sources(tmp_path):
    path = Path(__file__).resolve().parents[2] / "scripts/verify_container.py"
    spec = importlib.util.spec_from_file_location("container_verification", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    project = tmp_path / "project"
    expected = ["Dockerfile", ".dockerignore", "pyproject.toml", "requirements-runtime.lock",
                "frontend/package.json", "frontend/package-lock.json", "frontend/index.html", "frontend/vite.config.js",
                "frontend/src/main.jsx", "backend/src/poisontrace/__init__.py",
                "backend/src/poisontrace/adapters/mcp/corpus/synthetic.json"]
    for name in expected + [".scratch/private/sentinel.txt", "debug.log", "poisontrace.db", "frontend/debug.log",
                            "frontend/src/.env", "backend/src/poisontrace/__pycache__/cached.pyc"]:
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("synthetic sentinel")
    destination = tmp_path / "context"
    runner.stage_build_context(project, destination)
    assert sorted(str(p.relative_to(destination)).replace("\\", "/") for p in destination.rglob("*") if p.is_file()) == sorted(expected)
    assert (project / ".scratch/private/sentinel.txt").read_text() == "synthetic sentinel"


@pytest.mark.parametrize("engine", ["docker", "podman"])
def test_selected_engine_performs_linux_probe_and_fresh_build(engine):
    path = Path(__file__).resolve().parents[2] / "scripts/verify_container.py"
    spec = importlib.util.spec_from_file_location("container_verification", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[1] == "info":
            return subprocess.CompletedProcess(command, 0, stdout="linux\n", stderr="")
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="synthetic build failure")

    with pytest.raises(RuntimeError, match=f"{engine} check failed: build.*synthetic build failure"):
        runner.main(["--engine", engine], run=run)
    assert len(calls) == 2 and all(command[0] == engine for command in calls)
    assert "--no-cache" in calls[1]
    if engine == "podman":
        assert calls[1][calls[1].index("--format") + 1] == "docker"
