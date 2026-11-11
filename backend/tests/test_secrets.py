import sqlite3

import pytest
from cryptography.fernet import Fernet

from poisontrace.adapters.secrets.storage import EncryptedSqliteSecrets, ManagedSecretsAdapter


def test_encrypted_secrets_store_returns_reference_and_never_plaintext(tmp_path):
    secret = "sk-test-123456789"
    store = EncryptedSqliteSecrets(tmp_path / "secrets.db", Fernet.generate_key())

    reference = store.save("openai", secret, "Research key")

    assert reference.credential_id.startswith("cred-")
    assert reference.masked != secret
    assert store.retrieve(reference.credential_id) == secret
    with sqlite3.connect(tmp_path / "secrets.db") as connection:
        raw = connection.execute("SELECT encrypted_secret FROM credentials").fetchone()[0]
    assert secret.encode() not in raw


def test_secrets_can_be_rotated_by_replacing_reference(tmp_path):
    store = EncryptedSqliteSecrets(tmp_path / "secrets.db", Fernet.generate_key())
    old = store.save("gemini", "old-secret")
    new = store.save("gemini", "new-secret")
    store.revoke(old.credential_id)

    with pytest.raises(KeyError):
        store.retrieve(old.credential_id)
    assert store.retrieve(new.credential_id) == "new-secret"


def test_secrets_require_an_encryption_key(tmp_path, monkeypatch):
    monkeypatch.delenv("POISONTRACE_SECRETS_KEY", raising=False)
    with pytest.raises(ValueError, match="POISONTRACE_SECRETS_KEY"):
        EncryptedSqliteSecrets(tmp_path / "secrets.db")


def test_list_and_replace_return_only_masked_references(tmp_path):
    store = EncryptedSqliteSecrets(tmp_path / "secrets.db", Fernet.generate_key())
    reference = store.save("openai", "old-secret", "primary")
    replaced = store.replace(reference.credential_id, "openai", "new-secret", "rotated")

    assert replaced.credential_id == reference.credential_id
    assert replaced.masked != "new-secret"
    assert store.list() == [replaced]


def test_managed_secret_adapter_delegates_secret_operations_without_exposing_values():
    values = {}

    def put(credential_id, provider, label, secret):
        values[credential_id] = (provider, label, secret)

    def get(credential_id):
        return values[credential_id][2]

    def delete(credential_id):
        del values[credential_id]

    store = ManagedSecretsAdapter(put=put, get=get, delete=delete)
    reference = store.save("openai", "sk-managed-secret", "managed")

    assert reference.credential_id.startswith("cred-")
    assert reference.masked != "sk-managed-secret"
    assert store.retrieve(reference.credential_id) == "sk-managed-secret"
    store.revoke(reference.credential_id)
    with pytest.raises(KeyError):
        store.retrieve(reference.credential_id)


def test_managed_secret_adapter_can_be_wired_to_an_application_client():
    class Client:
        def __init__(self):
            self.values = {}

        def put_secret(self, credential_id, provider, label, secret):
            self.values[credential_id] = (provider, label, secret)

        def get_secret(self, credential_id):
            return self.values[credential_id][2]

        def delete_secret(self, credential_id):
            del self.values[credential_id]

    client = Client()
    store = ManagedSecretsAdapter(client=client)

    reference = store.save("gemini", "gemini-managed-secret", "Research")

    assert store.retrieve(reference.credential_id) == "gemini-managed-secret"
    assert client.values[reference.credential_id][:2] == ("gemini", "Research")
