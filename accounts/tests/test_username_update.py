import pytest
from django.contrib.auth import get_user_model

from accounts.tests.utils import create_test_user
from organizations.models import Membership, Organization

User = get_user_model()


@pytest.mark.django_db
def test_patch_username_success(api_client):
    user = create_test_user(
        email="me@example.com", password="testpass", username="oldname"
    )
    # Clean up any existing personal orgs for this user
    Organization.objects.filter(memberships__user=user, kind="personal").delete()
    org = Organization.objects.create(
        name="oldname", slug="oldname-success", kind="personal", creator=user
    )
    Membership.objects.create(user=user, organization=org, role="owner")
    response = api_client.post(
        "/auth/login", json={"email": "me@example.com", "password": "testpass"}
    )
    access = response.json()["access_token"]
    response = api_client.patch(
        "/auth/me/username",
        json={"username": "newname"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newname"
    assert data["slug"] == "oldname"
    org.refresh_from_db()
    assert org.name == "newname"
    assert org.slug == "oldname-success"
    # Ensure DB updated
    user.refresh_from_db()
    org.refresh_from_db()
    # Re-fetch org by id to ensure we check the updated org
    updated_org = Organization.objects.get(id=org.id)
    assert updated_org.name == "newname"
    assert updated_org.slug == "oldname-success"
    assert user.username == "newname"
    assert user.slug == "oldname"
    assert org.name == "newname"
    assert org.slug == "oldname-success"


@pytest.mark.django_db
def test_patch_username_taken(api_client):
    user1 = create_test_user(
        email="me@example.com", password="testpass", username="oldname"
    )
    user2 = create_test_user(
        email="other@example.com", password="testpass", username="takenname"
    )
    # Clean up any existing personal orgs for this user
    Organization.objects.filter(memberships__user=user1, kind="personal").delete()
    org = Organization.objects.create(
        name="oldname", slug="oldname-taken", kind="personal", creator=user1
    )
    Membership.objects.create(user=user1, organization=org, role="owner")
    response = api_client.post(
        "/auth/login", json={"email": "me@example.com", "password": "testpass"}
    )
    access = response.json()["access_token"]
    response = api_client.patch(
        "/auth/me/username",
        json={"username": "takenname"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 400
    assert "Username already taken" in response.json()["detail"]


@pytest.mark.django_db
def test_patch_username_empty(api_client):
    user = create_test_user(
        email="me2@example.com", password="testpass", username="oldname2"
    )
    Organization.objects.filter(memberships__user=user, kind="personal").delete()
    org = Organization.objects.create(
        name="oldname2", slug="oldname2-empty", kind="personal", creator=user
    )
    Membership.objects.create(user=user, organization=org, role="owner")
    response = api_client.post(
        "/auth/login", json={"email": "me2@example.com", "password": "testpass"}
    )
    access = response.json()["access_token"]
    response = api_client.patch(
        "/auth/me/username",
        json={"username": "   "},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 400
    assert "1-50" in response.json()["detail"]


@pytest.mark.django_db
def test_patch_username_rejects_invalid_characters(api_client):
    user = create_test_user(
        email="invalidname@example.com", password="testpass", username="oldname"
    )
    Organization.objects.filter(memberships__user=user, kind="personal").delete()
    org = Organization.objects.create(
        name="oldname", slug="oldname-invalid", kind="personal", creator=user
    )
    Membership.objects.create(user=user, organization=org, role="owner")
    response = api_client.post(
        "/auth/login", json={"email": "invalidname@example.com", "password": "testpass"}
    )
    access = response.json()["access_token"]
    response = api_client.patch(
        "/auth/me/username",
        json={"username": "bad name!"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 400
    assert "letters, numbers, dots, and underscores" in response.json()["detail"]


@pytest.mark.django_db
def test_patch_username_org_missing(api_client):
    user = create_test_user(
        email="me3@example.com", password="testpass", username="oldname3"
    )
    # Ensure no personal org exists for user
    Organization.objects.filter(memberships__user=user, kind="personal").delete()
    response = api_client.post(
        "/auth/login", json={"email": "me3@example.com", "password": "testpass"}
    )
    access = response.json()["access_token"]
    response = api_client.patch(
        "/auth/me/username",
        json={"username": "newname3"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 500
    assert "Personal organization not found for user" in response.json()["detail"]
