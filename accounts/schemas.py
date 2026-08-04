from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Field, Schema
from pydantic import ConfigDict

from accounts.validation import AccountEmail, GenericEmailInput


class UnverifiedUserSchema(Schema):
    detail: str
    email_verified: bool = False


class CustomTokenOutputSchema(Schema):
    access: str
    refresh: str
    email: str


class TokenRefreshInputSchema(Schema):
    refresh: str
    model_config = ConfigDict(extra="forbid")


class TokenRefreshOutputSchema(Schema):
    access: str
    refresh: str


class LogoutInputSchema(Schema):
    refresh: str
    model_config = ConfigDict(extra="forbid")


class TokenPairInputSchema(Schema):
    email: AccountEmail
    password: str
    device_name: Optional[str] = Field(None, max_length=120)
    model_config = ConfigDict(extra="forbid")


class RegisterSchema(Schema):
    email: AccountEmail
    model_config = ConfigDict(extra="forbid")


class RegistrationVerificationSchema(Schema):
    token: str = Field(min_length=8, max_length=128)
    password: str
    device_name: Optional[str] = Field(None, max_length=120)
    model_config = ConfigDict(extra="forbid")


class ChangePasswordSchema(Schema):
    old_password: str
    new_password: str
    model_config = ConfigDict(extra="forbid")


class ReauthenticationResponse(Schema):
    detail: str
    reauthentication_required: bool = True


class DeleteAccountSchema(Schema):
    password: str
    model_config = ConfigDict(extra="forbid")


class EmailUpdateSchema(Schema):
    email: AccountEmail
    current_password: str
    model_config = ConfigDict(extra="forbid")


class EmailSchema(Schema):
    email: GenericEmailInput
    model_config = ConfigDict(extra="forbid")


class TokenInputSchema(Schema):
    token: str = Field(min_length=8, max_length=128)
    model_config = ConfigDict(extra="forbid")


class PasswordResetRequestSchema(Schema):
    email: GenericEmailInput
    model_config = ConfigDict(extra="forbid")


class PasswordResetSchema(Schema):
    token: str
    new_password: str
    model_config = ConfigDict(extra="forbid")


class UserProfileOut(Schema):
    id: UUID
    email: str
    first_name: str = Field(..., max_length=120)
    last_name: str = Field(..., max_length=120)
    username: str = Field(..., max_length=50)
    slug: str
    org_name: str
    org_slug: str
    location: Optional[str]
    about: Optional[str]
    has_avatar: bool
    notification_preferences: Optional[dict]
    theme: str
    locale: str
    current_workspace_id: Optional[UUID] = None
    finished_onboarding: bool
    email_verified: bool
    created_at: Optional[datetime]


class UserProfileUpdate(Schema):
    first_name: Optional[str] = Field(None, max_length=120)
    last_name: Optional[str] = Field(None, max_length=120)
    location: Optional[str] = None
    about: Optional[str] = None
    theme: Optional[str] = Field(None, pattern="^(system|light|dark)$")
    locale: Optional[str] = Field(
        None,
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    model_config = ConfigDict(extra="forbid")


class UsernameCheckResponse(Schema):
    available: bool
    reason: Optional[str] = None
