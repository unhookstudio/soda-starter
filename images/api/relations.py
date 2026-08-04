from typing import List
from uuid import UUID

from ninja import Status
from ninja.errors import HttpError

from core.authentication import JWTAuth
from core.utils.idempotency import run_idempotently
from core.utils.polymorphic import resolve_workspace_scoped_content_object
from images.api.common import logger, router
from images.api_schemas import BulkImageIdsIn, ImageIdsIn
from images.operations import (
    ImageNotFoundError,
    attach_images_to_object,
    detach_images_from_object,
)
from images.schemas import BulkAttachOut, BulkDetachOut, PolymorphicImageRelationOut
from images.serializers import serialize_image_relation
from images.throttles import bulk_attach_throttle, bulk_detach_throttle


@router.post(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/images",
    response=List[PolymorphicImageRelationOut],
    auth=JWTAuth(),
)
def attach_images(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    data: ImageIdsIn,
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
        result = attach_images_to_object(
            organization_id=org.id,
            target=obj,
            content_type=ct,
            image_ids=data.image_ids,
        )
    except ImageNotFoundError as exc:
        raise HttpError(404, str(exc)) from exc
    for relation in result.relations:
        if relation.image_id in result.attached_image_ids:
            logger.info(
                "audit:image_attach org=%s user=%s app=%s model=%s obj=%s image=%s rel=%s",
                org.id,
                getattr(user, "id", None),
                app_label,
                model,
                object_id,
                relation.image_id,
                relation.id,
            )
    return [serialize_image_relation(relation) for relation in result.relations]


@router.post(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/images/bulk-attach",
    response=BulkAttachOut,
    auth=JWTAuth(),
    throttle=[bulk_attach_throttle],
)
def bulk_attach_images(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    data: BulkImageIdsIn,
):
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    resolved.scope.require_write()
    org = resolved.organization
    obj = resolved.obj
    ct = resolved.content_type
    user = resolved.scope.user
    requested_ids = list(dict.fromkeys(data.image_ids))

    def perform_attach() -> tuple[int, dict]:
        try:
            result = attach_images_to_object(
                organization_id=org.id,
                target=obj,
                content_type=ct,
                image_ids=requested_ids,
            )
        except ImageNotFoundError as exc:
            raise HttpError(
                403, "One or more images do not belong to this organization"
            ) from exc
        if result.attached_image_ids:
            logger.info(
                "audit:image_bulk_attach org=%s user=%s app=%s model=%s "
                "obj=%s attached=%s",
                org.id,
                getattr(user, "id", None),
                app_label,
                model,
                object_id,
                result.attached_image_ids,
            )
        return 200, {"attached": result.attached_image_ids}

    status, response_data = run_idempotently(request, perform_attach)
    return Status(status, response_data) if status != 200 else response_data


@router.post(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/images/bulk-detach",
    response=BulkDetachOut,
    auth=JWTAuth(),
    throttle=[bulk_detach_throttle],
)
def bulk_detach_images(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    data: BulkImageIdsIn,
):
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    resolved.scope.require_write()
    org = resolved.organization
    obj = resolved.obj
    ct = resolved.content_type
    user = resolved.scope.user

    def perform_detach() -> tuple[int, dict]:
        detached = detach_images_from_object(
            target=obj,
            content_type=ct,
            image_ids=data.image_ids,
        )
        if detached:
            logger.info(
                "audit:image_bulk_detach org=%s user=%s app=%s model=%s "
                "obj=%s detached=%s",
                org.id,
                getattr(user, "id", None),
                app_label,
                model,
                object_id,
                detached,
            )
        return 200, {"detached": detached}

    status, response_data = run_idempotently(request, perform_detach)
    return Status(status, response_data) if status != 200 else response_data


@router.delete(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/images/{image_id}",
    auth=JWTAuth(),
    response={204: None},
)
def remove_image_from_object(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    image_id: UUID,
):
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    resolved.scope.require_write()
    org = resolved.organization
    obj = resolved.obj
    ct = resolved.content_type
    user = resolved.scope.user
    detached = detach_images_from_object(
        target=obj,
        content_type=ct,
        image_ids=[image_id],
    )
    if not detached:
        raise HttpError(404, "Image relation not found")
    logger.info(
        "audit:image_detach org=%s user=%s app=%s model=%s obj=%s image=%s",
        org.id,
        getattr(user, "id", None),
        app_label,
        model,
        object_id,
        image_id,
    )
    return Status(204, None)
