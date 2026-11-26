"""Replaceable secret storage with encrypted local-prototype persistence."""

import os
import sqlite3
from hashlib import sha256

from poisontrace.adapters.persistence.recovery_ledger import RecoveryLedger
from pathlib import Path
from threading import RLock
from uuid import uuid4

from cryptography.fernet import Fernet

from poisontrace.application.ports import CredentialReference, ManagedSecretClient
from poisontrace.application.principals import analyst_owner_id, require_analyst_owner, CredentialNotFound


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
        self._owners: dict[str, int] = {}
        self._lock = RLock()

    def save(self, provider: str, secret: str, label: str = "") -> CredentialReference:
        with self._lock:
            owner = require_analyst_owner()
            if not secret:
                raise ValueError("secret cannot be empty")
            credential_id = f"cred-{uuid4().hex}"
            try:
                self._put(credential_id, provider, label, secret)
            except Exception:
                raise ValueError("credential storage unavailable") from None
            reference = CredentialReference(credential_id, provider, label, EncryptedSqliteSecrets._mask(secret))
            self._references[credential_id] = reference
            self._owners[credential_id] = owner
            return reference

    def retrieve(self, credential_id: str) -> str:
        with self._lock:
            self.reference(credential_id)
            try:
                return self._get(credential_id)
            except Exception:
                raise CredentialNotFound("credential not found") from None

    def reference(self, credential_id: str) -> CredentialReference:
        with self._lock:
            owner = require_analyst_owner()
            if self._owners.get(credential_id) != owner:
                raise CredentialNotFound('credential not found')
            return self._references[credential_id]

    def revoke(self, credential_id: str) -> None:
        with self._lock:
            self.reference(credential_id)
            try:
                self._delete(credential_id)
            except Exception:
                raise CredentialNotFound("credential not found") from None
            self._references.pop(credential_id, None)
            self._owners.pop(credential_id, None)

    def list(self) -> list[CredentialReference]:
        with self._lock:
            return [item for item in reversed(list(self._references.values())) if self._owners[item.credential_id] == analyst_owner_id()]

    def replace(self, credential_id: str, provider: str, secret: str, label: str = "") -> CredentialReference:
        with self._lock:
            self.reference(credential_id)
            if not secret:
                raise ValueError("secret cannot be empty")
            try:
                self._put(credential_id, provider, label, secret)
            except Exception:
                raise ValueError("credential storage unavailable") from None
            reference = CredentialReference(credential_id, provider, label, EncryptedSqliteSecrets._mask(secret))
            self._references[credential_id] = reference
            return reference

