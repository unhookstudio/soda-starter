import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from organizations.models import Membership, Organization
from organizations.tests.utils import create_test_group
from tags.models import Tag

User = get_user_model()


def get_access_token(email, password):
    client = Client()
    resp = client.post(
        "/api/v1/auth/login",
        data={"email": email, "password": password},
        content_type="application/json",
    )
    if resp.status_code != 200 or "access_token" not in resp.json():
        resp2 = client.post(
            "/api/v1/auth/login",
            data={"email": email, "password": password},
            content_type="application/x-www-form-urlencoded",
        )
        return resp2.json().get("access_token")
    return resp.json().get("access_token")


@pytest.mark.django_db
def test_list_tags_requires_membership():
    # org exists but user is not a member
    org = create_test_group(name="TagsOrg", slug="tagsorg")
    User.objects.create_user(
        email="tags1@example.com", password="pw", email_verified=True
    )
    client = Client()
    access = get_access_token("tags1@example.com", "pw")
    resp = client.get(
        f"/api/v1/workspaces/{org.id}/tags", HTTP_AUTHORIZATION=f"Bearer {access}"
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_assign_tags_wrong_object_org_is_hidden():
    # User is member of org1, but tries to assign tags to an object belonging to org2
    org1 = Organization.objects.create(name="OrgA", slug="orga")
    org2 = create_test_group(name="OrgB", slug="orgb")
    user = User.objects.create_user(
        email="tags2@example.com", password="pw", email_verified=True
    )
    Membership.objects.create(user=user, organization=org1, role="owner")

    client = Client()
    access = get_access_token("tags2@example.com", "pw")
    app_label = "organizations"
    model = "organization"
    object_id = org2.id  # object belongs to different org than route

    url = f"/api/v1/workspaces/{org1.id}/objects/{app_label}/{model}/{object_id}/tags"
    resp = client.post(
        url,
        data=["vip"],
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_unassign_by_id_wrong_object_is_hidden():
    org1 = Organization.objects.create(name="Org1", slug="org1tags")
    org2 = create_test_group(name="Org2", slug="org2tags")
    user = User.objects.create_user(
        email="tags3@example.com", password="pw", email_verified=True
    )
    Membership.objects.create(user=user, organization=org1, role="owner")

    client = Client()
    access = get_access_token("tags3@example.com", "pw")
    app_label = "organizations"
    model = "organization"
    # try to unassign from an object in a different org
    tag = Tag.objects.create(organization=org1, name="Some tag", slug="some-tag")
    url = f"/api/v1/workspaces/{org1.id}/objects/{app_label}/{model}/{org2.id}/tags/{tag.id}"
    resp = client.delete(url, HTTP_AUTHORIZATION=f"Bearer {access}")
    assert resp.status_code == 404
