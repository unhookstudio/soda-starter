from __future__ import annotations

from accounts.models import User
from accounts.schemas import UserProfileOut
from organizations.models import Organization


def serialize_user_profile(
    user: User,
    organization: Organization | None,
) -> UserProfileOut:
    return UserProfileOut(
        id=user.pk,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        slug=user.slug,
        location=user.location,
        about=user.about,
        has_avatar=bool(user.avatar_path),
        notification_preferences=user.notification_preferences,
        theme=user.theme,
        locale=user.locale,
        current_workspace_id=user.current_organization_id,
        finished_onboarding=user.finished_onboarding,
        email_verified=user.email_verified,
        created_at=user.created_at,
    )
