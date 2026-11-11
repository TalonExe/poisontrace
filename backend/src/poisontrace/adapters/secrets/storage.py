"""Replaceable secret storage with encrypted local-prototype persistence."""

import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet

from poisontrace.application.ports import CredentialReference, ManagedSecretClient


class ManagedSecretsAdapter:
    """Adapter for a managed secret service supplied by the host application."""

    def __init__(self, *, client: ManagedSecretClient | None = None, put=None, get=None, delete=None) -> None:
        if client is not None:
            put = client.put_secret
            get = client.get_secret
            delete = client.delete_secret
        if not all((put, get, delete)):
            raise ValueError("managed secret client or put, get, and delete callbacks are required")
        self._put = put
        self._get = get
        self._delete = delete
        self._references: dict[str, CredentialReference] = {}

    def save(self, provider: str, secret: str, label: str = "") -> CredentialReference:
        if not secret:
            raise ValueError("secret cannot be empty")
        credential_id = f"cred-{uuid4().hex}"
        self._put(credential_id, provider, label, secret)
        reference = CredentialReference(credential_id, provider, label, EncryptedSqliteSecrets._mask(secret))
        self._references[credential_id] = reference
        return reference

    def retrieve(self, credential_id: str) -> str:
        try:
            return self._get(credential_id)
        except KeyError:
            raise
        except Exception as exc:
            raise KeyError(credential_id) from exc

    def reference(self, credential_id: str) -> CredentialReference:
        try:
            return self._references[credential_id]
        except KeyError:
            raise

    def revoke(self, credential_id: str) -> None:
        try:
            self._delete(credential_id)
        except KeyError:
            raise
        except Exception as exc:
            raise KeyError(credential_id) from exc
        self._references.pop(credential_id, None)

    def list(self) -> list[CredentialReference]:
        return list(reversed(list(self._references.values())))

    def replace(self, credential_id: str, provider: str, secret: str, label: str = "") -> CredentialReference:
        self.reference(credential_id)
        self._put(credential_id, provider, label, secret)
        reference = CredentialReference(credential_id, provider, label, EncryptedSqliteSecrets._mask(secret))
        self._references[credential_id] = reference
        return reference


class EncryptedSqliteSecrets:
    """Local adapter; the encryption key must come from the environment."""

    def __init__(self, database: Path, encryption_key: bytes | None = None) -> None:
        key = encryption_key or os.environ.get("POISONTRACE_SECRETS_KEY", "").encode()
        if not key:
            raise ValueError("POISONTRACE_SECRETS_KEY is required")
        self._cipher = Fernet(key)
        self.database = database
        with sqlite3.connect(database) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS credentials (
                    credential_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    label TEXT NOT NULL,
                    encrypted_secret BLOB NOT NULL
                )"""
            )

    def save(self, provider: str, secret: str, label: str = "") -> CredentialReference:
        if not secret:
            raise ValueError("secret cannot be empty")
        credential_id = f"cred-{uuid4().hex}"
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "INSERT INTO credentials VALUES (?, ?, ?, ?)",
                (credential_id, provider, label, self._cipher.encrypt(secret.encode())),
            )
        return CredentialReference(credential_id, provider, label, self._mask(secret))

    def retrieve(self, credential_id: str) -> str:
        with sqlite3.connect(self.database) as connection:
            row = connection.execute(
                "SELECT encrypted_secret FROM credentials WHERE credential_id = ?",
                (credential_id,),
            ).fetchone()
        if row is None:
            raise KeyError(credential_id)
        return self._cipher.decrypt(row[0]).decode()

    def reference(self, credential_id: str) -> CredentialReference:
        with sqlite3.connect(self.database) as connection:
            row = connection.execute(
                "SELECT provider, label, encrypted_secret FROM credentials WHERE credential_id = ?",
                (credential_id,),
            ).fetchone()
        if row is None:
            raise KeyError(credential_id)
        provider, label, encrypted_secret = row
        return CredentialReference(credential_id, provider, label, self._mask(self._cipher.decrypt(encrypted_secret).decode()))

    def list(self) -> list[CredentialReference]:
        with sqlite3.connect(self.database) as connection:
            rows = connection.execute(
                "SELECT credential_id, provider, label, encrypted_secret FROM credentials ORDER BY rowid DESC"
            ).fetchall()
        return [
            CredentialReference(credential_id, provider, label, self._mask(self._cipher.decrypt(secret).decode()))
            for credential_id, provider, label, secret in rows
        ]

    def replace(self, credential_id: str, provider: str, secret: str, label: str = "") -> CredentialReference:
        self.retrieve(credential_id)
        if not secret:
            raise ValueError("secret cannot be empty")
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE credentials SET provider = ?, label = ?, encrypted_secret = ? WHERE credential_id = ?",
                (provider, label, self._cipher.encrypt(secret.encode()), credential_id),
            )
        return CredentialReference(credential_id, provider, label, self._mask(secret))

    def revoke(self, credential_id: str) -> None:
        with sqlite3.connect(self.database) as connection:
            cursor = connection.execute("DELETE FROM credentials WHERE credential_id = ?", (credential_id,))
        if cursor.rowcount == 0:
            raise KeyError(credential_id)

    @staticmethod
    def _mask(secret: str) -> str:
        return f"{secret[:3]}{'•' * max(4, len(secret) - 7)}{secret[-4:]}" if len(secret) > 7 else "••••••••"
