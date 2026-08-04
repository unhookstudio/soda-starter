from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.utils.avatar import delete_existing_avatar, sign_avatar_urls


@patch("django.core.files.storage.default_storage.delete")
def test_delete_existing_avatar_calls_storage_delete(mock_delete):
    # Arrange: dummy object with avatar_path
    obj = SimpleNamespace(avatar_path="avatars/foo.webp")
    # Act
    delete_existing_avatar(obj)
    # Assert: should call delete for both small and large avatar
    mock_delete.assert_any_call("avatars/foo.webp")
    mock_delete.assert_any_call("avatars/foo_lg.webp")
    assert mock_delete.call_count == 2


@patch("django.core.files.storage.default_storage.delete")
def test_delete_existing_avatar_no_avatar(mock_delete):
    obj = SimpleNamespace(avatar_path=None)
    delete_existing_avatar(obj)
    mock_delete.assert_not_called()


def test_sign_avatar_urls_uses_private_short_lived_urls(monkeypatch):
    calls = []

    def fake_sign(key, **kwargs):
        calls.append((key, kwargs))
        return f"https://signed.example/{key}"

    monkeypatch.setattr(
        "core.utils.avatar.generate_private_presigned_storage_url", fake_sign
    )

    result = sign_avatar_urls("avatars/users/example.webp", expires_in=300)

    assert result.small == "https://signed.example/avatars/users/example.webp"
    assert result.large == "https://signed.example/avatars/users/example_lg.webp"
    assert [call[0] for call in calls] == [
        "avatars/users/example.webp",
        "avatars/users/example_lg.webp",
    ]
    assert all(call[1]["expires_in"] == 300 for call in calls)
    assert all(call[1]["cache_control"] == "private, max-age=300" for call in calls)
