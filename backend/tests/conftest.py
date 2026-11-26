"""Explicit authenticated clients for investigation HTTP tests."""

import pytest


@pytest.fixture
def application_analyst():
    """Explicit trusted application caller for synthetic non-HTTP tests."""
    from poisontrace.application.principals import Principal, principal_scope
    with principal_scope(Principal(1, 'analyst')):
        yield


@pytest.fixture
def analyst_client(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("POISONTRACE_ANALYST_USERNAME", "test-analyst")
    monkeypatch.setenv("POISONTRACE_ANALYST_PASSCODE", "synthetic-test-passcode")

    def create(app):
        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"username": "test-analyst", "passcode": "synthetic-test-passcode"},
        )
        assert response.status_code == 200, response.text
        return client

    return create
