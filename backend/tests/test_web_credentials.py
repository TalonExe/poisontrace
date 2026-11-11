from cryptography.fernet import Fernet

from poisontrace.adapters.secrets.storage import EncryptedSqliteSecrets
from poisontrace.bootstrap import build_backend
from poisontrace.config import WebConfig


def test_web_credential_operations_never_return_plaintext(tmp_path):
    secrets = EncryptedSqliteSecrets(tmp_path / "secrets.db", Fernet.generate_key())
    backend = build_backend(WebConfig(scenario_dir=tmp_path, database=tmp_path / "runs.db"), secrets)

    saved = backend.credentials.save({"provider": "openai", "label": "research", "secret": "sk-super-secret"})
    replaced = backend.credentials.replace(saved["credential_id"], {"provider": "openai", "secret": "sk-rotated-secret"})

    assert "secret" not in saved
    assert "sk-super-secret" not in str(saved)
    assert "sk-rotated-secret" not in str(replaced)
    assert secrets.retrieve(saved["credential_id"]) == "sk-rotated-secret"

    assert backend.secrets.list()[0].credential_id == saved["credential_id"]


def test_web_factory_wires_an_application_managed_secret_client(tmp_path, monkeypatch):
    class Client:
        def __init__(self):
            self.values = {}

        def put_secret(self, credential_id, provider, label, secret):
            self.values[credential_id] = (provider, label, secret)

        def get_secret(self, credential_id):
            return self.values[credential_id][2]

        def delete_secret(self, credential_id):
            del self.values[credential_id]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("POISONTRACE_SECRETS_KEY", Fernet.generate_key().decode())
    from poisontrace.bootstrap import build_web_backend

    client = Client()
    backend = build_web_backend(managed_secret_client=client)

    saved = backend.credentials.save({"provider": "gemini", "label": "managed", "secret": "gemini-secret"})

    assert saved["masked"] != "gemini-secret"
    assert "gemini-secret" not in str(saved)
    assert client.values[saved["credential_id"]][2] == "gemini-secret"


def test_credential_http_lifecycle_preserves_masking_and_error_mapping(tmp_path, analyst_client):
    from poisontrace.bootstrap import create_app

    secrets = EncryptedSqliteSecrets(tmp_path / "secrets.db", Fernet.generate_key())
    client = analyst_client(create_app(build_backend(WebConfig(scenario_dir=tmp_path, database=tmp_path / "runs.db"), secrets)))
    response = client.post("/api/credentials", json={"provider": "openai", "secret": "synthetic-first-key"})
    assert response.status_code == 200
    saved = response.json()
    credential_id = saved["credential_id"]
    assert set(saved) == {"credential_id", "provider", "label", "masked"}
    assert "synthetic-first-key" not in response.text
    assert client.get("/api/credentials").json() == [saved]

    response = client.put(f"/api/credentials/{credential_id}", json={"provider": "gemini", "secret": "synthetic-second-key", "label": "rotated"})
    assert response.status_code == 200
    assert response.json()["provider"] == "gemini"
    assert response.json()["label"] == "rotated"
    assert "synthetic-second-key" not in response.text
    assert client.post(f"/api/credentials/{credential_id}/test").json() == {"credential_id": credential_id, "ok": True}
    assert client.delete(f"/api/credentials/{credential_id}").json() == {"credential_id": credential_id, "revoked": True}
    assert client.get("/api/credentials").json() == []
    assert client.post(f"/api/credentials/{credential_id}/test").status_code == 404
    assert client.delete(f"/api/credentials/{credential_id}").status_code == 404
    assert client.put(f"/api/credentials/{credential_id}", json={"provider": "openai", "secret": "replacement"}).status_code == 400
    assert client.post("/api/credentials", json={"provider": "openai", "secret": ""}).status_code == 400


def test_credential_http_missing_storage_preserves_operation_statuses(tmp_path, analyst_client):
    from poisontrace.bootstrap import create_app

    client = analyst_client(create_app(build_backend(WebConfig(scenario_dir=tmp_path, database=tmp_path / "runs.db"))))
    payload = {"provider": "openai", "secret": "synthetic-key"}
    for method, path, body, status in (
        ("GET", "/api/credentials", None, 503),
        ("POST", "/api/credentials", payload, 400),
        ("PUT", "/api/credentials/missing", payload, 400),
        ("POST", "/api/credentials/missing/test", None, 503),
        ("DELETE", "/api/credentials/missing", None, 503),
    ):
        response = client.request(method, path, json=body)
        assert response.status_code == status
        assert response.json() == {"detail": "credential storage is not configured"}
