from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from django.http import HttpRequest

from accounts.models import User
from core.api_errors import ApiError
from core.utils.auth_utils import get_request_user
from organizations.models import Membership, Organization

audit_logger = logging.getLogger("audit")


def is_platform_admin(user: User) -> bool:
    """Staff status alone never grants cross-workspace application access."""
    return bool(getattr(user, "is_superuser", False))


@dataclass(frozen=True)
class WorkspaceScope:
    user: User
    workspace: Organization
    membership: Membership | None = None

    @property
    def role(self) -> str | None:
        if is_platform_admin(self.user):
            return "platform_admin"
        return self.membership.role if self.membership else None

    @property
    def can_admin(self) -> bool:
        return is_platform_admin(self.user) or self.role in {"admin", "owner"}

    @property
    def can_write(self) -> bool:
        return is_platform_admin(self.user) or self.role in {
            "member",
            "admin",
            "owner",
        }

    def require_admin(self) -> "WorkspaceScope":
        if not self.can_admin:
            raise ApiError(
                403,
                "workspace_admin_required",
                "A workspace administrator or owner is required.",
            )
        return self

    def require_write(self) -> "WorkspaceScope":
        if not self.can_write:
            raise ApiError(
                403,
                "workspace_write_forbidden",
                "You cannot modify this workspace.",
            )
        return self


def resolve_workspace_scope(request: HttpRequest, workspace_id: UUID) -> WorkspaceScope:
    user = get_request_user(request)
    membership = (
        Membership.objects.select_related("organization")
        .filter(
            user=user,
            organization_id=workspace_id,
        )
        .first()
    )
    if membership is not None:
        return WorkspaceScope(
            user=user,
            workspace=membership.organization,
            membership=membership,
        )

    if not is_platform_admin(user):
        raise ApiError(404, "workspace_not_found", "Workspace not found.")

    try:
        workspace = Organization.objects.get(pk=workspace_id)
    except Organization.DoesNotExist as exc:
        raise ApiError(404, "workspace_not_found", "Workspace not found.") from exc

    audit_logger.info(
        "audit:platform_admin_workspace_access",
        extra={
            "event": "platform_admin_workspace_access",
            "workspace": str(workspace.pk),
            "user": str(user.pk),
            "method": getattr(request, "method", "UNKNOWN"),
            "path": getattr(request, "path", ""),
            "access": (
                "read"
                if getattr(request, "method", "GET") in {"GET", "HEAD", "OPTIONS"}
                else "write"
            ),
        },
    )
    return WorkspaceScope(user=user, workspace=workspace)


def resolve_write_workspace_scope(
    request: HttpRequest, workspace_id: UUID
) -> WorkspaceScope:
    return resolve_workspace_scope(request, workspace_id).require_write()


def resolve_admin_workspace_scope(
    request: HttpRequest, workspace_id: UUID
) -> WorkspaceScope:
    return resolve_workspace_scope(request, workspace_id).require_admin()
