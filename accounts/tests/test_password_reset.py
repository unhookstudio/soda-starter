import datetime
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import PendingPasswordReset
from accounts.tests.utils import create_test_user
from accounts.tokens import hash_token

User = get_user_model()


@pytest.mark.django_db
def test_password_reset_request_valid_email(settings, api_client):
    user = create_test_user(email="user@example.com", password="pass1234")
    url = "/auth/password-reset/request"
    data = {"email": "user@example.com"}
    with patch("accounts.services.enqueue_email") as mock_send_email:
        response = api_client.post(url, json=data)
        assert response.status_code == 202
        assert response.json() == {"status": "reset_pending"}
        # A PendingPasswordReset should be created
        assert PendingPasswordReset.objects.filter(user=user).exists()
        assert len(PendingPasswordReset.objects.get(user=user).token) == 64
        # Email should be sent
        assert mock_send_email.called


@pytest.mark.django_db
def test_password_reset_request_invalid_email_format(api_client):
    url = "/auth/password-reset/request"
    data = {"email": "not-an-email"}
    response = api_client.post(url, json=data)
    assert response.status_code == 202
    assert response.json() == {"status": "reset_pending"}
    assert not PendingPasswordReset.objects.exists()


@pytest.mark.django_db
def test_password_reset_request_nonexistent_email(api_client):
    url = "/auth/password-reset/request"
    data = {"email": "nobody@example.com"}
    response = api_client.post(url, json=data)
    assert response.status_code == 202
    assert response.json() == {"status": "reset_pending"}


@pytest.mark.django_db
def test_password_reset_request_deletes_previous(settings, api_client):
    user = create_test_user(email="user2@example.com", password="pass1234")
    expires_at = timezone.now() + datetime.timedelta(hours=2)
    PendingPasswordReset.objects.create(
        user=user, token=hash_token("oldtoken"), expires_at=expires_at
    )
    url = "/auth/password-reset/request"
    data = {"email": "user2@example.com"}
    with patch("accounts.services.enqueue_email"):
        response = api_client.post(url, json=data)
    assert response.status_code == 202
    # Only one PendingPasswordReset should exist now
    assert PendingPasswordReset.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_password_reset_request_email_send_failure(monkeypatch, api_client):
    create_test_user(email="failmail@example.com", password="pw")
    url = "/auth/password-reset/request"
    data = {"email": "failmail@example.com"}

    def fail_send_email_task(*args, **kwargs):
        raise Exception("Simulated email failure")

    monkeypatch.setattr("accounts.services.enqueue_email", fail_send_email_task)
    response = api_client.post(url, json=data)
    assert response.status_code == 202
    assert response.json() == {"status": "reset_pending"}


@pytest.mark.django_db
def test_password_reset_confirm_success(api_client):
    user = create_test_user(email="resetme@example.com", password="oldpassword")
    login = api_client.post(
        "/auth/login",
        json={"email": user.email, "password": "oldpassword"},
    ).json()
    # Create a valid PendingPasswordReset
    import secrets

    from django.utils import timezone

    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timezone.timedelta(hours=2)
    from accounts.models import PendingPasswordReset

    PendingPasswordReset.objects.create(
        user=user, token=hash_token(token), expires_at=expires_at
    )
    url = "/auth/password-reset/confirm"
    data = {"token": token, "new_password": "newpass123"}
    response = api_client.post(url, json=data)
    assert response.status_code == 200
    assert response.json()["reauthentication_required"] is True
    # Password should be changed
    user.refresh_from_db()
    assert user.check_password("newpass123")
    # PendingPasswordReset should be deleted
    assert not PendingPasswordReset.objects.filter(token=hash_token(token)).exists()
    assert (
        api_client.post(
            "/auth/refresh",
            json={"refresh_token": login["refresh_token"]},
        ).status_code
        == 401
    )
    assert api_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    ).status_code in {401, 403}


@pytest.mark.django_db
def test_password_reset_confirm_invalid_token(api_client):
    url = "/auth/password-reset/confirm"
    data = {"token": "invalidtoken", "new_password": "irrelevant"}
    response = api_client.post(url, json=data)
    assert response.status_code == 400
    assert (
        "invalid" in response.json()["detail"].lower()
        or "expired" in response.json()["detail"].lower()
    )


@pytest.mark.django_db
def test_password_reset_confirm_expired_token(api_client):
    user = create_test_user(email="expired@example.com", password="oldpassword")
    import secrets

    from django.utils import timezone

    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() - timezone.timedelta(hours=1)  # Already expired
    from accounts.models import PendingPasswordReset

    PendingPasswordReset.objects.create(
        user=user, token=hash_token(token), expires_at=expires_at
    )
    url = "/auth/password-reset/confirm"
    data = {"token": token, "new_password": "newpass123"}
    response = api_client.post(url, json=data)
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()
    # PendingPasswordReset should be deleted
    assert not PendingPasswordReset.objects.filter(token=hash_token(token)).exists()
