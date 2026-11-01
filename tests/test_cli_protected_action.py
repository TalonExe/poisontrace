from poisontrace import cli
from poisontrace.cli import main


def test_cli_blocks_protected_action_without_approval(monkeypatch, capsys):
    class ProtectedActionModel:
        model_name = "fake"
        prompt_version = "test"

        def respond(self, scenario, tools):
            from poisontrace.domain import AgentDecision, ToolCall

            return AgentDecision(ToolCall("disable_account", {"account_id": "acct-001"}), "escalate")

    monkeypatch.setattr(cli, "FakeModel", ProtectedActionModel)

    assert main(["run", "scenarios/protected-action.yaml"]) == 0
    assert "benign_success=False" in capsys.readouterr().out


def test_cli_executes_protected_action_after_approval(monkeypatch, capsys):
    class ProtectedActionModel:
        model_name = "fake"
        prompt_version = "test"

        def respond(self, scenario, tools):
            from poisontrace.domain import AgentDecision, ToolCall

            return AgentDecision(ToolCall("disable_account", {"account_id": "acct-001"}), "escalate")

    monkeypatch.setattr(cli, "FakeModel", ProtectedActionModel)

    assert main(["run", "scenarios/protected-action.yaml", "--approval-actor", "cli-analyst"]) == 0
    assert "benign_success=True" in capsys.readouterr().out
