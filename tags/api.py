import logging
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router, Status
from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from core.authentication import JWTAuth
from core.utils.polymorphic import resolve_workspace_scoped_content_object
from organizations.scope import resolve_workspace_scope
from tags.models import Tag
from tags.schemas import (
    RemovedCountResponse,
    TagAssignment,
    TagCreate,
    TagOut,
    TagUpdate,
)
from tags.services import (
    assign_tags_to_object,
)
from tags.services import create_tag as create_tag_service
from tags.services import delete_tag as delete_tag_service
from tags.services import (
    rename_tag,
    unassign_tags_from_object,
)

# Module-level router and logger
router = Router(tags=["tags"])
logger = logging.getLogger("audit")

TAG_ASSIGN_DESCRIPTION = (
    "Assign up to 50 tag names to an organization-scoped object. "
    "Missing tags are created in that organization."
)
TAG_OBJECT_DESCRIPTION = "Manage tags attached to a polymorphic object identified by app label, model name, and object id."


@router.get(
    "/workspaces/{workspace_id}/tags",
    response=list[TagOut],
    auth=JWTAuth(),
    summary="List organization tags",
    description="Return the paginated tag list for an organization. Supports ordering by name or id.",
)
@paginate(LimitOffsetPagination)
def list_tags(
    request,
    workspace_id: UUID,
    q: str | None = None,
    ordering: str | None = None,
):
    scope = resolve_workspace_scope(request, workspace_id)
    ordering_map = {
        None: "name",
        "name": "name",
        "-name": "-name",
        "id": "id",
        "-id": "-id",
    }
    if ordering not in ordering_map:
        raise HttpError(400, "Invalid ordering. Allowed: name, -name, id, -id")
    queryset = Tag.objects.filter(organization=scope.workspace)
    if q:
        queryset = queryset.filter(name__icontains=q)
    return queryset.order_by(ordering_map[ordering])


@router.get(
    "/workspaces/{workspace_id}/tags/{tag_id}",
    response=TagOut,
    auth=JWTAuth(),
    summary="Get tag",
    description="Return one workspace tag by UUID.",
)
def get_tag(request, workspace_id: UUID, tag_id: UUID):
    scope = resolve_workspace_scope(request, workspace_id)
    tag = get_object_or_404(Tag, pk=tag_id, organization=scope.workspace)
    return TagOut.model_validate(tag)


@router.post(
    "/workspaces/{workspace_id}/tags",
    response={201: TagOut},
    auth=JWTAuth(),
    summary="Create tag",
    description="Create a tag in an organization. Tag names must be unique within that organization.",
)
def create_tag(request, workspace_id: UUID, data: TagCreate):
    scope = resolve_workspace_scope(request, workspace_id).require_write()
    org = scope.workspace
    user = scope.user
    name = data.name
    tag = create_tag_service(org, name)
    logger.info(
        "audit:tag_create org=%s user=%s tag_id=%s name=%s",
        org.id,
        getattr(user, "id", None),
        tag.id,
        tag.name,
    )
    return Status(201, tag)


@router.get(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/tags",
    response=list[TagOut],
    auth=JWTAuth(),
    summary="List object tags",
    description=TAG_OBJECT_DESCRIPTION,
)
@paginate(LimitOffsetPagination)
def list_tags_for_object(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    ordering: str | None = None,
):
    """List tags for a specific object (paginated)."""
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    org = resolved.organization
    ct = resolved.content_type

    ordering_map = {
        None: "name",
        "name": "name",
        "-name": "-name",
        "id": "id",
        "-id": "-id",
    }
    if ordering not in ordering_map:
        raise HttpError(400, "Invalid ordering. Allowed: name, -name, id, -id")
    qs = (
        Tag.objects.filter(
            organization=org,
            taggeditem__content_type=ct,
            taggeditem__object_id=object_id,
        )
        .distinct()
        .order_by(ordering_map[ordering])
    )
    return qs


