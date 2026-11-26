"""Trusted caller identity shared by application use cases and ownership adapters.

Only authentication/composition code may establish a scope. Request payloads never
participate. ContextVar scopes propagate into ASGI worker threads and async tasks.
An absent principal or a non-analyst has no analyst credential authority.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


class CredentialNotFound(KeyError):
    """Identical denial for absent, quarantined and foreign references."""


@dataclass(frozen=True)
class Principal:
    account_id: int
    role: str


_principal: ContextVar[Principal | None] = ContextVar('poisontrace_principal', default=None)


@contextmanager
def principal_scope(principal: Principal | None):
    token = _principal.set(principal)
    try:
        yield
    finally:
        _principal.reset(token)


def analyst_owner_id() -> int | None:
    principal = _principal.get()
    if principal is not None and principal.role == 'analyst' and type(principal.account_id) is int and principal.account_id > 0:
        return principal.account_id
    return None


def require_analyst_owner() -> int:
    owner = analyst_owner_id()
    if owner is None:
        raise CredentialNotFound('credential not found')
    return owner
