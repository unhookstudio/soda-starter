from django.db import transaction
from ninja import Router

from core.api_errors import ApiError
from core.authentication import JWTAuth
from core.utils.auth_utils import get_request_user
from organizations.models import Membership
from organizations.schemas import CurrentWorkspaceIn, WorkspaceOut
from organizations.scope import resolve_workspace_scope

workspace_router = Router(tags=["workspaces"])


def serialize_workspace(membership: Membership) -> WorkspaceOut:
    workspace = membership.organization
    return WorkspaceOut(
        id=workspace.pk,
        name=workspace.name,
        slug=workspace.slug,
        kind=workspace.kind,
        role=membership.role,
        creator_id=workspace.creator_id,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


def user_workspace_memberships(user):
    return Membership.objects.select_related("organization").filter(user=user)


@workspace_router.get("", response=list[WorkspaceOut], auth=JWTAuth())
def list_workspaces(request):
    user = get_request_user(request)
    memberships = user_workspace_memberships(user).order_by(
        "organization__name", "organization_id"
    )
    return [serialize_workspace(membership) for membership in memberships]


def current_membership(user) -> Membership | None:
    memberships = user_workspace_memberships(user)
    membership = memberships.filter(
        organization_id=user.current_organization_id
    ).first()
    if membership is not None:
        return membership
    return memberships.order_by(
        "organization__kind", "organization__created_at"
    ).first()


@workspace_router.get("/current", response=WorkspaceOut, auth=JWTAuth())
def get_current_workspace(request):
    user = get_request_user(request)
    membership = current_membership(user)
    if membership is None:
        raise ApiError(404, "workspace_not_found", "No workspace is available.")
    if user.current_organization_id != membership.organization_id:
        user.current_organization_id = membership.organization_id
        user.save(update_fields=["current_organization", "updated_at"])
    return serialize_workspace(membership)


@workspace_router.put("/current", response=WorkspaceOut, auth=JWTAuth())
@transaction.atomic
def set_current_workspace(request, data: CurrentWorkspaceIn):
    user = get_request_user(request)
    scope = resolve_workspace_scope(request, data.workspace_id)
    if scope.membership is None:
        raise ApiError(
            403,
            "workspace_membership_required",
            "Only a workspace member can make it current.",
        )
    user.current_organization = scope.workspace
    user.save(update_fields=["current_organization", "updated_at"])
    return serialize_workspace(scope.membership)