@router.post(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/tags",
    response=list[TagOut],
    auth=JWTAuth(),
    summary="Assign tags to object",
    description=TAG_ASSIGN_DESCRIPTION,
)
def assign_tags(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    data: TagAssignment,
):
    """Assign tags by name to an object. Creates tags if missing within the organization.

    Example payload:
    ["vip", "newsletter"]
    """
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    resolved.scope.require_write()
    org = resolved.organization
    ct = resolved.content_type
    user = resolved.scope.user

    result = assign_tags_to_object(org, ct, object_id, data.root)
    for tag_id in result.newly_assigned_tag_ids:
        logger.info(
            "audit:tag_assign org=%s user=%s app=%s model=%s obj=%s tag_id=%s",
            org.id,
            getattr(user, "id", None),
            app_label,
            model,
            object_id,
            tag_id,
        )

    return [TagOut.model_validate(tag) for tag in result.tags]


@router.patch(
    "/workspaces/{workspace_id}/tags/{tag_id}",
    response=TagOut,
    auth=JWTAuth(),
    summary="Update tag",
    description="Rename an organization tag and regenerate its slug.",
)
def update_tag(request, workspace_id: UUID, tag_id: UUID, data: TagUpdate):
    scope = resolve_workspace_scope(request, workspace_id).require_write()
    org = scope.workspace
    tag = get_object_or_404(Tag, id=tag_id, organization=org)
    if data.name is not None:
        tag = rename_tag(tag, data.name)
    return TagOut.model_validate(
        {
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "organization_id": tag.organization_id,
        }
    )


@router.delete(
    "/workspaces/{workspace_id}/tags/{tag_id}",
    response={204: None},
    auth=JWTAuth(),
    summary="Delete tag",
    description="Delete one organization tag by id.",
)
def delete_tag(request, workspace_id: UUID, tag_id: UUID):
    scope = resolve_workspace_scope(request, workspace_id).require_write()
    org = scope.workspace
    user = scope.user
    tag = get_object_or_404(Tag, id=tag_id, organization=org)
    deleted_tag_id = delete_tag_service(tag)
    logger.info(
        "audit:tag_delete org=%s user=%s tag_id=%s",
        org.id,
        getattr(user, "id", None),
        deleted_tag_id,
    )
    return Status(204, None)


@router.delete(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/tags",
    response=RemovedCountResponse,
    auth=JWTAuth(),
    summary="Bulk unassign object tags",
    description="Remove multiple tag ids from an organization-scoped object.",
)
def unassign_tags(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    tag_ids: list[UUID],
):
    """Bulk unassign tags from an object.

    Accepts a JSON array of tag IDs. Example payload:
    [1, 4, 7]
    """
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    resolved.scope.require_write()
    org = resolved.organization
    ct = resolved.content_type
    user = resolved.scope.user

    result = unassign_tags_from_object(
        organization=org,
        content_type=ct,
        object_id=object_id,
        tag_ids=tag_ids,
    )
    if result.removed_count:
        logger.info(
            "audit:tag_bulk_unassign org=%s user=%s app=%s model=%s obj=%s tags=%s",
            org.id,
            getattr(user, "id", None),
            app_label,
            model,
            object_id,
            tag_ids,
        )
    return RemovedCountResponse(removed_count=result.removed_count)


@router.delete(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/tags/{tag_id}",
    response={204: None},
    auth=JWTAuth(),
    summary="Unassign object tag by slug",
    description="Remove one tag from an object by tag slug. Missing tags are treated as already removed.",
)
def unassign_tag(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    tag_id: UUID,
):
    """Idempotently unassign one tag from an object."""
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    resolved.scope.require_write()
    org = resolved.organization
    ct = resolved.content_type
    user = resolved.scope.user

    result = unassign_tags_from_object(
        organization=org,
        content_type=ct,
        object_id=object_id,
        tag_ids=[tag_id],
    )
    if result.removed_count:
        logger.info(
            "audit:tag_unassign org=%s user=%s app=%s model=%s obj=%s tag_id=%s",
            org.id,
            getattr(user, "id", None),
            app_label,
            model,
            object_id,
            tag_id,
        )
    return Status(204, None)
