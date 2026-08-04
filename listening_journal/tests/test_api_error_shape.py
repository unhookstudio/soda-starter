import pytest
from django.contrib.auth import get_user_model
from ninja.testing import TestClient

from organizations.models import Membership, Organization

from ..api import api


@pytest.mark.django_db
class TestApiErrorShape:
    def setup_method(self):
        User = get_user_model()
        self.member = User.objects.create_user(
            email="member@example.com", password="pass12345"
        )
        self.nonmember = User.objects.create_user(
            email="nonmember@example.com", password="pass12345"
        )
        self.org = Organization.objects.create(
            name="Acme", slug="acme", creator=self.member
        )
        Membership.objects.create(user=self.member, organization=self.org, role="owner")
        self.client = TestClient(api)

    def _get_auth_headers(self, user):
        # Get a valid JWT token for the user
        resp = self.client.post(
            "/auth/login", json={"email": user.email, "password": "pass12345"}
        )
        access = resp.json()["access_token"]
        return {"Authorization": f"Bearer {access}"}

    def test_invalid_ordering_returns_normalized_400_detail(self):
        headers = self._get_auth_headers(self.member)
        # Note: Ninja TestClient paths are relative to the API root, not the full URL
        resp = self.client.get(
            f"/workspaces/{self.org.id}/tags?ordering=bogus", headers=headers
        )
        assert resp.status_code == 400
        assert isinstance(resp.json(), dict)
        assert "detail" in resp.json()
        assert "Invalid ordering" in resp.json()["detail"]
        assert resp.json()["status"] == 400
        assert resp.json()["code"] == "invalid_request"
        assert resp["Content-Type"].startswith("application/problem+json")

    def test_nonmember_access_returns_normalized_404_detail(self):
        headers = self._get_auth_headers(self.nonmember)
        # Note: Ninja TestClient paths are relative to the API root, not the full URL
        resp = self.client.get(f"/workspaces/{self.org.id}/tags", headers=headers)
        assert resp.status_code == 404
        assert isinstance(resp.json(), dict)
        assert "detail" in resp.json()
        assert resp.json()["code"] == "workspace_not_found"

    def test_openapi_declares_problem_details_as_the_default_error(self):
        schema = api.get_openapi_schema()

        assert "ProblemDetails" in schema["components"]["schemas"]
        assert schema["paths"]["/api/v1/auth/login"]["post"]["responses"][
            "default"
        ] == {"$ref": "#/components/responses/ProblemDetails"}
