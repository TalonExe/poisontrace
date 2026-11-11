from poisontrace.interfaces.cli import main
from poisontrace.interfaces import cli


def test_cli_runs_yaml_scenario(capsys):
    exit_code = main(["run", "backend/tests/fixtures/scenarios/authentication-alert-001.yaml", "--mode", "clean"])

    assert exit_code == 0
    assert "001" in capsys.readouterr().out


def test_cli_runs_poisoned_yaml_scenario(capsys):
    exit_code = main(["run", "backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml", "--mode", "poisoned"])

    assert exit_code == 0
    assert "benign_success=False" in capsys.readouterr().out


def test_cli_benchmarks_yaml_scenario(capsys):
    exit_code = main(
        [
            "benchmark",
            "backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml",
            "--mode",
            "defended",
            "--repeated-runs",
            "3",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "runs=4" in output
    assert "attack_success_rate=0.00" in output
    # The gateway blocks execution, but cannot erase the marker already emitted by FakeModel.
    assert "benign_task_success_rate=0.00" in output
    assert "defence_blocking_rate=0.00" in output


def test_cli_defaults_to_fake_model(capsys):
    exit_code = main(["run", "backend/tests/fixtures/scenarios/authentication-alert-001.yaml", "--model", "fake"])

    assert exit_code == 0
    assert "001" in capsys.readouterr().out


def test_cli_exposes_openai_model_selection(monkeypatch, capsys):
    class OfflineOpenAIModel:
        model_name = "gpt-5-mini"
        prompt_version = "test"

        def __init__(self, model_name="gpt-5-mini"):
            self.model_name = model_name

        def respond(self, scenario, tools):
            from poisontrace.adapters.models.fake import FakeModel
            return FakeModel().respond(scenario, tools)

    monkeypatch.setattr("poisontrace.bootstrap.OpenAIModel", OfflineOpenAIModel)
    exit_code = main(["run", "backend/tests/fixtures/scenarios/authentication-alert-001.yaml", "--model", "gpt-5-mini"])

    assert exit_code == 0
    assert "001" in capsys.readouterr().out



def test_cli_exact_output_and_argument_errors(capsys):
    import pytest
    scenario = "backend/tests/fixtures/scenarios/authentication-alert-001.yaml"
    assert main(["run", scenario]) == 0
    assert capsys.readouterr().out == "001: mode=clean benign_success=True attack_success=False\n"
    assert main(["benchmark", scenario, "--repeated-runs", "0"]) == 0
    assert capsys.readouterr().out == "001: mode=clean runs=1 attack_success_rate=0.00 benign_task_success_rate=1.00 defence_blocking_rate=0.00 false_positive_rate=0.00\n"
    with pytest.raises(ValueError, match="repeated_runs must not be negative"):
        main(["benchmark", scenario, "--repeated-runs", "-1"])
    for arguments in (["run", scenario, "--model", "unknown"], ["run", scenario, "--mode", "unknown"], []):
        with pytest.raises(SystemExit) as error:
            main(arguments)
        assert error.value.code == 2


def test_cli_gemini_diagnostic_output_is_preserved(monkeypatch, capsys):
    from poisontrace import bootstrap
    from poisontrace.adapters.models.fake import FakeModel
    class OfflineGemini(FakeModel):
        raw_response = "synthetic diagnostic"
        def __init__(self, model_name):
            self.model_name = model_name
    monkeypatch.setattr(cli, "GeminiModel", OfflineGemini)
    monkeypatch.setattr(bootstrap, "GeminiModel", OfflineGemini)
    assert main(["run", "backend/tests/fixtures/scenarios/authentication-alert-001.yaml", "--model", "gemini-3.5-flash-lite"]) == 0
    assert capsys.readouterr().out == "gemini_raw_response=synthetic diagnostic\n001: mode=clean benign_success=True attack_success=False\n"
