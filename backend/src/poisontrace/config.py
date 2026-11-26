"""Web startup values without framework, storage or vendor dependencies."""

import base64
from collections.abc import Mapping
from dataclasses import dataclass, field
import os
from pathlib import Path
from urllib.parse import urlsplit
from ipaddress import ip_network


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
    profile: str = "local"
    public_origin: str = ""
    trusted_proxy_cidrs: tuple[str, ...] = ()
    recovery_ledger: Path | None = None

    def __post_init__(self):
        if self.profile not in {"local", "hosted"}:
            raise ValueError("profile must be local or hosted")
        for network in self.trusted_proxy_cidrs:
            if ip_network(network).prefixlen == 0:
                raise ValueError("proxy trust must use explicit bounded networks")

    def validate_http(self):
        if self.profile == "hosted":
            parsed = urlsplit(self.public_origin)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment or parsed.netloc != parsed.netloc.lower()
                    or any(c.isspace() for c in self.public_origin)):
                raise ValueError("hosted PUBLIC_ORIGIN must be one canonical HTTPS origin without a path")
            host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
            canonical = f"https://{host}" + (f":{parsed.port}" if parsed.port and parsed.port != 443 else "")
            if canonical != self.public_origin:
                raise ValueError("hosted PUBLIC_ORIGIN must be canonical")

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "WebConfig":
        environment = os.environ if environment is None else environment
        return cls(secrets_key=environment.get("POISONTRACE_SECRETS_KEY", "").encode(),
                   profile=environment.get("POISONTRACE_PROFILE", "local"),
                   public_origin=environment.get("POISONTRACE_PUBLIC_ORIGIN", ""),
                   trusted_proxy_cidrs=tuple(filter(None, (part.strip() for part in environment.get("POISONTRACE_TRUSTED_PROXIES", "").split(",")))))

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
