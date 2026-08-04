import pytest
from ninja.testing import TestClient

from listening_journal.api import api as project_api


@pytest.fixture
def bypass_throttles(monkeypatch):
    """Explicit opt-out for a test whose request volume is unrelated to throttling."""
    from core.throttling import PostgresRateThrottle

    monkeypatch.setattr(
        PostgresRateThrottle, "allow_request", lambda self, request, view=None: True
    )


@pytest.fixture(scope="function")
def api_client():
    return TestClient(project_api)


@pytest.fixture
def make_auth_headers():
    """Return a callable that generates Bearer auth headers for a user via /auth/login."""

    def _make(client: TestClient, user, password: str = "pw") -> dict[str, str]:
        from accounts.services import issue_token_pair

        access, _refresh = issue_token_pair(user)
        return {"Authorization": f"Bearer {access}"}

    return _make
