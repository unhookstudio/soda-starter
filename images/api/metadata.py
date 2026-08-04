from uuid import UUID

from django.shortcuts import get_object_or_404

from core.authentication import JWTAuth
from images.api.common import router
from images.models import Image
from images.schemas import ImageOut, ImagePatchIn
from images.serializers import serialize_image
from organizations.scope import resolve_workspace_scope


@router.patch(
    "/workspaces/{workspace_id}/images/{image_id}",
    response=ImageOut,
    auth=JWTAuth(),
)
def edit_image_metadata(
    request, workspace_id: UUID, image_id: UUID, data: ImagePatchIn
):
    scope = resolve_workspace_scope(request, workspace_id).require_write()
    image = get_object_or_404(Image, id=image_id, organization=scope.workspace)
    payload = data.model_dump(exclude_unset=True)
    for field in ("title", "description", "alt_text"):
        if field in payload:
            setattr(image, field, payload[field])
    image.save(update_fields=[*payload, "updated_at"])
    return serialize_image(image)
