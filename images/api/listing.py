from typing import List
from uuid import UUID

from ninja.errors import HttpError
from ninja.pagination import LimitOffsetPagination, paginate

from core.authentication import JWTAuth
from core.utils.polymorphic import resolve_workspace_scoped_content_object
from images.api.common import router
from images.models import Image, PolymorphicImageRelation
from images.schemas import ImageOut, PolymorphicImageRelationOut
from images.serializers import serialize_image, serialize_image_relation
from organizations.scope import resolve_workspace_scope


@router.get(
    "/workspaces/{workspace_id}/images", response=List[ImageOut], auth=JWTAuth()
)
@paginate(LimitOffsetPagination)
def list_images_for_org(request, workspace_id: UUID, ordering: str | None = None):
    scope = resolve_workspace_scope(request, workspace_id)
    ordering_map = {
        None: "-created_at",
        "created_at": "created_at",
        "-created_at": "-created_at",
        "title": "title",
        "-title": "-title",
    }
    if ordering not in ordering_map:
        raise HttpError(
            400, "Invalid ordering. Allowed: created_at, -created_at, title, -title"
        )
    return [
        serialize_image(image)
        for image in Image.objects.filter(organization=scope.workspace).order_by(
            ordering_map[ordering]
        )
    ]


@router.get(
    "/workspaces/{workspace_id}/objects/{app_label}/{model}/{object_id}/images",
    response=List[PolymorphicImageRelationOut],
    auth=JWTAuth(),
)
@paginate(LimitOffsetPagination)
def list_images_for_object(
    request,
    workspace_id: UUID,
    app_label: str,
    model: str,
    object_id: UUID,
    ordering: str | None = None,
):
    resolved = resolve_workspace_scoped_content_object(
        request, workspace_id, app_label, model, object_id
    )
    ct = resolved.content_type
    ordering_map = {
        None: "order",
        "order": "order",
        "-order": "-order",
        "created_at": "image__created_at",
        "-created_at": "-image__created_at",
        "title": "image__title",
        "-title": "-image__title",
    }
    if ordering not in ordering_map:
        raise HttpError(
            400, "Invalid ordering. Allowed: created_at, -created_at, title, -title"
        )
    relations = (
        PolymorphicImageRelation.objects.filter(content_type=ct, object_id=object_id)
        .select_related("image")
        .order_by(ordering_map[ordering], "pk")
    )
    return [serialize_image_relation(relation) for relation in relations]
