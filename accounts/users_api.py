import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import File, Router, Status, UploadedFile
from ninja.errors import HttpError

from accounts.models import User
from core.authentication import JWTAuth
from core.schemas import AvatarUrlsOut
from core.utils.auth_utils import get_request_user
from core.utils.avatar import schedule_avatar_file_deletion, sign_avatar_urls
from core.utils.image import InvalidImageContent, resize_avatar_images
from core.utils.storage import delete_storage_keys, upload_to_storage
from core.utils.uploads import UploadTooLarge, read_uploaded_file_bounded
from organizations.models import Organization
from organizations.services import ActiveOwnerRequiredError

from .schemas import (
    DeleteAccountSchema,
    UsernameCheckResponse,
    UserProfileOut,
    UserProfileUpdate,
)
from .serializers import serialize_user_profile
from .services import delete_user_account
from .throttles import username_check_throttle
from .username import router as username_router
from .username_validation import validate_username_value

# You can add more user/profile endpoints here as needed
users_router = Router()
profile_router = Router()

profile_router.add_router("", username_router, tags=["profile"])


def serialize_profile_with_current_org(user: User) -> UserProfileOut:
    org = user.current_organization
    if org is None:
        org = (
            Organization.objects.filter(
                memberships__user=user,
                memberships__role="owner",
                kind="personal",
            )
            .order_by("id")
            .first()
        )
    return serialize_user_profile(user, org)


@profile_router.post("/me/avatar", response=AvatarUrlsOut, auth=JWTAuth())
def upload_avatar(request, file: UploadedFile = File(...)):
    """
    Handles avatar upload: validates, deletes old, resizes, uploads, updates DB.
    """
    max_size = 10 * 1024 * 1024
    if (file.size or 0) > max_size:
        raise HttpError(400, "Avatar file too large (max 10MB)")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HttpError(400, "Invalid file type. Only images allowed.")
    try:
        img_bytes = read_uploaded_file_bounded(file, max_bytes=max_size)
    except UploadTooLarge as exc:
        raise HttpError(400, "Avatar file too large (max 10MB)") from exc

    try:
        small_bytes, large_bytes = resize_avatar_images(img_bytes)
    except InvalidImageContent as exc:
        raise HttpError(400, str(exc)) from exc

    user = get_request_user(request)
    old_avatar_path = user.avatar_path
    token = uuid.uuid4().hex
    filename = f"avatars/users/{token}.webp"
    large_filename = f"avatars/users/{token}_lg.webp"
    uploaded: list[str] = []
    try:
        upload_to_storage(filename, small_bytes)
        uploaded.append(filename)
        upload_to_storage(large_filename, large_bytes)
        uploaded.append(large_filename)
        signed_urls = sign_avatar_urls(filename)
        with transaction.atomic():
            user.avatar_path = filename
            user.save(update_fields=["avatar_path", "updated_at"])
            if old_avatar_path:
                schedule_avatar_file_deletion(old_avatar_path)
    except Exception as exc:
        delete_storage_keys(uploaded)
        raise HttpError(503, "Avatar upload is temporarily unavailable.") from exc
    return signed_urls


@profile_router.delete("/me/avatar", response={204: None}, auth=JWTAuth())
def delete_avatar(request):
    user = get_request_user(request)
    old_avatar_path = user.avatar_path
    with transaction.atomic():
        user.avatar_path = None
        user.save(update_fields=["avatar_path", "updated_at"])
        if old_avatar_path:
            schedule_avatar_file_deletion(old_avatar_path)
    return Status(204, None)


@users_router.get("/{user_id}/avatar", response=AvatarUrlsOut, auth=JWTAuth())
def get_user_avatar(request, user_id: uuid.UUID):
    user = get_object_or_404(User, pk=user_id, is_active=True)
    if not user.avatar_path:
        raise HttpError(404, "Avatar not found.")
    return sign_avatar_urls(user.avatar_path)


@profile_router.get("/me", response=UserProfileOut, auth=JWTAuth())
def get_me(request):
    user = get_request_user(request)
    return serialize_profile_with_current_org(user)


@profile_router.patch("/me", response=UserProfileOut, auth=JWTAuth())
def update_me(request, data: UserProfileUpdate):
    user = get_request_user(request)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    user.save()
    return serialize_profile_with_current_org(user)


@profile_router.delete("/me", response={204: None}, auth=JWTAuth())
def delete_account(request, data: DeleteAccountSchema):
    user = get_request_user(request)
    if not user.check_password(data.password):
        raise HttpError(400, "Password is incorrect")
    try:
        delete_user_account(user)
    except ActiveOwnerRequiredError as exc:
        raise HttpError(409, str(exc)) from exc
    return Status(204, None)


@users_router.get(
    "/username-availability",
    response=UsernameCheckResponse,
    auth=JWTAuth(),
    throttle=[username_check_throttle],
)
def check_username(request, username: str = ""):
    username = username.strip()
    is_valid, reason = validate_username_value(username)
    if not is_valid:
        return UsernameCheckResponse(available=False, reason=reason)
    if User.objects.filter(username__iexact=username).exists():
        return UsernameCheckResponse(available=False, reason="Username already taken.")
    return UsernameCheckResponse(available=True)
