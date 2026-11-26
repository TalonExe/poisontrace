"""Account lifecycle, authentication and session behavior over transactional storage."""

from collections.abc import Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass
import hashlib
import secrets
from typing import Protocol
import time


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


class LoginThrottled(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("Too many sign-in attempts. Try again later.")


class AccountRecords(Protocol):
    """Storage operations sharing one commit/rollback scope, without SQL in use cases."""
    def find_credentials(self, username: str) -> tuple[AuthUser, str] | None: ...
    def get(self, user_id: int) -> AuthUser | None: ...
    def create(self, username: str, display_name: str, role: str, passcode_hash: str, *, ignore_existing: bool = False) -> AuthUser: ...
    def touch_login(self, user_id: int) -> None: ...
    def add_session(self, token_hash: str, user_id: int, expires_at: float) -> None: ...
    def session_user(self, token_hash: str, now: float) -> AuthUser | None: ...
    def delete_session(self, token_hash: str) -> None: ...
    def delete_user_sessions(self, user_id: int) -> None: ...
    def replace_passcode(self, user_id: int, passcode_hash: str) -> None: ...
    def reserve_login(self, keys: tuple[tuple[str, int], ...], now: float) -> int: ...
    def list_users(self, username_pattern: str, display_name_pattern: str) -> list[AuthUser]: ...
    def active_superadmin_count(self) -> int: ...
    def update(self, user_id: int, display_name: str, role: str, status: str) -> AuthUser: ...


class AccountStore(Protocol):
    def transaction(self) -> AbstractContextManager[AccountRecords]: ...


class UserSessionService:
    def __init__(self, store: AccountStore, *, clock=time.time, session_seconds: int = 28800) -> None:
        if not 1 <= session_seconds <= 28800:
            raise ValueError("session lifetime must be between 1 and 28800 seconds")
        self.store = store
        self.clock = clock
        self.session_seconds = session_seconds

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

    def authenticate(self, username: str, passcode: str, *, client_address: str | None = None) -> tuple[AuthUser, str]:
        normalized = self.normalize_username(username)
        if client_address is not None:
            keys = tuple((hashlib.sha256(value.encode()).hexdigest(), limit) for value, limit in
                         (("account:" + normalized, 10), ("peer:" + client_address, 60), ("global", 200)))
            with self.store.transaction() as accounts:
                retry_after = accounts.reserve_login(keys, self.clock())
            if retry_after:
                raise LoginThrottled(retry_after)
        with self.store.transaction() as accounts:
            credentials = accounts.find_credentials(normalized)
            if credentials:
                matched = self._matches(passcode, credentials[1])
            else:
                self._hash(passcode, b"missing-account!")
                matched = False
            if not credentials or credentials[0].status != "active" or not matched:
                raise AuthenticationError("invalid credentials")
            user = credentials[0]
            accounts.touch_login(user.id)
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            accounts.add_session(token_hash, user.id, self.clock() + self.session_seconds)
            return user, token

    def current_user(self, token: str | None) -> AuthUser:
        if not token:
            raise AuthenticationError("authentication required")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.store.transaction() as accounts:
            user = accounts.session_user(token_hash, self.clock())
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

    def reset_analyst_passcode(self, actor_token: str | None, user_id: int, passcode: str) -> None:
        with self.store.transaction() as accounts:
            actor = accounts.session_user(hashlib.sha256(actor_token.encode()).hexdigest(), self.clock()) if actor_token else None
            if not actor or actor.status != "active":
                raise AuthenticationError("authentication required")
            if actor.role != "superadmin":
                raise PermissionError("Forbidden")
            user = accounts.get(user_id)
            if not user:
                raise KeyError(user_id)
            if user.role != "analyst":
                raise ValueError("superadmin passcode recovery requires the restricted operator command")
            if not isinstance(passcode, str) or not passcode or len(passcode) > 1024:
                raise ValueError("a passcode of 1 to 1024 characters is required")
            accounts.replace_passcode(user.id, self._hash(passcode))
            accounts.delete_user_sessions(user.id)

    def recover_superadmin(self, username: str, passcode: str, *, enable_disabled: bool = False) -> AuthUser:
        if not isinstance(passcode, str) or not passcode or len(passcode) > 1024:
            raise ValueError("a passcode of 1 to 1024 characters is required")
        with self.store.transaction() as accounts:
            credentials = accounts.find_credentials(self.normalize_username(username))
            if not credentials or credentials[0].role != "superadmin":
                raise ValueError("an existing superadmin is required; recovery never creates or promotes accounts")
            user = credentials[0]
            if user.status != "active" and not enable_disabled:
                raise ValueError("disabled superadmin requires explicit enable-disabled recovery")
            accounts.replace_passcode(user.id, self._hash(passcode))
            accounts.delete_user_sessions(user.id)
            return accounts.update(user.id, user.display_name, user.role, "active")

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
            if next_status != "active" or next_role != user.role:
                accounts.delete_user_sessions(user_id)
            return accounts.update(user_id, display_name.strip() if display_name is not None else user.display_name,
                                   next_role, next_status)
