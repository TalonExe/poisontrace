from poisontrace.web_adapter import RunWebAdapter
from poisontrace.secrets import EncryptedSqliteSecrets
from cryptography.fernet import Fernet


def test_web_adapter_runs_and_lists_persisted_results(tmp_path):
    adapter = RunWebAdapter(tmp_path / "scenarios", tmp_path / "runs.db")
    (tmp_path / "scenarios").mkdir()
    source = __import__("pathlib").Path("scenarios/authentication-alert.yaml")
    (tmp_path / "scenarios/authentication-alert.yaml").write_text(
        source.read_text(encoding="utf-8"), encoding="utf-8"
    )

    created = adapter.create_run(
        {
            "session_id": "session-1",
            "scenario_id": "authentication-alert",
            "mode": "defended",
            "provider": "fake",
        }
    )

    assert created["id"] == "EXP-001"
    assert created["mode"] == "Defended"
    assert adapter.list_runs() == [created]
    assert adapter.store.result_for(1).run_configuration["session_id"] == "session-1"


def test_web_adapter_rejects_unknown_provider(tmp_path):
    adapter = RunWebAdapter(tmp_path, tmp_path / "runs.db")
    try:
        adapter.create_run({"provider": "local"})
    except ValueError as error:
        assert "unsupported provider" in str(error)
    else:
        raise AssertionError("unknown provider was accepted")


def test_web_adapter_rejects_unknown_credential_reference(tmp_path):
    adapter = RunWebAdapter(tmp_path, tmp_path / "runs.db")
    try:
        adapter.create_run({"provider": "fake", "credential_id": "cred-missing"})
    except ValueError as error:
        assert "credential storage" in str(error)
    else:
        raise AssertionError("unknown credential reference was accepted")


def test_web_adapter_rejects_credential_for_the_wrong_provider(tmp_path):
    secrets = EncryptedSqliteSecrets(tmp_path / "secrets.db", Fernet.generate_key())
    reference = secrets.save("openai", "sk-test-secret", "OpenAI")
    adapter = RunWebAdapter(tmp_path, tmp_path / "runs.db", secrets)

    try:
        adapter.create_run({"provider": "gemini", "credential_id": reference.credential_id})
    except ValueError as error:
        assert "provider" in str(error)
    else:
        raise AssertionError("a credential for another provider was accepted")
