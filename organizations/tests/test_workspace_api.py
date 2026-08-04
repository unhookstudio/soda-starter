import pytest

from accounts.models import User
from accounts.services import issue_token_pair
from organizations.models import Membership, Organization


def headers_for(user: User) -> dict[str, str]:
    access, _refresh = issue_token_pair(user)
    return {"Authorization": f"Bearer {access}"}


@pytest.mark.django_db
def test_workspace_list_and_current_preference(api_client):
    user = User.objects.create_user(email="workspaces@example.com", password="pw")
    first = Organization.objects.create(
        name="Alpha", slug="alpha-workspace", kind="shared", creator=user
    )
    second = Organization.objects.create(
        name="Beta", slug="beta-workspace", kind="shared", creator=user
    )
    Membership.objects.create(user=user, organization=first, role="owner")
    Membership.objects.create(user=user, organization=second, role="owner")
    user.current_organization = first
    user.save(update_fields=["current_organization", "updated_at"])
    headers = headers_for(user)

    listed = api_client.get("/workspaces", headers=headers)
    current = api_client.get("/workspaces/current", headers=headers)
    changed = api_client.put(
        "/workspaces/current",
        json={"workspace_id": second.id},
        headers=headers,
    )

    assert listed.status_code == 200
    listed_ids = {item["id"] for item in listed.json()}
    assert {str(first.id), str(second.id)} <= listed_ids
    assert current.status_code == 200
    assert current.json()["id"] == str(first.id)
    assert changed.status_code == 200
    assert changed.json()["id"] == str(second.id)
    assert changed.json()["role"] == "owner"
    user.refresh_from_db()
    assert user.current_organization_id == second.id


@pytest.mark.django_db
def test_current_workspace_requires_membership_even_for_platform_admin(api_client):
    superuser = User.objects.create_superuser(
        email="workspace-superuser@example.com", password="pw"
    )
    original_workspace_id = superuser.current_organization_id
    owner = User.objects.create_user(email="unjoined-owner@example.com", password="pw")
    workspace = Organization.objects.create(
        name="Unjoined", slug="unjoined-workspace", kind="shared", creator=owner
    )
    Membership.objects.create(user=owner, organization=workspace, role="owner")

    response = api_client.put(
        "/workspaces/current",
        json={"workspace_id": workspace.id},
        headers=headers_for(superuser),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "workspace_membership_required"
    superuser.refresh_from_db()
    assert superuser.current_organization_id == original_workspace_id


@pytest.mark.django_db
def test_current_workspace_without_memberships_returns_problem_details(api_client):
    user = User.objects.create_user(email="no-workspace@example.com", password="pw")
    Organization.objects.filter(memberships__user=user).delete()
    user.refresh_from_db()

    response = api_client.get("/workspaces/current", headers=headers_for(user))

    assert response.status_code == 404
    assert response["Content-Type"].startswith("application/problem+json")
    assert response.json()["code"] == "workspace_not_found"
