import logging
import os
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.schemas import AvatarUrlsOut
from core.utils.storage import (
    delete_storage_keys,
    generate_private_presigned_storage_url,
)

logger = logging.getLogger(__name__)
DEFAULT_AVATAR_URL_TTL_SECONDS = 15 * 60


def avatar_storage_keys(avatar_filename: str) -> tuple[str, str]:
    base, ext = os.path.splitext(avatar_filename)
    return avatar_filename, f"{base}_lg{ext}"


def sign_avatar_urls(
    avatar_filename: str,
    *,
    expires_in: int | None = None,
) -> AvatarUrlsOut:
    ttl = expires_in or int(
        getattr(
            settings,
            "AVATAR_SIGNED_URL_TTL_SECONDS",
            DEFAULT_AVATAR_URL_TTL_SECONDS,
        )
    )
    small_key, large_key = avatar_storage_keys(avatar_filename)
    signing_options = {
        "expires_in": ttl,
        "content_type": "image/webp",
        "cache_control": f"private, max-age={ttl}",
    }
    return AvatarUrlsOut(
        small=generate_private_presigned_storage_url(small_key, **signing_options),
        large=generate_private_presigned_storage_url(large_key, **signing_options),
        expires_at=timezone.now() + timedelta(seconds=ttl),
    )


def delete_existing_avatar(obj):
    """
    Deletes both small and large avatar files for the given object from storage.
    Expects the object to have an 'avatar_path' attribute.
    """
    avatar_filename = getattr(obj, "avatar_path", None)
    if not avatar_filename:
        return

    delete_avatar_files(avatar_filename)


def delete_avatar_files(avatar_filename: str) -> None:
    delete_storage_keys(avatar_storage_keys(avatar_filename))


def schedule_avatar_file_deletion(avatar_filename: str | None) -> None:
    if not avatar_filename:
        return

    def delete_after_commit() -> None:
        try:
            delete_avatar_files(avatar_filename)
        except Exception:
            logger.exception(
                "avatar:delete_failed path=%s",
                avatar_filename,
            )

    transaction.on_commit(delete_after_commit)
