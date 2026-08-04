import logging

from django.conf import settings
from ninja import Router, Status
from ninja.errors import HttpError
from ninja_jwt.schema import TokenVerifyInputSchema

from accounts.models import PendingEmailChange
from accounts.operations import (
    AccountOperationConflict,
    AccountOperationError,
    cancel_pending_registration,
)
from accounts.operations import change_password as change_password_operation
from accounts.operations import (
    confirm_email_change,
)
from accounts.operations import (
    confirm_password_reset as confirm_password_reset_operation,
)
from accounts.operations import (
    confirm_registration,
)
from accounts.operations import request_email_change as request_email_change_operation
from accounts.operations import (
    rotate_password_reset,
    rotate_pending_registration,
)
from accounts.schemas import (
    ChangePasswordSchema,
    EmailSchema,
    EmailUpdateSchema,
    LogoutInputSchema,
    PasswordResetRequestSchema,
    PasswordResetSchema,
    PendingActionOut,
    ReauthenticationResponse,
    RegisterSchema,
    RegistrationVerificationSchema,
    TokenInputSchema,
    TokenPairInputSchema,
    TokenPairOut,
    TokenRefreshInputSchema,
)
from accounts.services import (
    authenticate_for_token,
    issue_token_pair,
    revoke_all_sessions,
    revoke_session_from_refresh,
    rotate_token_pair,
    send_templated_email,
)
from accounts.throttles import (
    email_change_throttle,
    login_throttle,
    logout_throttle,
    password_reset_confirm_throttle,
    password_reset_request_throttle,
    refresh_throttle,
    register_throttle,
    token_verify_throttle,
    verification_throttle,
)
from accounts.validation import normalize_and_validate_email
from core.api_errors import ApiError
from core.authentication import JWTAuth
from core.utils.auth_utils import get_request_user

EMAIL_VERIFICATION_EXPIRY_HOURS = 12
EMAIL_CHANGE_TOKEN_EXPIRY_HOURS = 24
PASSWORD_RESET_TOKEN_EXPIRY_HOURS = 2
REGISTRATION_RESPONSE_DETAIL = (
    "If the address can be registered, a verification email has been sent."
)
PASSWORD_RESET_RESPONSE_DETAIL = (
    "If the email exists, a password reset link has been sent."
)

auth_router = Router(tags=["authentication"])
logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")


def token_response(access: str, refresh: str) -> TokenPairOut:
    return TokenPairOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=int(settings.NINJA_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
    )


@auth_router.post(
    "/login",
    response=TokenPairOut,
    throttle=[login_throttle],
)
def obtain_token_pair(request, data: TokenPairInputSchema):
    try:
        user, is_verified = authenticate_for_token(data.email, data.password)
    except HttpError:
        audit_logger.warning(
            "audit:login_failed ip=%s",
            request.META.get("REMOTE_ADDR"),
        )
        raise
    if not is_verified:
        raise ApiError(
            403,
            "email_not_verified",
            "Verify the email address before logging in.",
        )

    access, refresh = issue_token_pair(user, device_name=data.device_name or "")
    audit_logger.info("audit:login_succeeded user=%s", user.pk)
    return token_response(access, refresh)


@auth_router.post(
    "/refresh",
    response=TokenPairOut,
    throttle=[refresh_throttle],
)
def refresh_token(request, data: TokenRefreshInputSchema):
    access, refresh = rotate_token_pair(data.refresh_token)
    return token_response(access, refresh)


@auth_router.post(
    "/token/verify",
    response={204: None},
    throttle=[token_verify_throttle],
)
def verify_token(request, data: TokenVerifyInputSchema):
    data.to_response_schema()
    return Status(204, None)


def send_verification_email(email: str, token: str) -> None:
    verification_link = f"{settings.FRONTEND_URL}/verify-registration#token={token}"
    try:
        send_templated_email(
            "registration_verification.txt",
            {
                "project_name": settings.PROJECT_NAME,
                "user_display_name": email,
                "verification_link": verification_link,
                "expiry_hours": EMAIL_VERIFICATION_EXPIRY_HOURS,
            },
            [email],
        )
    except Exception as exc:
        logger.warning("accounts:verification_email_failed")
        raise HttpError(500, "Failed to send verification email.") from exc


def create_pending_registration(email: str) -> None:
    delivery = rotate_pending_registration(
        email=email,
        expiry_hours=EMAIL_VERIFICATION_EXPIRY_HOURS,
    )
    if delivery is None:
        return
    try:
        send_verification_email(delivery.email, delivery.raw_token)
    except HttpError:
        cancel_pending_registration(
            pending_id=delivery.pending_id,
            token_hash=delivery.token_hash,
        )
        raise


@auth_router.post(
    "/register",
    response={202: PendingActionOut},
    throttle=[register_throttle],
)
def register(request, data: RegisterSchema):
    email = data.email
    create_pending_registration(email)

    return Status(202, PendingActionOut(status="verification_pending"))


@auth_router.post("/verify-registration", response=TokenPairOut)
def verify_registration(request, data: RegistrationVerificationSchema):
    try:
        user = confirm_registration(raw_token=data.token, password=data.password)
    except AccountOperationConflict as exc:
        raise HttpError(409, str(exc)) from exc
    except AccountOperationError as exc:
        raise HttpError(400, str(exc)) from exc

    access, refresh = issue_token_pair(user, device_name=data.device_name or "")
    return token_response(access, refresh)


