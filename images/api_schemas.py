from typing import List, Optional
from uuid import UUID

from ninja import Schema
from pydantic import ConfigDict


class BulkDeleteResponse(Schema):
    id: Optional[UUID] = None
    status: str
    error: Optional[str] = None


class BulkUploadResponse(Schema):
    id: Optional[UUID] = None
    file: Optional[str] = None
    status: str
    error: Optional[str] = None


class BulkImageIdsIn(Schema):
    image_ids: List[UUID]
    model_config = ConfigDict(extra="forbid")


class ImageIdsIn(Schema):
    image_ids: list[UUID]
    model_config = ConfigDict(extra="forbid")


class ReorderIn(Schema):
    image_ids: list[UUID]
    model_config = ConfigDict(extra="forbid")
