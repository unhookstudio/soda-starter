import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import File, Router, UploadedFile
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

from .schemas import UsernameCheckResponse, UserProfileOut, UserProfileUpdate
from .serializers import serialize_user_profile
from .throttles import username_check_throttle
from .username import router as username_router
from .username_validation import validate_username_value

# You can add more user/profile endpoints here as needed
users_router = Router()

users_router.add_router("/", username_router, tags=["users"])


def serialize_profile_with_personal_org(user: User) -> UserProfileOut:
    org = (
        Organization.objects.filter(
            memberships__user=user,
            memberships__role="owner",
            type="personal",
        )
        .order_by("id")
        .first()
    )
    return serialize_user_profile(user, org)


@users_router.post("/avatar", response=AvatarUrlsOut, auth=JWTAuth())
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


@users_router.delete("/avatar", auth=JWTAuth())
def delete_avatar(request):
    user = get_request_user(request)
    old_avatar_path = user.avatar_path
    with transaction.atomic():
        user.avatar_path = None
        user.save(update_fields=["avatar_path", "updated_at"])
        if old_avatar_path:
            schedule_avatar_file_deletion(old_avatar_path)
    return {"detail": "Avatar deleted."}


@users_router.get("/{slug}/avatar", response=AvatarUrlsOut, auth=JWTAuth())
def get_user_avatar(request, slug: str):
    user = get_object_or_404(User, slug=slug, is_active=True)
    if not user.avatar_path:
        raise HttpError(404, "Avatar not found.")
    return sign_avatar_urls(user.avatar_path)


@users_router.get("/me", response=UserProfileOut, auth=JWTAuth())
def get_me(request):
    user = get_request_user(request)
    return serialize_profile_with_personal_org(user)


@users_router.patch("/me", response=UserProfileOut, auth=JWTAuth())
def update_me(request, data: UserProfileUpdate):
    user = get_request_user(request)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    user.save()
    return serialize_profile_with_personal_org(user)


@users_router.get(
    "/check_username",
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
