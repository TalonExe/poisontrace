"""CLI composition preserves its two execution policies and per-trial state."""
from pathlib import Path

import pytest

from poisontrace.adapters.models.fake import FakeModel
from poisontrace.bootstrap import build_cli_model, build_cli_runner, build_cli_benchmark
from poisontrace.domain import AgentDecision, ExperimentMode, ToolCall
from poisontrace.adapters.scenarios.loader import load_scenario


class ProtectedActionModel:
    model_name = "fake"
    prompt_version = "test"
    def respond(self, scenario, tools):
        return AgentDecision(ToolCall("disable_account", {"account_id": "acct-001"}), "escalate")


@pytest.mark.parametrize("actor,success", [(None, False), ("cli-analyst", True)])
def test_cli_runner_applies_protected_tool_approval(actor, success):
    scenario = load_scenario(Path("backend/tests/fixtures/scenarios/protected-action-004.yaml"))
    calls = []
    def factory(name):
        calls.append(name)
        return ProtectedActionModel()
    runner = build_cli_runner(scenario, ExperimentMode.CLEAN, "fake", actor, model_factory=factory)
    result = runner.run(scenario, ExperimentMode.CLEAN)
    assert result.benign_task_success is success
    assert calls == ["fake"]


@pytest.mark.parametrize("mode,tool_status", [(ExperimentMode.POISONED, "Executed"), (ExperimentMode.DEFENDED, "Blocked")])
def test_cli_runner_preserves_manifest_policy(mode, tool_status):
    scenario = load_scenario(Path("backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml"))
    result = build_cli_runner(scenario, mode).run(scenario, mode)
    assert result.attack_success
    assert result.tool_call_status == tool_status


def test_cli_benchmark_preserves_empty_high_impact_policy_and_fresh_trials():
    scenario = load_scenario(Path("backend/tests/fixtures/scenarios/protected-action-004.yaml"))
    models = []
    def factory(name):
        model = ProtectedActionModel()
        models.append(model)
        return model
    benchmark = build_cli_benchmark(scenario, ExperimentMode.CLEAN, "fake", model_factory=factory)
    results = benchmark.run(scenario, ExperimentMode.CLEAN, 3)
    assert len(results) == 4
    assert len({id(model) for model in models}) == 4
    assert all(result.benign_task_success for result in results)
    first = benchmark.scenario_runner_factory()
    second = benchmark.scenario_runner_factory()
    assert first.trace_store is not second.trace_store
    assert first.trace_store.events == second.trace_store.events == []
    with pytest.raises(ValueError, match="repeated_runs must not be negative"):
        benchmark.run(scenario, ExperimentMode.CLEAN, -1)
    assert len(models) == 6


def test_cli_model_selection_preserves_supported_names_and_environment_key_fallback(monkeypatch):
    from poisontrace import bootstrap
    calls = []
    def construct(*, model_name):
        calls.append(model_name)
        return FakeModel()
    monkeypatch.setattr(bootstrap, "OpenAIModel", construct)
    monkeypatch.setattr(bootstrap, "GeminiModel", construct)
    assert isinstance(build_cli_model("fake"), FakeModel)
    build_cli_model("gemini-3.5-flash-lite")
    build_cli_model("gpt-5-mini")
    assert calls == ["gemini-3.5-flash-lite", "gpt-5-mini"]
    with pytest.raises(ValueError, match="unsupported model: unknown"):
        build_cli_model("unknown")


@pytest.mark.parametrize("command", ["run", "benchmark"])
def test_module_entrypoint_needs_no_web_secrets_or_authentication(tmp_path, command):
    import os
    import subprocess
    import sys
    environment = os.environ.copy()
    environment.pop("POISONTRACE_SECRETS_KEY", None)
    environment["PYTHONPATH"] = str(Path("backend/src").resolve())
    scenario = str(Path("backend/tests/fixtures/scenarios/authentication-alert-001.yaml").resolve())
    script = """
import importlib.abc
import runpy
import sys
class NoWebDependencies(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {"poisontrace.web", "poisontrace.adapters.secrets", "poisontrace.application.accounts", "poisontrace.adapters.persistence.accounts", "fastapi", "cryptography"}:
            raise AssertionError("CLI imported web dependency: " + fullname)
sys.meta_path.insert(0, NoWebDependencies())
sys.argv = ["poisontrace", sys.argv[1], sys.argv[2]]
runpy.run_module("poisontrace", run_name="__main__")
"""
    result = subprocess.run([sys.executable, "-c", script, command, scenario], cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    if command == "run":
        assert result.stdout == "001: mode=clean benign_success=True attack_success=False\n"
    else:
        assert result.stdout == "001: mode=clean runs=4 attack_success_rate=0.00 benign_task_success_rate=1.00 defence_blocking_rate=0.00 false_positive_rate=0.00\n"
    assert list(tmp_path.iterdir()) == []
