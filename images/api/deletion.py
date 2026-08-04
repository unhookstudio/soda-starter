from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Status
from ninja.errors import HttpError

from core.authentication import JWTAuth
from core.utils.idempotency import run_idempotently
from images.api.common import logger, router
from images.api_schemas import BulkDeleteIn, BulkDeleteOut
from images.models import Image
from images.services import delete_image_record
from images.throttles import bulk_delete_throttle
from organizations.scope import resolve_workspace_scope


@router.post(
    "/workspaces/{workspace_id}/images/bulk-delete",
    response=BulkDeleteOut,
    auth=JWTAuth(),
    throttle=[bulk_delete_throttle],
)
def bulk_delete_images(request, workspace_id: UUID, data: BulkDeleteIn):
    scope = resolve_workspace_scope(request, workspace_id).require_write()
    org = scope.workspace
    user = scope.user

    def perform_delete() -> tuple[int, dict]:
        ids = data.image_ids
        if not ids:
            raise HttpError(400, "No ids provided for deletion")

        deleted_ids = []
        failed = []
        for img_id in ids:
            try:
                image = Image.objects.get(id=img_id, organization=org)
            except Image.DoesNotExist:
                failed.append({"id": img_id, "reason": "not found"})
                continue

            try:
                delete_image_record(image)
            except Exception:
                failed.append({"id": img_id, "reason": "delete failed"})
                continue

            deleted_ids.append(img_id)
            logger.info(
                "audit:image_delete org=%s user=%s image=%s",
                org.id,
                getattr(user, "id", None),
                img_id,
            )

        return 200, {"deleted": deleted_ids, "failed": failed}

    try:
        status, data = run_idempotently(request, perform_delete)
        return Status(status, data)
    except HttpError:
        raise
    except Exception as exc:
        logger.exception("images:bulk_delete_failed org=%s", org.id)
        raise HttpError(500, "Image deletion failed.") from exc


@router.delete(
    "/workspaces/{workspace_id}/images/{image_id}", auth=JWTAuth(), response={204: None}
)
def delete_image(request, workspace_id: UUID, image_id: UUID):
    scope = resolve_workspace_scope(request, workspace_id).require_write()
    org = scope.workspace
    user = scope.user
    image = get_object_or_404(Image, id=image_id, organization=org)
    delete_image_record(image)
    logger.info(
        "audit:image_delete org=%s user=%s image=%s",
        org.id,
        getattr(user, "id", None),
        image_id,
    )
    return Status(204, None)
