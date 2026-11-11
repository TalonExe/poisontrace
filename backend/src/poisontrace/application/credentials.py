"""Credential operations and masked results, independent of HTTP and storage."""

from poisontrace.application.contracts import CredentialResponse, CredentialWriteRequest
from poisontrace.application.ports import CredentialReference, SecretsAdapter


class CredentialApplicationService:
    def __init__(self, secrets: SecretsAdapter | None) -> None:
        self._secrets = secrets

    def _storage(self) -> SecretsAdapter:
        if self._secrets is None:
            raise RuntimeError("credential storage is not configured")
        return self._secrets

    def _write_storage(self) -> SecretsAdapter:
        # Preserve the existing write rejection contract used by HTTP callers.
        if self._secrets is None:
            raise ValueError("credential storage is not configured")
        return self._secrets

    @staticmethod
    def _response(reference: CredentialReference) -> CredentialResponse:
        return {
            "credential_id": reference.credential_id,
            "provider": reference.provider,
            "label": reference.label,
            "masked": reference.masked,
        }

    def list(self) -> list[CredentialResponse]:
        return [self._response(item) for item in self._storage().list()]

    def save(self, payload: CredentialWriteRequest) -> CredentialResponse:
        storage = self._write_storage()
        return self._response(storage.save(payload["provider"], payload["secret"], payload.get("label", "")))

    def replace(self, credential_id: str, payload: CredentialWriteRequest) -> CredentialResponse:
        storage = self._write_storage()
        return self._response(storage.replace(credential_id, payload["provider"], payload["secret"], payload.get("label", "")))

    def test(self, credential_id: str) -> dict[str, str | bool]:
        # This checks stored-key retrieval, not a request to the model provider.
        self._storage().retrieve(credential_id)
        return {"credential_id": credential_id, "ok": True}

    def revoke(self, credential_id: str) -> dict[str, str | bool]:
        self._storage().revoke(credential_id)
        return {"credential_id": credential_id, "revoked": True}
