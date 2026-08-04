import pytest
from ninja.testing import TestClient

from accounts.services import issue_token_pair
from accounts.tests.utils import create_test_user

from ..api import api


@pytest.mark.django_db
class TestLogout:
    def setup_method(self):
        self.client = TestClient(api)

    def test_logout_requires_refresh_token(self):
        response = self.client.post("/auth/logout")
        assert response.status_code == 422

    def test_logout_revokes_session(self):
        email = "logoutuser@example.com"
        password = "testpass123"
        create_test_user(email=email, password=password)
        token_response = self.client.post(
            "/auth/login",
            json={"email": email, "password": password, "device_name": "Test iPhone"},
        )
        tokens = token_response.json()

        response = self.client.post(
            "/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 204

        refresh_response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_response.status_code == 401

        protected_response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert protected_response.status_code in {401, 403}

    def test_logout_all_revokes_every_session(self):
        user = create_test_user(email="logout-all@example.com", password="testpass123")
        first_access, first_refresh = issue_token_pair(user, device_name="Laptop")
        second_access, second_refresh = issue_token_pair(user, device_name="Phone")

        response = self.client.post(
            "/auth/logout-all",
            headers={"Authorization": f"Bearer {first_access}"},
        )

        assert response.status_code == 204
        for refresh in (first_refresh, second_refresh):
            rejected = self.client.post(
                "/auth/refresh", json={"refresh_token": refresh}
            )
            assert rejected.status_code == 401
        rejected_access = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {second_access}"},
        )
        assert rejected_access.status_code in {401, 403}
