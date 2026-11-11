"""Account lifecycle, authentication and session behavior over transactional storage."""

from collections.abc import Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass
import hashlib
import secrets
from typing import Protocol


@dataclass(frozen=True)
class AuthUser:
    id: int
    username: str
    display_name: str
    role: str
    status: str
    created_at: str
    last_login_at: str | None

    def public_dict(self) -> dict[str, str | int | None]:
        return self.__dict__.copy()


class AuthenticationError(Exception):
    pass


class AccountRecords(Protocol):
    """Storage operations sharing one commit/rollback scope, without SQL in use cases."""
    def find_credentials(self, username: str) -> tuple[AuthUser, str] | None: ...
    def get(self, user_id: int) -> AuthUser | None: ...
    def create(self, username: str, display_name: str, role: str, passcode_hash: str, *, ignore_existing: bool = False) -> AuthUser: ...
    def touch_login(self, user_id: int) -> None: ...
    def add_session(self, token_hash: str, user_id: int) -> None: ...
    def session_user(self, token_hash: str) -> AuthUser | None: ...
    def delete_session(self, token_hash: str) -> None: ...
    def list_users(self, username_pattern: str, display_name_pattern: str) -> list[AuthUser]: ...
    def active_superadmin_count(self) -> int: ...
    def update(self, user_id: int, display_name: str, role: str, status: str) -> AuthUser: ...


class AccountStore(Protocol):
    def transaction(self) -> AbstractContextManager[AccountRecords]: ...


class UserSessionService:
    def __init__(self, store: AccountStore) -> None:
        self.store = store

    @staticmethod
    def normalize_username(username: str) -> str:
        return username.strip().casefold()

    @staticmethod
    def _hash(passcode: str, salt: bytes | None = None) -> str:
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.scrypt(passcode.encode(), salt=salt, n=2**14, r=8, p=1)
        return f"scrypt${salt.hex()}${digest.hex()}"

    @classmethod
    def _matches(cls, passcode: str, stored: str) -> bool:
        _, salt, digest = stored.split("$", 2)
        actual = cls._hash(passcode, bytes.fromhex(salt)).split("$", 2)[2]
        return secrets.compare_digest(actual, digest)

    def seed_demo_accounts(self, seeds: Iterable[tuple[str, str, str]]) -> None:
        with self.store.transaction() as accounts:
            for username, role, passcode in seeds:
                accounts.create(self.normalize_username(username), f"Development {role}", role,
                                self._hash(passcode), ignore_existing=True)

    def authenticate(self, username: str, passcode: str) -> tuple[AuthUser, str]:
        normalized = self.normalize_username(username)
        with self.store.transaction() as accounts:
            credentials = accounts.find_credentials(normalized)
            if not credentials or credentials[0].status != "active" or not self._matches(passcode, credentials[1]):
                raise AuthenticationError("invalid credentials")
            user = credentials[0]
            accounts.touch_login(user.id)
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            accounts.add_session(token_hash, user.id)
            return user, token

    def current_user(self, token: str | None) -> AuthUser:
        if not token:
            raise AuthenticationError("authentication required")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.store.transaction() as accounts:
            user = accounts.session_user(token_hash)
        if not user or user.status != "active":
            raise AuthenticationError("authentication required")
        return user

    def logout(self, token: str | None) -> None:
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            with self.store.transaction() as accounts:
                accounts.delete_session(token_hash)

    def list_users(self, search: str = "") -> list[AuthUser]:
        pattern = f"%{self.normalize_username(search)}%"
        with self.store.transaction() as accounts:
            return accounts.list_users(pattern, f"%{search.strip()}%")

    def create_analyst(self, username: str, display_name: str, passcode: str) -> AuthUser:
        normalized = self.normalize_username(username)
        if not normalized or not display_name.strip() or not passcode:
            raise ValueError("username, display name, and passcode are required")
        with self.store.transaction() as accounts:
            return accounts.create(normalized, display_name.strip(), "analyst", self._hash(passcode))

    def update_user(self, user_id: int, *, display_name: str | None = None, role: str | None = None, status: str | None = None) -> AuthUser:
        with self.store.transaction() as accounts:
            user = accounts.get(user_id)
            if not user:
                raise KeyError(user_id)
            next_role = role or user.role
            next_status = status or user.status
            if next_role not in {"analyst", "superadmin"} or next_status not in {"active", "disabled"}:
                raise ValueError("invalid role or status")
            if user.role == "superadmin" and user.status == "active" and (next_role != "superadmin" or next_status != "active"):
                if accounts.active_superadmin_count() <= 1:
                    raise ValueError("the last active superadmin cannot be demoted or disabled")
            return accounts.update(user_id, display_name.strip() if display_name is not None else user.display_name,
                                   next_role, next_status)
