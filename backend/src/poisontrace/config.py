"""Web startup values without framework, storage or vendor dependencies."""

import base64
from collections.abc import Mapping
from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass(frozen=True)
class AccountSeed:
    username: str
    role: str
    passcode: str = field(repr=False)


def load_account_seeds(environment: Mapping[str, str] | None = None) -> tuple[AccountSeed, ...]:
    environment = os.environ if environment is None else environment
    defaults = (
        ("POISONTRACE_ANALYST_USERNAME", "POISONTRACE_ANALYST_PASSCODE", "analyst", "analyst"),
        ("POISONTRACE_SUPERADMIN_USERNAME", "POISONTRACE_SUPERADMIN_PASSCODE", "superadmin", "superadmin"),
    )
    return tuple(AccountSeed(environment.get(username_key, fallback), role, environment[passcode_key])
                 for username_key, passcode_key, fallback, role in defaults if environment.get(passcode_key))


@dataclass(frozen=True)
class WebConfig:
    # Relative defaults intentionally retain the local edition's working-directory contract.
    scenario_dir: Path = Path("backend/scenarios")
    database: Path = Path("poisontrace.db")
    secrets_database: Path = Path("poisontrace-secrets.db")
    secrets_key: bytes = field(default=b"", repr=False)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "WebConfig":
        environment = os.environ if environment is None else environment
        return cls(secrets_key=environment.get("POISONTRACE_SECRETS_KEY", "").encode())

    def require_secrets_key(self) -> bytes:
        """Validate local encryption configuration before storage is constructed."""
        if not self.secrets_key:
            raise RuntimeError(
                "POISONTRACE_SECRETS_KEY is required. Generate one with "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        try:
            decoded = base64.urlsafe_b64decode(self.secrets_key)
        except (ValueError, TypeError):
            raise ValueError("Fernet key must be 32 url-safe base64-encoded bytes.") from None
        if len(decoded) != 32:
            raise ValueError("Fernet key must be 32 url-safe base64-encoded bytes.")
        return self.secrets_key