@auth_router.post(
    "/resend-verification",
    response={202: PendingActionOut},
    throttle=[verification_throttle],
)
def resend_verification(request, data: EmailSchema):
    try:
        email = normalize_and_validate_email(data.email)
    except ValueError:
        return Status(202, PendingActionOut(status="verification_pending"))
    create_pending_registration(email)

    return Status(202, PendingActionOut(status="verification_pending"))


@auth_router.post("/logout", response={204: None}, throttle=[logout_throttle])
def logout(request, data: LogoutInputSchema):
    revoke_session_from_refresh(data.refresh_token)
    audit_logger.info("audit:session_logged_out")
    return Status(204, None)


@auth_router.post("/logout-all", response={204: None}, auth=JWTAuth())
def logout_all(request):
    revoke_all_sessions(get_request_user(request))
    audit_logger.info("audit:all_sessions_logged_out")
    return Status(204, None)


@auth_router.patch("/me/password", auth=JWTAuth(), response=ReauthenticationResponse)
def change_password(request, data: ChangePasswordSchema):
    user = get_request_user(request)
    try:
        change_password_operation(
            user_id=user.pk,
            old_password=data.old_password,
            new_password=data.new_password,
        )
    except AccountOperationError as exc:
        raise HttpError(400, str(exc)) from exc
    return ReauthenticationResponse()


@auth_router.patch(
    "/me/email",
    response={202: PendingActionOut},
    auth=JWTAuth(),
    throttle=[email_change_throttle],
)
def request_email_change(request, data: EmailUpdateSchema):
    user = get_request_user(request)
    try:
        delivery = request_email_change_operation(
            user_id=user.pk,
            new_email=data.email,
            current_password=data.current_password,
            expiry_hours=EMAIL_CHANGE_TOKEN_EXPIRY_HOURS,
        )
    except AccountOperationError as exc:
        raise HttpError(400, str(exc)) from exc

    verification_link = (
        f"{settings.FRONTEND_URL}/verify-email-change#token={delivery.raw_token}"
    )
    try:
        send_templated_email(
            "email_change_requested.txt",
            {
                "project_name": settings.PROJECT_NAME,
                "user_display_name": delivery.display_name,
                "old_email": delivery.old_email,
                "new_email": delivery.new_email,
            },
            [delivery.old_email],
        )
        send_templated_email(
            "email_change_verification.txt",
            {
                "project_name": settings.PROJECT_NAME,
                "user_display_name": delivery.display_name,
                "new_email": delivery.new_email,
                "verification_link": verification_link,
            },
            [delivery.new_email],
        )
    except Exception as exc:
        PendingEmailChange.objects.filter(
            pk=delivery.pending_id,
            token=delivery.token_hash,
        ).delete()
        logger.warning(
            "accounts:email_change_verification_failed user=%s",
            delivery.user_id,
        )
        raise HttpError(500, "Failed to send verification email.") from exc
    audit_logger.info("audit:email_change_requested user=%s", delivery.user_id)
    return Status(202, PendingActionOut(status="verification_pending"))


@auth_router.post("/email/verify", response=ReauthenticationResponse)
def verify_email_change(request, data: TokenInputSchema):
    try:
        result = confirm_email_change(raw_token=data.token)
    except AccountOperationError as exc:
        raise HttpError(400, str(exc)) from exc

    notification_context = {
        "project_name": settings.PROJECT_NAME,
        "old_email": result.old_email,
        "new_email": result.new_email,
    }
    for recipient in (result.old_email, result.new_email):
        try:
            send_templated_email(
                "email_change_completed.txt", notification_context, [recipient]
            )
        except Exception:
            logger.exception(
                "accounts:email_change_completion_notice_failed user=%s",
                result.user_id,
            )
    return ReauthenticationResponse()


@auth_router.post(
    "/password-reset/request",
    response={202: PendingActionOut},
    throttle=[password_reset_request_throttle],
)
def request_password_reset(request, data: PasswordResetRequestSchema):
    """
    Send a reset email when the account exists; always return a generic response.
    """
    try:
        email = normalize_and_validate_email(data.email)
    except ValueError:
        return Status(202, PendingActionOut(status="reset_pending"))
    delivery = rotate_password_reset(
        email=email,
        expiry_hours=PASSWORD_RESET_TOKEN_EXPIRY_HOURS,
    )
    if delivery is None:
        return Status(202, PendingActionOut(status="reset_pending"))
    reset_link = f"{settings.FRONTEND_URL}/reset-password#token={delivery.raw_token}"
    try:
        send_templated_email(
            "password_reset.txt",
            {
                "project_name": settings.PROJECT_NAME,
                "user_display_name": delivery.display_name,
                "reset_link": reset_link,
            },
            [delivery.email],
        )
    except Exception:
        logger.exception(
            "accounts:password_reset_email_failed user=%s", delivery.user_id
        )
    return Status(202, PendingActionOut(status="reset_pending"))


@auth_router.post(
    "/password-reset/confirm",
    response=ReauthenticationResponse,
    throttle=[password_reset_confirm_throttle],
)
def confirm_password_reset(request, data: PasswordResetSchema):
    """
    Reset password using token.
    """
    try:
        confirm_password_reset_operation(
            raw_token=data.token,
            new_password=data.new_password,
        )
    except AccountOperationError as exc:
        raise HttpError(400, str(exc)) from exc
    return ReauthenticationResponse()
