from poisontrace.cli import main


def test_cli_runs_yaml_scenario(capsys):
    exit_code = main(["run", "scenarios/authentication-alert.yaml", "--mode", "clean"])

    assert exit_code == 0
    assert "authentication-alert-001" in capsys.readouterr().out


def test_cli_runs_poisoned_yaml_scenario(capsys):
    exit_code = main(["run", "scenarios/authentication-alert-poisoned.yaml", "--mode", "poisoned"])

    assert exit_code == 0
    assert "benign_success=False" in capsys.readouterr().out


def test_cli_benchmarks_yaml_scenario(capsys):
    exit_code = main(
        [
            "benchmark",
            "scenarios/authentication-alert-poisoned.yaml",
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
    assert "benign_task_success_rate=1.00" in output


def test_cli_defaults_to_fake_model(capsys):
    exit_code = main(["run", "scenarios/authentication-alert.yaml", "--model", "fake"])

    assert exit_code == 0
    assert "authentication-alert-001" in capsys.readouterr().out
