from uuid import UUID

from ninja import Status
from ninja.errors import HttpError

from core.authentication import JWTAuth
from core.utils.polymorphic import resolve_workspace_scoped_content_object
from images.api.common import logger, router
from images.api_schemas import ReorderIn
from images.operations import (
    ImageNotFoundError,
    ImageOperationError,
    ImageOwnershipError,
    reorder_object_images,
    set_object_cover_image,
    unset_object_cover_image,
)
from images.schemas import SetCoverIn


@router.put(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/images/order",
    response={204: None},
    auth=JWTAuth(),
)
def reorder_images(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    data: ReorderIn,
):
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    resolved.scope.require_write()
    org = resolved.organization
    obj = resolved.obj
    ct = resolved.content_type
    user = resolved.scope.user

    provided = data.image_ids
    try:
        reorder_object_images(
            organization_id=org.id,
            target=obj,
            content_type=ct,
            image_ids=provided,
        )
    except ImageOwnershipError as exc:
        raise HttpError(403, str(exc)) from exc
    except ImageOperationError as exc:
        raise HttpError(400, str(exc)) from exc
    logger.info(
        "audit:image_reorder org=%s user=%s app=%s model=%s obj=%s images=%s",
        org.id,
        getattr(user, "id", None),
        app_label,
        model,
        object_id,
        provided,
    )
    return Status(204, None)


@router.put(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/cover-image",
    response={204: None},
    auth=JWTAuth(),
)
def set_cover_image(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    data: SetCoverIn,
):
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    resolved.scope.require_write()
    org = resolved.organization
    obj = resolved.obj
    ct = resolved.content_type
    user = resolved.scope.user

    try:
        set_object_cover_image(
            organization_id=org.id,
            target=obj,
            content_type=ct,
            image_id=data.image_id,
        )
    except ImageNotFoundError as exc:
        raise HttpError(404, str(exc)) from exc

    logger.info(
        "audit:image_set_cover org=%s user=%s app=%s model=%s obj=%s image=%s",
        org.id,
        getattr(user, "id", None),
        app_label,
        model,
        object_id,
        data.image_id,
    )
    return Status(204, None)


@router.delete(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/cover-image",
    response={204: None},
    auth=JWTAuth(),
)
def unset_cover_image(
    request, workspace_id: UUID, app_label: str, model: str, object_id: UUID
):
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    resolved.scope.require_write()
    org = resolved.organization
    obj = resolved.obj
    ct = resolved.content_type
    user = resolved.scope.user

    unset_object_cover_image(target=obj, content_type=ct)

    logger.info(
        "audit:image_unset_cover org=%s user=%s app=%s model=%s obj=%s",
        org.id,
        getattr(user, "id", None),
        app_label,
        model,
        object_id,
    )
    return Status(204, None)
