"""Exercise credential behavior without a web adapter or HTTP application."""

import pytest
from cryptography.fernet import Fernet

from poisontrace.application.credentials import CredentialApplicationService
from poisontrace.adapters.secrets.storage import EncryptedSqliteSecrets, ManagedSecretsAdapter


@pytest.fixture(params=["encrypted", "managed"])
def storage(request, tmp_path):
    if request.param == "encrypted":
        return EncryptedSqliteSecrets(tmp_path / "secrets.db", Fernet.generate_key())
    values = {}
    return ManagedSecretsAdapter(
        put=lambda credential_id, provider, label, secret: values.__setitem__(credential_id, secret),
        get=lambda credential_id: values[credential_id],
        delete=lambda credential_id: values.pop(credential_id),
    )


def test_credential_module_owns_masked_lifecycle_for_both_adapters(storage):
    credentials = CredentialApplicationService(storage)
    saved = credentials.save({"provider": "openai", "secret": "synthetic-first-key", "label": "research"})
    credential_id = saved["credential_id"]
    assert set(saved) == {"credential_id", "provider", "label", "masked"}
    assert "synthetic-first-key" not in str(saved)
    assert credentials.list() == [saved]

    replaced = credentials.replace(credential_id, {"provider": "gemini", "secret": "synthetic-second-key"})
    assert replaced["credential_id"] == credential_id
    assert replaced["provider"] == "gemini"
    assert replaced["label"] == ""
    assert "synthetic-second-key" not in str(replaced)
    assert storage.retrieve(credential_id) == "synthetic-second-key"
    assert credentials.test(credential_id) == {"credential_id": credential_id, "ok": True}
    assert credentials.revoke(credential_id) == {"credential_id": credential_id, "revoked": True}
    assert credentials.list() == []
    with pytest.raises(KeyError):
        credentials.test(credential_id)
    with pytest.raises(KeyError):
        credentials.replace(credential_id, {"provider": "gemini", "secret": "replacement"})
    with pytest.raises(KeyError):
        credentials.revoke(credential_id)


@pytest.mark.parametrize("operation,error", [
    (lambda module: module.list(), RuntimeError),
    (lambda module: module.save({"provider": "openai", "secret": "key"}), ValueError),
    (lambda module: module.replace("missing", {"provider": "openai", "secret": "key"}), ValueError),
    (lambda module: module.test("missing"), RuntimeError),
    (lambda module: module.revoke("missing"), RuntimeError),
])
def test_missing_storage_preserves_exception_contract(operation, error):
    with pytest.raises(error, match="credential storage is not configured"):
        operation(CredentialApplicationService(None))
