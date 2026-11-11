
import pytest

from poisontrace.adapters.persistence.accounts import SqliteAccountStore
from poisontrace.application.accounts import AuthenticationError, UserSessionService
from poisontrace.bootstrap import build_accounts
from poisontrace.config import AccountSeed, load_account_seeds


def test_explicit_account_composition_ignores_environment_and_redacts_seed_repr(tmp_path, monkeypatch):
    monkeypatch.setenv("POISONTRACE_ANALYST_PASSCODE", "unused-environment-passcode")
    seeds = (AccountSeed(" Operator ", "superadmin", "synthetic-admin-passcode"),)
    assert "synthetic-admin-passcode" not in repr(seeds)
    service = build_accounts(tmp_path / "accounts.db", seeds=seeds)
    assert [user.username for user in service.list_users()] == ["operator"]
    assert service.authenticate("operator", "synthetic-admin-passcode")[0].role == "superadmin"
    assert load_account_seeds({}) == ()
    assert load_account_seeds({"POISONTRACE_ANALYST_PASSCODE": "synthetic"}) == (AccountSeed("analyst", "analyst", "synthetic"),)


def test_account_storage_transaction_rolls_back_on_failure(tmp_path):
    store = SqliteAccountStore(tmp_path / "accounts.db")
    service = UserSessionService(store)
    with pytest.raises(RuntimeError, match="synthetic failure"):
        with store.transaction() as accounts:
            accounts.create("synthetic", "Synthetic", "analyst", "hash")
            raise RuntimeError("synthetic failure")
    assert service.list_users() == []
    user = service.create_analyst("user", "User", "synthetic-passcode")
    with pytest.raises(AuthenticationError):
        service.authenticate("user", "wrong")
    assert service.list_users()[0].last_login_at is None
    assert user.public_dict().keys() == {"id", "username", "display_name", "role", "status", "created_at", "last_login_at"}
