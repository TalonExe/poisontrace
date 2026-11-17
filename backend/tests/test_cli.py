from poisontrace.interfaces.cli import main


def test_cli_runs_yaml_scenario(capsys):
    exit_code = main(["run", "backend/tests/fixtures/scenarios/authentication-alert-001.yaml", "--mode", "clean"])

    assert exit_code == 0
    assert "001" in capsys.readouterr().out


def test_cli_runs_poisoned_yaml_scenario(capsys):
    exit_code = main(["run", "backend/tests/fixtures/scenarios/authentication-alert-poisoned-002.yaml", "--mode", "poisoned"])

    assert exit_code == 0
    assert "recommendation_correctness=True" in capsys.readouterr().out


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
    assert "attacker_goal=Not applicable (0/0)" in output
    # Output influence and recommendation correctness coexist with simulated call rejection.
    assert "recommendation_correctness=1.00 (4/4)" in output
    assert "call_rejection=1.00 (4/4)" in output


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
    assert capsys.readouterr().out == "001: mode=clean status=completed marker_influence=False attacker_goal=Unscored recommendation_correctness=True\n"
    assert main(["benchmark", scenario, "--repeated-runs", "0"]) == 0
    output = capsys.readouterr().out
    assert "runs=1 completed=1 failed=0 legacy=0 unscored=0" in output
    assert "attacker_goal=Not applicable (0/0)" in output
    assert "inappropriate_clean_block=0.00 (0/1)" in output
    with pytest.raises(ValueError, match="repeated_runs must not be negative"):
        main(["benchmark", scenario, "--repeated-runs", "-1"])
    for arguments in (["run", scenario, "--model", "unknown"], ["run", scenario, "--mode", "unknown"], []):
        with pytest.raises(SystemExit) as error:
            main(arguments)
        assert error.value.code == 2


def test_cli_does_not_print_sensitive_provider_diagnostics(monkeypatch, capsys):
    from poisontrace import bootstrap
    from poisontrace.adapters.models.fake import FakeModel
    class OfflineGemini(FakeModel):
        raw_response = "synthetic diagnostic"
        def __init__(self, model_name):
            self.model_name = model_name
    monkeypatch.setattr(bootstrap, "GeminiModel", OfflineGemini)
    assert main(["run", "backend/tests/fixtures/scenarios/authentication-alert-001.yaml", "--model", "gemini-3.5-flash-lite"]) == 0
    assert capsys.readouterr().out == "001: mode=clean status=completed marker_influence=False attacker_goal=Unscored recommendation_correctness=True\n"

def test_cli_failures_are_unscored_and_return_nonzero(monkeypatch, capsys):
    from poisontrace.interfaces import cli
    class Failed:
        def respond(self, scenario, tools): raise RuntimeError('synthetic-secret')
    monkeypatch.setattr(cli, 'build_cli_model', lambda name: Failed())
    scenario = 'backend/tests/fixtures/scenarios/authentication-alert-001.yaml'
    assert main(['run', scenario]) == 1
    output = capsys.readouterr().out
    assert 'status=failed' in output
    assert 'attacker_goal=Unscored' in output
    assert 'synthetic-secret' not in output
    assert main(['benchmark', scenario, '--repeated-runs', '0']) == 1
    output = capsys.readouterr().out
    assert 'system_error=1.00 (1/1)' in output
    assert 'recommendation_correctness=Not applicable (0/0)' in output