class EncryptedSqliteSecrets:
    """Local adapter; the encryption key must come from the environment."""

    def __init__(self, database: Path, encryption_key: bytes | None = None, *, recovery_ledger: Path | None = None) -> None:
        key = encryption_key or os.environ.get("POISONTRACE_SECRETS_KEY", "").encode()
        if not key:
            raise ValueError("POISONTRACE_SECRETS_KEY is required")
        self._cipher = Fernet(key)
        self.database = database
        self.ledger = None
        with sqlite3.connect(database) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS credentials (
                    credential_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    label TEXT NOT NULL,
                    encrypted_secret BLOB NOT NULL
                )"""
            )
            # Additive migration: NULL owners are quarantined, never adopted at login.
            columns = {row[1] for row in connection.execute("PRAGMA table_info(credentials)")}
            if "owner_id" not in columns:
                connection.execute("ALTER TABLE credentials ADD COLUMN owner_id INTEGER")
            connection.execute("CREATE INDEX IF NOT EXISTS credentials_owner ON credentials(owner_id)")
            enrolled = connection.execute("SELECT 1 FROM sqlite_master WHERE name='recovery_identity'").fetchone()
        if enrolled and recovery_ledger is None:
            raise ValueError("an enrolled application requires its independent recovery ledger")
        if recovery_ledger is not None:
            self.ledger = RecoveryLedger(recovery_ledger, database, self._cipher, create=True)

    def _available(self, token):
        return self.ledger is None or sha256(token).hexdigest() not in self.ledger.revoked()

    def save(self, provider: str, secret: str, label: str = "") -> CredentialReference:
        owner = require_analyst_owner()
        if not secret:
            raise ValueError("secret cannot be empty")
        credential_id = f"cred-{uuid4().hex}"
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "INSERT INTO credentials (credential_id, provider, label, encrypted_secret, owner_id) VALUES (?, ?, ?, ?, ?)",
                (credential_id, provider, label, self._cipher.encrypt(secret.encode()), owner),
            )
        return CredentialReference(credential_id, provider, label, self._mask(secret))

    def retrieve(self, credential_id: str) -> str:
        with sqlite3.connect(self.database) as connection:
            row = connection.execute(
                "SELECT encrypted_secret FROM credentials WHERE credential_id = ? AND owner_id = ?",
                (credential_id, require_analyst_owner()),
            ).fetchone()
        if row is None or not self._available(row[0]):
            raise CredentialNotFound("credential not found")
        return self._cipher.decrypt(row[0]).decode()

    def reference(self, credential_id: str) -> CredentialReference:
        with sqlite3.connect(self.database) as connection:
            row = connection.execute(
                "SELECT provider, label, encrypted_secret FROM credentials WHERE credential_id = ? AND owner_id = ?",
                (credential_id, require_analyst_owner()),
            ).fetchone()
        if row is None:
            raise CredentialNotFound("credential not found")
        provider, label, encrypted_secret = row
        if not self._available(encrypted_secret):
            raise CredentialNotFound("credential not found")
        return CredentialReference(credential_id, provider, label, self._mask(self._cipher.decrypt(encrypted_secret).decode()))

    def list(self) -> list[CredentialReference]:
        with sqlite3.connect(self.database) as connection:
            rows = connection.execute(
                "SELECT credential_id, provider, label, encrypted_secret FROM credentials WHERE owner_id = ? ORDER BY rowid DESC",
                (analyst_owner_id(),)
            ).fetchall()
        revoked = self.ledger.revoked() if self.ledger is not None else set()
        return [
            CredentialReference(credential_id, provider, label, self._mask(self._cipher.decrypt(secret).decode()))
            for credential_id, provider, label, secret in rows if sha256(secret).hexdigest() not in revoked
        ]

    def replace(self, credential_id: str, provider: str, secret: str, label: str = "") -> CredentialReference:
        if not secret:
            raise ValueError("secret cannot be empty")
        with sqlite3.connect(self.database) as connection:
            connection.execute("BEGIN IMMEDIATE")
            owner = require_analyst_owner()
            self._record_removal(connection, credential_id, owner)
            connection.execute(
                "UPDATE credentials SET provider = ?, label = ?, encrypted_secret = ? WHERE credential_id = ? AND owner_id = ?",
                (provider, label, self._cipher.encrypt(secret.encode()), credential_id, owner),
            )
        return CredentialReference(credential_id, provider, label, self._mask(secret))

    def revoke(self, credential_id: str) -> None:
        with sqlite3.connect(self.database) as connection:
            connection.execute("BEGIN IMMEDIATE")
            owner = require_analyst_owner()
            self._record_removal(connection, credential_id, owner)
            connection.execute("DELETE FROM credentials WHERE credential_id = ? AND owner_id = ?", (credential_id, owner))

    def _record_removal(self, connection, credential_id, owner):
        row = connection.execute(
            "SELECT encrypted_secret FROM credentials WHERE credential_id=? AND owner_id=?", (credential_id, owner)
        ).fetchone()
        if row is None:
            raise CredentialNotFound("credential not found")
        if self.ledger is not None:
            self.ledger.revoke(row[0])

    @staticmethod
    def _mask(secret: str) -> str:
        return f"{secret[:3]}{'•' * max(4, len(secret) - 7)}{secret[-4:]}" if len(secret) > 7 else "••••••••"
