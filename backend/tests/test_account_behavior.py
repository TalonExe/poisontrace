import hashlib
import sqlite3

import pytest

from poisontrace.application.accounts import AuthenticationError
from poisontrace.bootstrap import build_accounts


def test_seed_accounts_skip_absent_passcodes_and_never_reset_existing(tmp_path, monkeypatch):
    monkeypatch.delenv("POISONTRACE_ANALYST_PASSCODE", raising=False)
    monkeypatch.delenv("POISONTRACE_SUPERADMIN_PASSCODE", raising=False)
    database = tmp_path / "accounts.db"
    assert build_accounts(database).list_users() == []
    monkeypatch.setenv("POISONTRACE_ANALYST_USERNAME", " Mixed.Case ")
    monkeypatch.setenv("POISONTRACE_ANALYST_PASSCODE", "synthetic-original")
    first = build_accounts(database)
    assert first.list_users()[0].username == "mixed.case"
    assert first.list_users()[0].display_name == "Development analyst"
    monkeypatch.setenv("POISONTRACE_ANALYST_PASSCODE", "synthetic-changed")
    reopened = build_accounts(database)
    assert reopened.authenticate("MIXED.CASE", "synthetic-original")[0].role == "analyst"
    with pytest.raises(AuthenticationError, match="invalid credentials"):
        reopened.authenticate("mixed.case", "synthetic-changed")


def test_account_session_hashes_reopen_logout_and_reenable(tmp_path, monkeypatch):
    monkeypatch.delenv("POISONTRACE_ANALYST_PASSCODE", raising=False)
    monkeypatch.delenv("POISONTRACE_SUPERADMIN_PASSCODE", raising=False)
    database = tmp_path / "accounts.db"
    service = build_accounts(database)
    user = service.create_analyst(" New.User ", " User Name ", "synthetic-passcode")
    returned, token = service.authenticate("NEW.USER", "synthetic-passcode")
    assert returned.last_login_at is None  # Login returns the pre-update account, as before.
    assert returned.display_name == "User Name"
    with sqlite3.connect(database) as db:
        stored = db.execute("SELECT passcode_hash FROM users").fetchone()[0]
        assert stored.startswith("scrypt$") and "synthetic-passcode" not in stored
        assert db.execute("SELECT token_hash FROM auth_sessions").fetchone()[0] == hashlib.sha256(token.encode()).hexdigest()
    reopened = build_accounts(database)
    assert reopened.current_user(token).last_login_at is not None
    reopened.update_user(user.id, status="disabled")
    with pytest.raises(AuthenticationError):
        service.current_user(token)
    reopened.update_user(user.id, status="active")
    assert service.current_user(token).id == user.id
    service.logout(token)
    service.logout(None)
    with pytest.raises(AuthenticationError):
        reopened.current_user(token)


def test_account_errors_and_last_admin_policy(tmp_path, monkeypatch):
    monkeypatch.setenv("POISONTRACE_SUPERADMIN_PASSCODE", "synthetic-admin")
    monkeypatch.delenv("POISONTRACE_ANALYST_PASSCODE", raising=False)
    service = build_accounts(tmp_path / "accounts.db")
    admin = service.list_users()[0]
    for update in ({"role": "analyst"}, {"status": "disabled"}):
        with pytest.raises(ValueError, match="last active superadmin"):
            service.update_user(admin.id, **update)
    second = service.create_analyst("second", "Second", "synthetic")
    with pytest.raises(ValueError, match="username already exists"):
        service.create_analyst("SECOND", "Duplicate", "synthetic")
    with pytest.raises(KeyError):
        service.update_user(999)
    with pytest.raises(ValueError, match="invalid role or status"):
        service.update_user(second.id, role="other")
    service.update_user(second.id, role="superadmin")
    service.update_user(admin.id, role="analyst")
    assert service.update_user(admin.id, display_name=" ", role="", status="").display_name == ""
    assert service.list_users("SECOND")[0].id == second.id
