import pytest
from ninja.testing import TestClient

from accounts.tests.utils import create_test_user

from ..api import api


@pytest.mark.django_db
class TestJWT:
    def setup_method(self):
        self.client = TestClient(api)

    def test_token_pair_endpoint_exists(self):
        response = self.client.get("/auth/login")
        assert response.status_code == 405
        response = self.client.post("/auth/login", data={})
        assert response.status_code == 422

    def test_token_pair_success(self):
        from accounts.models import User

        email = "testuser@example.com"
        password = "testpass123"
        create_test_user(email=email, password=password)
        response = self.client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0

    def test_token_pair_invalid_credentials(self):
        from accounts.models import User

        email = "testuser2@example.com"
        password = "testpass123"
        create_test_user(email=email, password=password)
        response = self.client.post(
            "/auth/login", json={"email": email, "password": "wrongpass"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "access_token" not in data
        assert "refresh_token" not in data
        response = self.client.post(
            "/auth/login",
            json={"email": "nouser@example.com", "password": "irrelevant"},
        )
        assert response.status_code == 401
        data = response.json()
        assert "access_token" not in data
        assert "refresh_token" not in data

    def test_token_pair_missing_fields(self):
        response = self.client.post(
            "/auth/login", json={"email": "someone@example.com"}
        )
        assert response.status_code == 422
        response = self.client.post("/auth/login", json={"password": "irrelevant"})
        assert response.status_code == 422
        response = self.client.post("/auth/login", json={})
        assert response.status_code == 422

    def test_token_pair_jwt_structure(self):
        from accounts.models import User

        email = "jwtstructure@example.com"
        password = "testpass123"
        create_test_user(email=email, password=password)
        response = self.client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200
        data = response.json()
        for token_name in ("access_token", "refresh_token"):
            token = data.get(token_name)
            assert isinstance(token, str)
            assert (
                token.count(".") == 2
            ), f"{token_name} token is not a valid JWT: {token}"

    def test_refresh_token_flow(self):
        from accounts.models import User

        email = "refreshuser@example.com"
        password = "testpass123"
        create_test_user(email=email, password=password)
        response = self.client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200
        tokens = response.json()
        refresh_token = tokens.get("refresh_token")
        assert refresh_token is not None
        response = self.client.post(
            "/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != refresh_token
        assert isinstance(data["access_token"], str)
        assert (
            data["access_token"].count(".") == 2
        ), "Refreshed access token is not a valid JWT"

        replay = self.client.post(
            "/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert replay.status_code == 401

        # Replay detection revokes the complete device session, including the
        # token returned by the successful rotation.
        after_replay = self.client.post(
            "/auth/refresh",
            json={"refresh_token": data["refresh_token"]},
        )
        assert after_replay.status_code == 401

    def test_refresh_token_invalid_and_missing(self):
        response = self.client.post(
            "/auth/refresh", json={"refresh_token": "invalid.token.value"}
        )
        assert response.status_code in [401, 400, 422]
        data = response.json()
        assert "detail" in data or "message" in data
        response = self.client.post("/auth/refresh", json={})
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data or "message" in data

    def test_verify_token(self):
        from accounts.models import User

        email = "verifyuser@example.com"
        password = "testpass123"
        create_test_user(email=email, password=password)
        response = self.client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200
        tokens = response.json()
        access_token = tokens.get("access_token")
        assert access_token is not None
        response = self.client.post("/auth/token/verify", json={"token": access_token})
        assert response.status_code == 204
        response = self.client.post(
            "/auth/token/verify", json={"token": "invalid.token.value"}
        )
        assert response.status_code in [401, 422, 400]
        data = response.json()
        assert "detail" in data or "message" in data
